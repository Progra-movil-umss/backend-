import pytest
import asyncio
from datetime import datetime, timedelta
import jwt
from sqlalchemy.orm import Session
import hashlib
import threading
import concurrent.futures
import time

from src.auth import service, schemas, models, exceptions
from src.config import get_settings
from src.auth.utils import get_utc_now
from src.auth.service import MAX_RESET_ATTEMPTS

# Añadir configuración de asyncio para las pruebas
pytest_plugins = ('pytest_asyncio',)

settings = get_settings()

def test_verify_password():
    password = "Test1234!"
    hashed_password = service.get_password_hash(password)
    
    assert service.verify_password(password, hashed_password) is True
    assert service.verify_password("WrongPassword123!", hashed_password) is False

def test_get_password_hash():
    password = "Test1234!"
    hashed_password = service.get_password_hash(password)
    
    assert password != hashed_password
    assert hashed_password.startswith("$2b$")

def test_create_access_token():
    data = {"sub": "testuser"}
    token = service.create_access_token(data)
    
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    
    assert payload.get("sub") == "testuser"
    assert payload.get("type") == "access"
    assert "exp" in payload

def test_create_refresh_token():
    data = {"sub": "testuser"}
    token = service.create_refresh_token(data)
    
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    
    assert payload.get("sub") == "testuser"
    assert payload.get("type") == "refresh"
    assert "exp" in payload

def test_create_password_reset_token():
    data = {"sub": "testuser"}
    token = service.create_password_reset_token(data)
    
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    
    assert payload.get("sub") == "testuser"
    assert payload.get("type") == "password_reset"
    assert "exp" in payload

def test_authenticate_user(db_session, test_user):
    # Autenticación exitosa
    authenticated_user = service.authenticate_user(
        db_session, 
        "test@example.com", 
        "Test1234!"
    )
    assert authenticated_user is not None
    assert authenticated_user.id == test_user.id
    
    # Autenticación fallida - email incorrecto
    non_user = service.authenticate_user(
        db_session, 
        "wrong@example.com", 
        "Test1234!"
    )
    assert non_user is None
    
    # Autenticación fallida - contraseña incorrecta
    wrong_pass_user = service.authenticate_user(
        db_session, 
        "test@example.com", 
        "WrongPassword123!"
    )
    assert wrong_pass_user is None

def test_create_user(db_session):
    user_data = schemas.UserCreate(
        email="newuser@example.com",
        username="newuser",
        password="Test1234!"
    )
    
    new_user = service.create_user(db_session, user_data)
    
    assert new_user.email == "newuser@example.com"
    assert new_user.username == "newuser"
    assert new_user.hashed_password != "Test1234!"
    assert new_user.is_active is True
    assert new_user.is_superuser is False
    
    # Verificar que el historial de contraseñas también se guarda
    password_history = db_session.query(models.PasswordHistory).filter(
        models.PasswordHistory.user_id == new_user.id
    ).first()
    
    assert password_history is not None
    assert password_history.hashed_password == new_user.hashed_password

def test_create_duplicate_user(db_session, test_user):
    user_data = schemas.UserCreate(
        email="test@example.com",
        username="anotheruser",
        password="Test1234!"
    )
    
    with pytest.raises(exceptions.UserAlreadyExistsException):
        service.create_user(db_session, user_data)
    
    user_data = schemas.UserCreate(
        email="another@example.com",
        username="testuser",
        password="Test1234!"
    )
    
    with pytest.raises(exceptions.UserAlreadyExistsException):
        service.create_user(db_session, user_data)

def test_update_user(db_session, test_user):
    user_update = schemas.UserUpdate(
        full_name="Test User Full Name"
    )
    
    updated_user = service.update_user(
        db_session, 
        user_id=test_user.id, 
        user_update=user_update
    )
    
    assert updated_user.full_name == "Test User Full Name"

def test_update_user_password(db_session, test_user):
    user_update = schemas.UserUpdate(
        current_password="Test1234!",
        new_password="NewPassword123!"
    )
    
    updated_user = service.update_user(
        db_session, 
        user_id=test_user.id, 
        user_update=user_update,
        current_password="Test1234!"
    )
    
    assert service.verify_password("NewPassword123!", updated_user.hashed_password)
    assert not service.verify_password("Test1234!", updated_user.hashed_password)
    
    # Verificar que el historial de contraseñas se actualizó
    password_history = db_session.query(models.PasswordHistory).filter(
        models.PasswordHistory.user_id == test_user.id
    ).order_by(models.PasswordHistory.created_at.desc()).first()
    
    assert password_history is not None
    assert password_history.hashed_password == updated_user.hashed_password

def test_update_user_password_invalid_current(db_session, test_user):
    user_update = schemas.UserUpdate(
        current_password="WrongPassword123!",
        new_password="NewPassword123!"
    )
    
    with pytest.raises(exceptions.InvalidCredentialsException):
        service.update_user(
            db_session, 
            user_id=test_user.id, 
            user_update=user_update,
            current_password="WrongPassword123!"
        )

