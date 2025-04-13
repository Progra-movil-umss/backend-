import pytest
from fastapi import status

from src.auth import exceptions

def test_auth_exception_base():
    exception = exceptions.AuthException("Mensaje de error personalizado")
    assert exception.status_code == status.HTTP_400_BAD_REQUEST
    assert exception.detail == "Mensaje de error personalizado"
    
    # Probar con código de estado personalizado
    exception = exceptions.AuthException(
        "Mensaje de error personalizado", 
        status_code=status.HTTP_403_FORBIDDEN
    )
    assert exception.status_code == status.HTTP_403_FORBIDDEN
    assert exception.detail == "Mensaje de error personalizado"

def test_invalid_credentials_exception():
    exception = exceptions.InvalidCredentialsException()
    assert exception.status_code == status.HTTP_401_UNAUTHORIZED
    assert "credenciales inválidas" in exception.detail.lower()

def test_user_already_exists_exception():
    exception = exceptions.UserAlreadyExistsException()
    assert exception.status_code == status.HTTP_400_BAD_REQUEST
    assert "ya existe" in exception.detail.lower()

def test_user_not_found_exception():
    exception = exceptions.UserNotFoundException()
    assert exception.status_code == status.HTTP_404_NOT_FOUND
    assert "no encontrado" in exception.detail.lower()

def test_invalid_token_exception():
    exception = exceptions.InvalidTokenException()
    assert exception.status_code == status.HTTP_401_UNAUTHORIZED
    assert "inválido" in exception.detail.lower()

def test_token_expired_exception():
    exception = exceptions.TokenExpiredException()
    assert exception.status_code == status.HTTP_401_UNAUTHORIZED
    assert "expirado" in exception.detail.lower()

def test_password_history_exception():
    exception = exceptions.PasswordHistoryException()
    assert exception.status_code == status.HTTP_400_BAD_REQUEST
    assert "contraseña" in exception.detail.lower()
    assert "utilizadas" in exception.detail.lower() 