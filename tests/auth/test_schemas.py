import pytest
from pydantic import ValidationError

from src.auth import schemas

def test_user_base_schema():
    # Caso válido
    user_data = {
        "email": "test@example.com",
        "username": "testuser",
        "full_name": "Test User"
    }
    user = schemas.UserBase(**user_data)
    assert user.email == user_data["email"]
    assert user.username == user_data["username"]
    assert user.full_name == user_data["full_name"]
    
    # Email inválido
    with pytest.raises(ValidationError):
        schemas.UserBase(
            email="invalid-email",
            username="testuser"
        )
    
    # Username demasiado corto
    with pytest.raises(ValidationError):
        schemas.UserBase(
            email="test@example.com",
            username="te"  # menos de 3 caracteres
        )
    
    # Username demasiado largo
    with pytest.raises(ValidationError):
        schemas.UserBase(
            email="test@example.com",
            username="a" * 51  # más de 50 caracteres
        )

def test_user_create_schema():
    # Caso válido
    user_data = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "Test1234!",
        "full_name": "Test User"
    }
    user = schemas.UserCreate(**user_data)
    assert user.email == user_data["email"]
    assert user.username == user_data["username"]
    assert user.password == user_data["password"]
    assert user.full_name == user_data["full_name"]
    
    # Contraseña demasiado corta
    with pytest.raises(ValidationError):
        schemas.UserCreate(
            email="test@example.com",
            username="testuser",
            password="Test"  # menos de 8 caracteres
        )
    
    # Contraseña sin fuerza suficiente (depende de validate_password)
    # Nota: esto depende de la implementación exacta de validate_password

def test_user_update_schema():
    # Actualización completa
    user_data = {
        "email": "updated@example.com",
        "username": "updateduser",
        "full_name": "Updated User",
        "current_password": "CurrentPass123!",
        "new_password": "NewPass123!"
    }
    user = schemas.UserUpdate(**user_data)
    assert user.email == user_data["email"]
    assert user.username == user_data["username"]
    assert user.full_name == user_data["full_name"]
    assert user.current_password == user_data["current_password"]
    assert user.new_password == user_data["new_password"]
    
    # Actualización parcial
    user_data = {
        "full_name": "Only Name Updated"
    }
    user = schemas.UserUpdate(**user_data)
    assert user.full_name == user_data["full_name"]
    assert user.email is None
    assert user.username is None
    assert user.current_password is None
    assert user.new_password is None
    
    # Solo cambio de contraseña
    user_data = {
        "current_password": "CurrentPass123!",
        "new_password": "NewPass123!"
    }
    user = schemas.UserUpdate(**user_data)
    assert user.current_password == user_data["current_password"]
    assert user.new_password == user_data["new_password"]
    assert user.email is None
    assert user.username is None
    assert user.full_name is None

def test_token_schema():
    token_data = {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer",
        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    }
    token = schemas.Token(**token_data)
    assert token.access_token == token_data["access_token"]
    assert token.token_type == token_data["token_type"]
    assert token.refresh_token == token_data["refresh_token"]

def test_login_request_schema():
    # Caso válido
    login_data = {
        "email": "test@example.com",
        "password": "Test1234!"
    }
    login = schemas.LoginRequest(**login_data)
    assert login.email == login_data["email"]
    assert login.password == login_data["password"]
    
    # Email inválido
    with pytest.raises(ValidationError):
        schemas.LoginRequest(
            email="invalid-email",
            password="Test1234!"
        )

def test_password_reset_request_schema():
    # Caso válido
    reset_data = {
        "email": "test@example.com"
    }
    reset = schemas.PasswordResetRequest(**reset_data)
    assert reset.email == reset_data["email"]
    
    # Email inválido
    with pytest.raises(ValidationError):
        schemas.PasswordResetRequest(
            email="invalid-email"
        )

def test_password_reset_schema():
    # Caso válido
    reset_data = {
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "new_password": "NewPassword123!"
    }
    reset = schemas.PasswordReset(**reset_data)
    assert reset.token == reset_data["token"]
    assert reset.new_password == reset_data["new_password"]
    
    # Contraseña demasiado corta
    with pytest.raises(ValidationError):
        schemas.PasswordReset(
            token="valid_token",
            new_password="short"  # menos de 8 caracteres
        )
    
    # Nota: En la implementación actual, un token vacío es válido para Pydantic,
    # ya que solo se valida que sea un string 