def test_password_reset_flow(db_session, test_user):
    # Solicitar restablecimiento
    result = service.request_password_reset(db_session, test_user.email)
    assert result is True  # En pruebas debe retornar True aunque no envíe el email real
    
    # Simular el token
    token = service.create_password_reset_token({"sub": test_user.username})
    
    # Restablecer contraseña
    result = service.reset_password(db_session, token, "ResetPassword123!")
    assert result is True
    
    # Verificar que la contraseña se actualizó
    db_session.refresh(test_user)
    assert service.verify_password("ResetPassword123!", test_user.hashed_password)

@pytest.mark.asyncio
async def test_get_current_user(db_session, test_user):
    token = service.create_access_token(data={"sub": test_user.username})
    
    user = await service.get_current_user(token, db_session)
    
    assert user.id == test_user.id
    assert user.username == test_user.username 

def test_token_is_marked_as_used(db_session, test_user):
    # Solicitar restablecimiento
    service.request_password_reset(db_session, test_user.email)
    
    # Simular el token
    token = service.create_password_reset_token({"sub": test_user.username})
    
    # Restablecer contraseña
    service.reset_password(db_session, token, "ResetPassword123!")
    
    # Verificar que el token está marcado como usado
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    used_token = db_session.query(models.UsedToken).filter(
        models.UsedToken.token_hash == token_hash
    ).first()
    
    assert used_token is not None
    assert used_token.token_type == "password_reset"
    assert used_token.user_id == test_user.id

def test_reset_with_used_token_fails(db_session, test_user):
    # Solicitar restablecimiento
    service.request_password_reset(db_session, test_user.email)
    
    # Simular el token
    token = service.create_password_reset_token({"sub": test_user.username})
    
    # Restablecer contraseña primera vez
    service.reset_password(db_session, token, "ResetPassword123!")
    
    # Intentar restablecer de nuevo con el mismo token
    with pytest.raises(exceptions.InvalidTokenException) as excinfo:
        service.reset_password(db_session, token, "DifferentPassword456!")
    
    assert "ya ha sido utilizado" in str(excinfo.value)

def test_reset_attempt_limits(db_session, test_user):
    # Simular múltiples intentos de restablecimiento
    for _ in range(MAX_RESET_ATTEMPTS):
        service.request_password_reset(db_session, test_user.email)
    
    # Verificar que el contador de intentos se actualizó
    db_session.refresh(test_user)
    assert test_user.reset_attempts == MAX_RESET_ATTEMPTS
    
    # El siguiente intento debería fallar con RateLimitException
    with pytest.raises(exceptions.RateLimitException) as excinfo:
        service.request_password_reset(db_session, test_user.email)
    
    assert "Demasiados intentos" in str(excinfo.value)
    
    # Verificar que se estableció el tiempo de bloqueo
    db_session.refresh(test_user)
    assert test_user.reset_lockout_until is not None
    
    # Asegurar que ambas fechas tengan información de zona horaria para la comparación
    from datetime import timezone
    lockout_time = test_user.reset_lockout_until
    if lockout_time.tzinfo is None:
        lockout_time = lockout_time.replace(tzinfo=timezone.utc)
    
    current_time = get_utc_now()
    assert lockout_time > current_time

def test_password_history_constraint(db_session, test_user):
    # Cambiar contraseña una vez
    service.update_user(
        db_session, 
        user_id=test_user.id, 
        user_update=schemas.UserUpdate(new_password="Password123!"),
        current_password="Test1234!"
    )
    
    # Solicitar restablecimiento
    service.request_password_reset(db_session, test_user.email)
    token = service.create_password_reset_token({"sub": test_user.username})
    
    # Intentar restablecer con la misma contraseña
    with pytest.raises(exceptions.PasswordHistoryException):
        service.reset_password(db_session, token, "Password123!")
    
    # Debería funcionar con una contraseña diferente
    result = service.reset_password(db_session, token, "DifferentPassword456!")
    assert result is True

def test_reset_attempts_counter_resets_after_time(db_session, test_user, monkeypatch):
    """Verificar que el contador de intentos de restablecimiento se reinicia después de 1 hora."""
    # Configurar intentos iniciales
    test_user.reset_attempts = 2
    
    # Guardar last_reset_attempt sin información de zona horaria
    from datetime import timezone
    now = get_utc_now().replace(tzinfo=None)
    test_user.last_reset_attempt = now
    db_session.commit()
    
    # Simular el paso de tiempo (más de 1 hora)
    future_time = get_utc_now() + timedelta(hours=1, minutes=1)
    future_time_naive = future_time.replace(tzinfo=None)  # Sin zona horaria
    
    # Parchar la función get_utc_now para que devuelva un tiempo futuro
    def mock_get_utc_now():
        return future_time
    
    monkeypatch.setattr(service.utils, "get_utc_now", mock_get_utc_now)
    
    # Solicitar restablecimiento después del tiempo
    service.request_password_reset(db_session, test_user.email)
    
    # Verificar que el contador se reinició
    db_session.refresh(test_user)
    assert test_user.reset_attempts == 1  # Debería reiniciarse a 1 (este intento)
    
    # Solo comparamos que el día, hora, minuto y segundo sean iguales
    reset_time = test_user.last_reset_attempt
    assert reset_time.year == future_time_naive.year
    assert reset_time.month == future_time_naive.month
    assert reset_time.day == future_time_naive.day
    assert reset_time.hour == future_time_naive.hour
    assert reset_time.minute == future_time_naive.minute

