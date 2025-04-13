import pytest
import asyncio
from datetime import datetime, timedelta
import jwt
from sqlalchemy.orm import Session

from src.auth import service, schemas, models, exceptions
from src.config import get_settings

# Añadir configuración de asyncio para las pruebas
pytest_plugins = ['pytest_asyncio']

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