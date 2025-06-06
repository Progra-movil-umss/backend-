import hashlib
from datetime import timedelta, datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBearer
from fastapi.templating import Jinja2Templates
from jose import jwt
from sqlalchemy.orm import Session

from src.auth import service, schemas, models
from src.auth.service import email_service, get_password_hash
from src.config import get_settings
from src.database import get_db
from src.validators.password import validate_password

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()

templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

settings = get_settings()


@router.post("/register", 
            response_model=schemas.UserResponse,
            responses={
                201: {"description": "Usuario creado exitosamente"},
                400: {"model": schemas.ErrorResponse, "description": "Datos inválidos"},
                409: {"model": schemas.ErrorResponse, "description": "Conflicto con datos existentes"},
                422: {"description": "Error de validación", "model": schemas.ValidationError}
            },
            status_code=status.HTTP_201_CREATED,
            summary="Registrar nuevo usuario")
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)) -> dict:
    created_user = service.create_user(db=db, user=user)
    return {
        "status_code": 201,
        "message": "Usuario registrado exitosamente",
        "data": created_user
    }


@router.post("/token", 
            response_model=schemas.LoginResponse,
            responses={
                200: {"description": "Login exitoso"},
                400: {"model": schemas.ErrorResponse, "description": "Datos inválidos"},
                401: {"model": schemas.ErrorResponse, "description": "No autorizado"},
                429: {"model": schemas.ErrorResponse, "description": "Demasiados intentos"},
                422: {"description": "Error de validación", "model": schemas.ValidationError}
            },
            summary="Iniciar sesión")
def login_for_access_token(
        login_data: schemas.LoginRequest,
        db: Session = Depends(get_db)
) -> dict:
    # Validar campos requeridos
    if not login_data.username_or_email or not login_data.password:
        raise HTTPException(
            status_code=400,
            detail="El email/username y la contraseña son requeridos"
        )
    # Autenticar usuario
    user = service.authenticate_user(db, login_data.username_or_email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=400,
            detail="Credenciales inválidas"
        )
    # Generar tokens
    access_token = service.create_access_token(data={"sub": str(user.id)})
    refresh_token = service.create_refresh_token(data={"sub": str(user.id)})
    return {
        "status_code": 200,
        "message": "Login exitoso",
        "data": {
            "access_token": access_token,
            "token_type": "bearer",
            "refresh_token": refresh_token,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "username": user.username
            }
        }
    }


@router.post("/refresh", 
            response_model=schemas.RefreshTokenResponse,
            responses={
                200: {"description": "Token refrescado exitosamente"},
                400: {"model": schemas.ErrorResponse, "description": "Datos inválidos"},
                401: {"model": schemas.ErrorResponse, "description": "No autorizado"},
                422: {"description": "Error de validación", "model": schemas.ValidationError}
            },
            summary="Refrescar token de acceso")
def refresh_token(
        refresh_token: str = Form(..., description="Token de refresco"),
        db: Session = Depends(get_db)
) -> dict:
    # Validar que se proporcionó el token
    if not refresh_token:
        return JSONResponse(
            status_code=400,
            content={
                "status_code": 400,
                "message": "Datos inválidos",
                "detail": "Token de refresco no proporcionado"
            }
        )
    # Decodificar y validar el token
    try:
        payload = jwt.decode(
            refresh_token,
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        user_id = payload.get("sub")
        token_type = payload.get("type")
        if not user_id or token_type != "refresh":
            return JSONResponse(
                status_code=401,
                content={
                    "status_code": 401,
                    "message": "No autorizado",
                    "detail": "Token de refresco inválido"
                }
            )
    except jwt.ExpiredSignatureError:
        return JSONResponse(
            status_code=401,
            content={
                "status_code": 401,
                "message": "No autorizado",
                "detail": "Token de refresco expirado"
            }
        )
    except jwt.JWTError:
        return JSONResponse(
            status_code=401,
            content={
                "status_code": 401,
                "message": "No autorizado",
                "detail": "Token de refresco inválido"
            }
        )
    # Verificar que el usuario existe
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return JSONResponse(
            status_code=401,
            content={
                "status_code": 401,
                "message": "No autorizado",
                "detail": "Usuario no encontrado"
            }
        )
    # Generar nuevos tokens
    new_access_token = service.create_access_token(data={"sub": str(user.id)})
    new_refresh_token = service.create_refresh_token(data={"sub": str(user.id)})
    return {
        "status_code": 200,
        "message": "Token refrescado exitosamente",
        "data": {
            "access_token": new_access_token,
            "token_type": "bearer",
            "refresh_token": new_refresh_token,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "username": user.username
            }
        }
    }