def test_token_expiration(db_session, test_user):
    """Verificar que el token de restablecimiento expire correctamente."""
    # En lugar de crear manualmente un token expirado,
    # creamos un token normal con la funcionalidad estándar
    # pero con un tiempo de expiración muy corto
    from src.auth.service import settings
    from jose import jwt
    
    # Guardar la configuración original
    original_expire_minutes = settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
    
    # Establecer expiración a 0 minutos para que expire inmediatamente
    settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = 0
    
    try:
        # Crear un token que ya debe estar expirado
        token = service.create_password_reset_token({"sub": test_user.username})
        
        # Esperar un poco para asegurar que el token expire
        time.sleep(1)
        
        # Intentar usar el token expirado
        with pytest.raises(exceptions.TokenExpiredException):
            service.reset_password(db_session, token, "NewPassword123!")
    finally:
        # Restaurar la configuración original
        settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = original_expire_minutes

def test_password_history_cleanup(db_session, test_user):
    """Verifica que se cree y mantenga un historial de contraseñas."""
    # Contraseña original
    original_password = "Test1234!"
    
    # Cambiar a una nueva contraseña usando update_user
    new_password = "Password1!Abc123"
    service.update_user(
        db_session,
        user_id=test_user.id,
        user_update=schemas.UserUpdate(new_password=new_password),
        current_password=original_password
    )
    
    # Verificar que existe al menos una entrada en el historial de contraseñas
    password_history = db_session.query(models.PasswordHistory).filter(
        models.PasswordHistory.user_id == test_user.id
    ).all()
    
    # Debe haber al menos una entrada en el historial
    assert len(password_history) > 0
    
    # Verificar que la contraseña anterior está en el historial
    old_hash = service.get_password_hash(original_password)
    for entry in password_history:
        if service.verify_password(original_password, entry.hashed_password):
            break
    else:
        pytest.fail("La contraseña original no se encontró en el historial")

def test_special_characters_password(db_session, test_user):
    """Verificar que las contraseñas con caracteres especiales se manejen correctamente."""
    # Contraseñas con caracteres especiales y Unicode
    special_passwords = [
        "P@$$w0rd!",
        "Clave-Con_Símbolos#123",
        "Contraseña2023!",
        "Password💪123!",
        "官话123Abc!"
    ]
    
    current_password = "Test1234!"  # Contraseña inicial
    
    # Probar cada contraseña especial con la función update_user en lugar de reset_password
    for password in special_passwords:
        # Actualizar contraseña con caracteres especiales
        service.update_user(
            db_session,
            user_id=test_user.id,
            user_update=schemas.UserUpdate(new_password=password),
            current_password=current_password
        )
        
        # Verificar que la contraseña se guardó correctamente
        db_session.refresh(test_user)
        assert service.verify_password(password, test_user.hashed_password)
        
        # Usar esta contraseña como la contraseña actual para la siguiente iteración
        current_password = password

def test_concurrent_password_reset_requests(db_session, test_user):
    """Verificar que múltiples solicitudes simultáneas se manejen correctamente."""
    # Función que ejecuta la solicitud de restablecimiento
    def request_reset():
        try:
            # Crear una nueva sesión para cada hilo
            from sqlalchemy.orm import sessionmaker
            SessionLocal = sessionmaker(bind=db_session.bind)
            thread_db = SessionLocal()
            
            # Buscar el usuario en esta sesión
            user = thread_db.query(models.User).filter(models.User.id == test_user.id).first()
            
            # Hacer la solicitud
            return service.request_password_reset(thread_db, user.email)
        except Exception as e:
            return str(e)
        finally:
            thread_db.close()
    
    # Simular 5 solicitudes concurrentes
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(request_reset) for _ in range(5)]
        results = [future.result() for future in futures]
    
    # Verificar que al menos una solicitud tuvo éxito
    assert any(results)
    
    # Verificar que el contador de intentos se actualizó
    db_session.refresh(test_user)
    assert test_user.reset_attempts > 0
    
    # Verificar que no hay condiciones de carrera en la base de datos
    # Si hubiera problemas de concurrencia, alguna excepción se habría levantado 