import pytest
from pydantic import ValidationError

from src.auth import schemas

def test_user_base_schema():
    # Caso válido
    user_data = {
        "email": "test@example.com",
        "username": "testuser"
    }
    user = schemas.UserBase(**user_data)
    assert user.email == user_data["email"]
    assert user.username == user_data["username"]
    
    # Correo inválido
    with pytest.raises(ValidationError):
        schemas.UserBase(email="invalid_email", username="testuser")
    
    # Username demasiado corto
    with pytest.raises(ValidationError):
        schemas.UserBase(email="test@example.com", username="te")

def test_user_create_schema():
    # Caso válido
    user_data = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "Test1234!"
    }
    user = schemas.UserCreate(**user_data)
    assert user.email == user_data["email"]
    assert user.username == user_data["username"]
    assert user.password == user_data["password"]
    
    # Contraseña insegura
    with pytest.raises(ValidationError):
        schemas.UserCreate(
            email="test@example.com",
            username="testuser",
            password="password"  # Contraseña simple
        )

def test_user_update_schema():
    # Actualización completa
    user_data = {
        "email": "updated@example.com",
        "username": "updateduser",
        "current_password": "CurrentPass123!",
        "new_password": "NewPass123!"
    }
    user = schemas.UserUpdate(**user_data)
    assert user.email == user_data["email"]
    assert user.username == user_data["username"]
    assert user.current_password == user_data["current_password"]
    assert user.new_password == user_data["new_password"]
    
    # Actualización parcial solo username
    user_data = {
        "username": "only_username_updated"
    }
    user = schemas.UserUpdate(**user_data)
    assert user.username == user_data["username"]
    assert user.email is None
    assert user.new_password is None
    
    # Nueva contraseña insegura
    with pytest.raises(ValidationError):
        schemas.UserUpdate(
            email="test@example.com",
            new_password="password"  # Contraseña simple
        )

def test_token_schema():
    token_data = {
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "token_type": "bearer",
        "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
    }
    token = schemas.Token(**token_data)
    assert token.access_token == token_data["access_token"]
    assert token.token_type == token_data["token_type"]
    assert token.refresh_token == token_data["refresh_token"]

def test_login_request_schema():
    # Caso válido
    login_data = {
        "username_or_email": "test@example.com",
        "password": "Test1234!"
    }
    login = schemas.LoginRequest(**login_data)
    assert login.username_or_email == login_data["username_or_email"]
    assert login.password == login_data["password"]

def test_password_reset_request_schema():
    # Caso válido
    reset_data = {
        "email": "test@example.com"
    }
    reset = schemas.PasswordResetRequest(**reset_data)
    assert reset.email == reset_data["email"]
    
    # Email inválido
    with pytest.raises(ValidationError):
        schemas.PasswordResetRequest(email="invalid_email")

def test_password_reset_schema():
    # Caso válido
    reset_data = {
        "token": "valid_token",
        "new_password": "ValidPassword123!"
    }
    reset = schemas.PasswordReset(**reset_data)
    assert reset.token == reset_data["token"]
    assert reset.new_password == reset_data["new_password"]
    
    # Contraseña insegura
    with pytest.raises(ValidationError):
        schemas.PasswordReset(
            token="valid_token",
            new_password="password"  # Contraseña simple
        ) 