@router.post("/password-reset-request", 
            response_model=schemas.PasswordResetRequestResponse,
            responses={
                200: {"description": "Solicitud de restablecimiento enviada"},
                400: {"model": schemas.ErrorResponse, "description": "Datos inválidos"},
                429: {"model": schemas.ErrorResponse, "description": "Demasiados intentos"},
                422: {"description": "Error de validación", "model": schemas.ValidationError}
            },
            summary="Solicitar restablecimiento de contraseña")
async def request_password_reset(
        request: Request,
        reset_request: schemas.PasswordResetRequest,
        db: Session = Depends(get_db)
) -> dict:
    # Verificar si el usuario existe
    user = db.query(models.User).filter(models.User.email == reset_request.email).first()
    if not user:
        return {
            "status_code": 200,
            "message": "Solicitud de restablecimiento enviada",
            "data": {
                "detail": "Si existe una cuenta con ese email, recibirás instrucciones para restablecer tu contraseña"
            }
        }
    # Verificar intentos de restablecimiento
    if user.reset_attempts >= 3:
        if user.reset_lockout_until and user.reset_lockout_until > datetime.now(timezone.utc):
            raise HTTPException(
                status_code=429,
                detail="Demasiados intentos. Por favor, intente más tarde"
            )
        # Resetear contadores si ya pasó el tiempo de bloqueo
        user.reset_attempts = 0
        user.reset_lockout_until = None
    # Generar y enviar token
    token = await service.create_password_reset_token(user)
    try:
        await email_service.send_password_reset_email(user.email, token)
    except Exception as e:
        print(f"Error al enviar email: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error al enviar el email de restablecimiento"
        )
    # Incrementar contador de intentos
    user.reset_attempts = (user.reset_attempts or 0) + 1
    if user.reset_attempts >= 3:
        user.reset_lockout_until = datetime.now(timezone.utc) + timedelta(minutes=15)
    db.commit()
    return {
        "status_code": 200,
        "message": "Solicitud de restablecimiento enviada",
        "data": {
            "detail": "Si existe una cuenta con ese email, recibirás instrucciones para restablecer tu contraseña"
        }
    }


@router.get("/password-reset",
            response_class=HTMLResponse,
            responses={
                200: {"description": "Formulario de restablecimiento"},
                400: {"model": schemas.ErrorResponse, "description": "Token inválido o expirado"},
                401: {"model": schemas.ErrorResponse, "description": "No autorizado"}
            },
            summary="Mostrar formulario de restablecimiento")
async def get_password_reset_form(
        request: Request,
        token: str,
        db: Session = Depends(get_db)
) -> HTMLResponse:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        token_type = payload.get("type")
        if not user_id or token_type != "password_reset":
            return templates.TemplateResponse(
                "email/reset_password_error.html",
                {
                    "request": request,
                    "error_code": 400,
                    "error_message": "Token inválido"
                }
            )
    except jwt.ExpiredSignatureError:
        return templates.TemplateResponse(
            "email/reset_password_error.html",
            {
                "request": request,
                "error_code": 400,
                "error_message": "El enlace de restablecimiento ha expirado"
            }
        )
    except jwt.JWTError:
        return templates.TemplateResponse(
            "email/reset_password_error.html",
            {
                "request": request,
                "error_code": 400,
                "error_message": "Token inválido"
            }
        )
    # Verificar que el usuario existe
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return templates.TemplateResponse(
            "email/reset_password_error.html",
            {
                "request": request,
                "error_code": 400,
                "error_message": "Usuario no encontrado"
            }
        )
    # Verificar si el token ya fue usado
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    used_token = db.query(models.UsedToken).filter(
        models.UsedToken.token_hash == token_hash
    ).first()
    if used_token:
        return templates.TemplateResponse(
            "email/reset_password_error.html",
            {
                "request": request,
                "error_code": 400,
                "error_message": "Este enlace ya ha sido utilizado"
            }
        )
    return templates.TemplateResponse(
        "email/reset_password.html",
        {"request": request, "token": token}
    )


