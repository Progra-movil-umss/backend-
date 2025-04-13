from datetime import datetime, timedelta
from typing import Optional, Tuple
import secrets
import hashlib
from uuid import UUID

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from src.auth import models, schemas, email, exceptions, utils
from src.config import get_settings
from src.database import get_db
from src.validators.password import validate_password

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
email_service = email.EmailService()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

MAX_RESET_ATTEMPTS = 4
BASE_LOCKOUT_MINUTES = 5
MAX_LOCKOUT_MINUTES = 60


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = utils.get_utc_now() + expires_delta
    else:
        expire = utils.get_future_datetime(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = utils.get_future_datetime(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_password_reset_token(data: dict) -> str:
    to_encode = data.copy()
    expire = utils.get_future_datetime(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "password_reset"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def authenticate_user(db: Session, email: str, password: str) -> Optional[models.User]:
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    db_user = db.query(models.User).filter(
        (models.User.email == user.email) | (models.User.username == user.username)
    ).first()
    if db_user:
        raise exceptions.UserAlreadyExistsException()

    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password,
        full_name=user.full_name
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    password_history = models.PasswordHistory(
        user_id=db_user.id,
        hashed_password=hashed_password
    )
    db.add(password_history)
    db.commit()

    email_service.send_welcome_email(db_user.email, db_user.username)

    return db_user


def update_user(
        db: Session,
        user_id: int,
        user_update: schemas.UserUpdate,
        current_password: Optional[str] = None
) -> models.User:
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise exceptions.UserNotFoundException()

    update_data = user_update.model_dump(exclude_unset=True)

    if "new_password" in update_data:
        if not current_password or not verify_password(current_password, db_user.hashed_password):
            raise exceptions.InvalidCredentialsException()

        hashed_new_password = get_password_hash(update_data["new_password"])
        recent_passwords = db.query(models.PasswordHistory).filter(
            models.PasswordHistory.user_id == user_id
        ).order_by(models.PasswordHistory.created_at.desc()).limit(
            settings.PASSWORD_HISTORY_SIZE
        ).all()

        for old_password in recent_passwords:
            if verify_password(update_data["new_password"], old_password.hashed_password):
                raise exceptions.PasswordHistoryException()

        db_user.hashed_password = hashed_new_password
        password_history = models.PasswordHistory(
            user_id=user_id,
            hashed_password=hashed_new_password
        )
        db.add(password_history)
        del update_data["new_password"]

    for key, value in update_data.items():
        setattr(db_user, key, value)

    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: int) -> bool:
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        return False

    db.delete(db_user)
    db.commit()
    return True


def request_password_reset(db: Session, email: str) -> bool:
    """
    Solicita un restablecimiento de contraseña para un email.
    
    Args:
        db: Sesión de la base de datos
        email: Email del usuario que solicita el restablecimiento
        
    Returns:
        bool: True si se envió el email correctamente, False si el usuario no existe
        
    Raises:
        RateLimitException: Si se excede el límite de intentos de restablecimiento
    """
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        return False

    # Verificar límites de intentos y aplicar restricciones si es necesario
    _check_reset_rate_limits(db, user)

    # Invalidar tokens anteriores y crear uno nuevo
    reset_token = _create_new_reset_token(db, user)

    # Enviar email con el enlace de restablecimiento
    return _send_password_reset_email(user.email, reset_token)


def _check_reset_rate_limits(db: Session, user: models.User) -> None:
    """
    Verifica los límites de intentos de restablecimiento de contraseña.
    
    Args:
        db: Sesión de la base de datos
        user: Usuario que solicita el restablecimiento
        
    Raises:
        RateLimitException: Si se excede el límite de intentos
    """
    now = utils.get_utc_now()

    # Verificar si el usuario está en tiempo de espera
    if user.reset_lockout_until and user.reset_lockout_until > now:
        remaining_minutes = int((user.reset_lockout_until - now).total_seconds() / 60)
        raise exceptions.RateLimitException(
            f"Demasiados intentos de restablecimiento. Por favor, espera {remaining_minutes} minutos antes de intentarlo nuevamente."
        )

    # Actualizar contadores de intentos
    if user.last_reset_attempt:
        # Asegurarse que last_reset_attempt tenga información de zona horaria
        last_attempt = user.last_reset_attempt
        if last_attempt.tzinfo is None:
            # Si la fecha no tiene zona horaria, asumimos que es UTC
            from datetime import timezone
            last_attempt = last_attempt.replace(tzinfo=timezone.utc)

        if (now - last_attempt) < timedelta(hours=1):
            # Menos de una hora desde el último intento, incrementar contador
            user.reset_attempts += 1
        else:
            # Reiniciar contador si ha pasado más de una hora
            user.reset_attempts = 1
    else:
        # Primer intento
        user.reset_attempts = 1

    user.last_reset_attempt = now

    # Aplicar tiempo de espera si se exceden los intentos
    if user.reset_attempts > MAX_RESET_ATTEMPTS:
        # Calcular tiempo de espera progresivo (5, 10, 20, 40, 60 minutos)
        lockout_minutes = min(
            BASE_LOCKOUT_MINUTES * (2 ** (user.reset_attempts - MAX_RESET_ATTEMPTS - 1)),
            MAX_LOCKOUT_MINUTES
        )
        user.reset_lockout_until = now + timedelta(minutes=lockout_minutes)
        db.commit()
        raise exceptions.RateLimitException(
            f"Demasiados intentos de restablecimiento. Por favor, espera {lockout_minutes} minutos antes de intentarlo nuevamente."
        )

    db.commit()


def _create_new_reset_token(db: Session, user: models.User) -> str:
    """
    Invalida los tokens anteriores de restablecimiento y crea uno nuevo.
    
    Args:
        db: Sesión de la base de datos
        user: Usuario para el que se crea el token
        
    Returns:
        str: Token de restablecimiento generado
    """
    # Invalidar cualquier token anterior para este usuario
    invalidate_previous_tokens(db, user.id, "password_reset")

    # Crear nuevo token
    reset_token = create_password_reset_token({"sub": user.username})
    db.commit()

    return reset_token


def _send_password_reset_email(to_email: str, reset_token: str) -> bool:
    """
    Envía un email con el enlace para restablecer la contraseña.
    
    Args:
        to_email: Email del destinatario
        reset_token: Token de restablecimiento
        
    Returns:
        bool: True si el email se envió correctamente, False en caso contrario
    """
    return email_service.send_password_reset_email(to_email, reset_token)


def invalidate_previous_tokens(db: Session, user_id: UUID, token_type: str) -> None:
    """
    Marca todos los tokens existentes del tipo especificado como utilizados para un usuario.
    Esto se usa para invalidar tokens anteriores cuando se emite uno nuevo.
    """
    invalidation_token = models.UsedToken(
        token_hash=f"invalidation_{token_type}_{user_id}_{utils.get_utc_now().isoformat()}",
        token_type=f"invalidation_{token_type}",
        user_id=user_id
    )
    db.add(invalidation_token)
    db.commit()


def is_token_valid(db: Session, token: str, user_id: UUID, token_type: str) -> bool:
    """
    Verifica si un token es válido: no ha sido utilizado y no ha sido invalidado por
    una solicitud posterior.
    """
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    used_token = db.query(models.UsedToken).filter(
        models.UsedToken.token_hash == token_hash
    ).first()

    if used_token:
        return False

    if token_type == "password_reset":
        return True

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if 'iat' not in payload:  # Si no tiene fecha de emisión, usamos la fecha de expiración
            # Estimamos la fecha de emisión basada en la expiración y duración estándar
            if 'exp' in payload and payload.get('type') == token_type:
                estimated_iat = payload['exp'] - (settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES * 60)
            else:
                return False  # No podemos determinar emisión - no válido
        else:
            estimated_iat = payload['iat']

        # Buscar tokens de invalidación posteriores a la emisión de este token
        invalidation_tokens = db.query(models.UsedToken).filter(
            models.UsedToken.user_id == user_id,
            models.UsedToken.token_type == f"invalidation_{token_type}",
            models.UsedToken.used_at > datetime.fromtimestamp(estimated_iat)
        ).all()

        if invalidation_tokens:
            return False

    except Exception:
        # Cualquier error en la verificación, asumimos que el token no es válido
        return False

    return True


def reset_password(db: Session, token: str, new_password: str) -> bool:
    """
    Restablece la contraseña de un usuario utilizando un token de restablecimiento.
    
    Args:
        db: Sesión de la base de datos
        token: Token de restablecimiento
        new_password: Nueva contraseña
        
    Returns:
        bool: True si la contraseña se restableció correctamente
        
    Raises:
        InvalidTokenException: Si el token no es válido o ya fue utilizado
        TokenExpiredException: Si el token ha expirado
        UserNotFoundException: Si no se encuentra el usuario
        InvalidPasswordException: Si la contraseña no cumple con los requisitos
        PasswordHistoryException: Si la contraseña está en el historial reciente
    """
    try:
        # Validar el token y obtener el usuario
        user = _validate_reset_token(db, token)

        # Validar los requisitos de la contraseña
        _validate_password_requirements(new_password)

        # Verificar que la contraseña no esté en el historial reciente
        _check_password_history(db, user, new_password)

        # Actualizar la contraseña del usuario
        _update_user_password(db, user, new_password, token)

        return True
    except jwt.ExpiredSignatureError:
        raise exceptions.TokenExpiredException()
    except jwt.JWTError:
        raise exceptions.InvalidTokenException()


def _validate_reset_token(db: Session, token: str) -> models.User:
    """
    Valida un token de restablecimiento y devuelve el usuario asociado.
    
    Args:
        db: Sesión de la base de datos
        token: Token de restablecimiento
        
    Returns:
        models.User: Usuario asociado al token
        
    Raises:
        InvalidTokenException: Si el token no es válido o ya fue utilizado
        UserNotFoundException: Si no se encuentra el usuario
    """
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    if payload.get("type") != "password_reset":
        raise exceptions.InvalidTokenException()

    username: str = payload.get("sub")
    if username is None:
        raise exceptions.InvalidTokenException()

    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise exceptions.UserNotFoundException()

    # Verificar si el token ya ha sido utilizado
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    used_token = db.query(models.UsedToken).filter(
        models.UsedToken.token_hash == token_hash
    ).first()

    if used_token:
        raise exceptions.InvalidTokenException(
            "Este enlace ya ha sido utilizado para restablecer tu contraseña. Por favor solicita un nuevo enlace si lo necesitas.")

    return user


def _validate_password_requirements(new_password: str) -> None:
    """
    Valida que la contraseña cumpla con los requisitos de seguridad.
    
    Args:
        new_password: Contraseña a validar
        
    Raises:
        InvalidPasswordException: Si la contraseña no cumple con los requisitos
    """
    if len(new_password) < 8:
        raise exceptions.InvalidPasswordException("La contraseña debe tener al menos 8 caracteres")

    is_valid, error_message = validate_password(new_password)
    if not is_valid:
        raise exceptions.InvalidPasswordException(error_message)


def _check_password_history(db: Session, user: models.User, new_password: str) -> None:
    """
    Verifica que la contraseña no esté en el historial reciente del usuario.
    
    Args:
        db: Sesión de la base de datos
        user: Usuario
        new_password: Nueva contraseña
        
    Raises:
        PasswordHistoryException: Si la contraseña está en el historial reciente
    """
    recent_passwords = db.query(models.PasswordHistory).filter(
        models.PasswordHistory.user_id == user.id
    ).order_by(models.PasswordHistory.created_at.desc()).limit(
        settings.PASSWORD_HISTORY_SIZE
    ).all()

    for old_password in recent_passwords:
        if verify_password(new_password, old_password.hashed_password):
            raise exceptions.PasswordHistoryException()


def _update_user_password(db: Session, user: models.User, new_password: str, token: str) -> None:
    """
    Actualiza la contraseña del usuario y registra el cambio.
    
    Args:
        db: Sesión de la base de datos
        user: Usuario
        new_password: Nueva contraseña
        token: Token utilizado para el restablecimiento
    """
    # Cifrar la nueva contraseña
    hashed_new_password = get_password_hash(new_password)

    # Actualizar la contraseña del usuario
    user.hashed_password = hashed_new_password

    # Registrar la nueva contraseña en el historial
    password_history = models.PasswordHistory(
        user_id=user.id,
        hashed_password=hashed_new_password
    )
    db.add(password_history)

    # Marcar el token como utilizado
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    used_token = models.UsedToken(
        token_hash=token_hash,
        token_type="password_reset",
        user_id=user.id
    )
    db.add(used_token)

    # Reiniciar contadores de intentos
    user.reset_attempts = 0
    user.reset_lockout_until = None

    db.commit()


def get_user_from_token(db: Session, token: str) -> models.User:
    """
    Valida un token y devuelve el usuario asociado.
    Utilizado principalmente para el endpoint de refresco de tokens.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        token_type: str = payload.get("type", "")

        if username is None:
            raise exceptions.InvalidTokenException()

        if token_type != "refresh":
            raise exceptions.InvalidTokenException("Token inválido: se requiere un token de refresco")

        user = db.query(models.User).filter(models.User.username == username).first()
        if user is None:
            raise exceptions.UserNotFoundException()

        return user
    except jwt.ExpiredSignatureError:
        raise exceptions.TokenExpiredException()
    except jwt.JWTError:
        raise exceptions.InvalidTokenException()


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
) -> models.User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        token_type: str = payload.get("type", "access")

        if username is None:
            raise exceptions.InvalidCredentialsException()

        if token_type != "access":
            raise exceptions.InvalidTokenException("Token inválido: se requiere un token de acceso")

    except jwt.ExpiredSignatureError:
        raise exceptions.TokenExpiredException()
    except jwt.JWTError:
        raise exceptions.InvalidTokenException()

    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise exceptions.UserNotFoundException()

    return user


def validate_password_reset_form_token(token: str) -> dict:
    """
    Valida un token para el formulario de restablecimiento de contraseña.
    
    Args:
        token: Token de restablecimiento
        
    Returns:
        dict: Datos para la plantilla, incluyendo mensajes de error si los hay
    """
    try:
        db = next(get_db())

        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        # Verificar que sea un token de restablecimiento de contraseña
        if payload.get("type") != "password_reset":
            return {
                "title": "Enlace inválido",
                "message": "Este enlace de restablecimiento de contraseña no es válido."
            }

        # Verificar que contenga información de usuario
        username = payload.get("sub")
        if username is None:
            return {
                "title": "Enlace inválido",
                "message": "Este enlace de restablecimiento de contraseña no contiene información de usuario."
            }

        # Buscar el usuario
        user = db.query(models.User).filter(models.User.username == username).first()
        if user is None:
            return {
                "title": "Usuario no encontrado",
                "message": "No se encontró ningún usuario asociado a este enlace."
            }

        # Verificar si el token ya ha sido utilizado
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        used_token = db.query(models.UsedToken).filter(
            models.UsedToken.token_hash == token_hash
        ).first()

        if used_token:
            return {
                "title": "Enlace ya utilizado",
                "message": "Este enlace ya ha sido utilizado para restablecer la contraseña. Por favor, solicita uno nuevo si necesitas cambiar tu contraseña."
            }

        # Verificar si ha sido invalidado por un token más reciente
        if not is_token_valid(db, token, user.id, "password_reset"):
            return {
                "title": "Enlace reemplazado",
                "message": "Este enlace ya no es válido porque se ha solicitado uno más reciente. Por favor, utiliza el enlace más reciente que enviamos a tu correo."
            }

        # Token válido
        return {}

    except jwt.ExpiredSignatureError:
        return {
            "title": "Enlace expirado",
            "message": "Este enlace de restablecimiento de contraseña ha expirado. Por favor, solicita uno nuevo."
        }
    except jwt.JWTError:
        return {
            "title": "Enlace inválido",
            "message": "Este enlace de restablecimiento de contraseña no es válido o ha sido modificado."
        }
    except Exception as e:
        return {
            "title": "Error inesperado",
            "message": "Ha ocurrido un error al procesar este enlace. Por favor, solicita uno nuevo."
        }