@router.post("/password-reset",
            response_model=schemas.PasswordResetResponse,
            responses={
                200: {"description": "Contraseña actualizada exitosamente"},
                400: {"model": schemas.ErrorResponse, "description": "Datos inválidos"},
                422: {"description": "Error de validación", "model": schemas.ValidationError}
            },
            summary="Restablecer contraseña")
async def reset_password(
        token: str = Form(...),
        new_password: str = Form(...),
        db: Session = Depends(get_db)
) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        token_type = payload.get("type")
        if not user_id or token_type != "password_reset":
            raise HTTPException(
                status_code=400,
                detail="Token inválido"
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=400,
            detail="El enlace de restablecimiento ha expirado"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=400,
            detail="Token inválido"
        )
    # Verificar que el usuario existe
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=400,
            detail="Usuario no encontrado"
        )
    # Verificar si el token ya fue usado
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    used_token = db.query(models.UsedToken).filter(
        models.UsedToken.token_hash == token_hash
    ).first()
    if used_token:
        raise HTTPException(
            status_code=400,
            detail="Este enlace ya ha sido utilizado"
        )
    # Validar nueva contraseña
    is_valid, error_message = validate_password(new_password)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=error_message
        )
    # Actualizar contraseña
    hashed_password = get_password_hash(new_password)
    user.hashed_password = hashed_password
    # Registrar en historial
    password_history = models.PasswordHistory(
        user_id=user.id,
        hashed_password=hashed_password
    )
    # Marcar token como usado
    used_token = models.UsedToken(
        token_hash=token_hash,
        token_type="password_reset",
        user_id=user.id
    )
    # Resetear contadores
    user.reset_attempts = 0
    user.reset_lockout_until = None
    db.add(password_history)
    db.add(used_token)
    db.commit()
    return {
        "status_code": 200,
        "message": "Contraseña actualizada exitosamente",
        "data": {
            "detail": "Tu contraseña ha sido actualizada correctamente"
        }
    }


@router.get("/me", 
            response_model=schemas.UserResponse,
            responses={
                200: {"description": "Datos del usuario obtenidos exitosamente"},
                401: {"model": schemas.ErrorResponse, "description": "No autorizado"},
                422: {"description": "Error de validación", "model": schemas.ValidationError}
            },
            summary="Obtener datos del usuario actual")
async def get_me(current_user: dict = Depends(service.get_current_user)) -> dict:
    return {
        "status_code": 200,
        "message": "Datos del usuario obtenidos exitosamente",
        "data": {
            "id": str(current_user["id"]),
            "email": current_user["email"],
            "username": current_user["username"],
            "is_active": current_user["is_active"],
            "created_at": current_user["created_at"],
            "updated_at": current_user["updated_at"]
        }
    }


@router.put("/me", 
            response_model=schemas.UserUpdateResponse,
            responses={
                200: {"description": "Perfil actualizado exitosamente"},
                400: {"model": schemas.ErrorResponse, "description": "Datos inválidos"},
                401: {"model": schemas.ErrorResponse, "description": "No autorizado"},
                404: {"model": schemas.ErrorResponse, "description": "Usuario no encontrado"}
            },
            summary="Actualizar perfil de usuario")
def update_user_me(
        user_update: schemas.UserUpdate,
        current_user: schemas.User = Depends(service.get_current_user),
        db: Session = Depends(get_db)
) -> dict:
    updated_user = service.update_user(
        db=db,
        user_id=current_user.id,
        user_update=user_update,
        current_password=user_update.current_password
    )
    return {
        "status_code": 200,
        "message": "Perfil actualizado exitosamente",
        "data": updated_user
    }
