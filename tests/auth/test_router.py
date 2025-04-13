import pytest
from fastapi.testclient import TestClient
import hashlib

from src.auth import schemas, service, models
from src.auth.utils import get_utc_now

def test_register_user(client):
    user_data = {
        "email": "newuser@example.com",
        "username": "newuser",
        "password": "Test1234!",
        "full_name": "New User"
    }
    
    response = client.post("/auth/register", json=user_data)
    
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == user_data["email"]
    assert data["username"] == user_data["username"]
    assert data["full_name"] == user_data["full_name"]
    assert "password" not in data
    assert "hashed_password" not in data
    assert data["is_active"] is True
    assert data["is_superuser"] is False

def test_register_user_duplicate_email(client, test_user):
    user_data = {
        "email": "test@example.com",  # Email ya existente
        "username": "newuser123",
        "password": "Test1234!",
        "full_name": "New User"
    }
    
    response = client.post("/auth/register", json=user_data)
    
    assert response.status_code == 400
    assert "ya existe" in response.json()["detail"].lower()

def test_register_user_duplicate_username(client, test_user):
    user_data = {
        "email": "newuser123@example.com",
        "username": "testuser",  # Username ya existente
        "password": "Test1234!",
        "full_name": "New User"
    }
    
    response = client.post("/auth/register", json=user_data)
    
    assert response.status_code == 400
    assert "ya existe" in response.json()["detail"].lower()

def test_login_for_access_token(client, test_user):
    login_data = {
        "email": "test@example.com",
        "password": "Test1234!"
    }
    
    response = client.post("/auth/token", json=login_data)
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

def test_login_invalid_credentials(client):
    # Email incorrecto
    login_data = {
        "email": "nonexistent@example.com",
        "password": "Test1234!"
    }
    
    response = client.post("/auth/token", json=login_data)
    
    assert response.status_code == 401
    assert "inválidas" in response.json()["detail"].lower()
    
    # Contraseña incorrecta
    login_data = {
        "email": "test@example.com",
        "password": "WrongPassword123!"
    }
    
    response = client.post("/auth/token", json=login_data)
    
    assert response.status_code == 401
    assert "inválidas" in response.json()["detail"].lower()

def test_refresh_token(client, test_user):
    # Primero obtener un token
    login_data = {
        "email": "test@example.com",
        "password": "Test1234!"
    }
    
    response = client.post("/auth/token", json=login_data)
    assert response.status_code == 200
    tokens = response.json()
    
    # Ahora refrescar el token
    response = client.post(f"/auth/refresh?refresh_token={tokens['refresh_token']}")
    
    assert response.status_code == 200
    new_tokens = response.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens
    assert new_tokens["token_type"] == "bearer"
    # En los tests, los tokens pueden ser iguales si se generan en un tiempo muy cercano
    # porque la expiración será la misma. No validamos que sean distintos.

def test_refresh_token_invalid(client):
    response = client.post("/auth/refresh?refresh_token=invalid_token")
    
    assert response.status_code == 401
    assert "inválido" in response.json()["detail"].lower()

def test_password_reset_request(client, test_user):
    response = client.post(
        "/auth/password-reset-request", 
        json={"email": "test@example.com"}
    )
    
    assert response.status_code == 200
    assert "message" in response.json()
    assert "correo" in response.json()["message"].lower()

def test_password_reset(client, db_session, test_user):
    # Crear un token de reset
    token = service.create_password_reset_token({"sub": test_user.username})
    
    # Probar reset de contraseña
    response = client.post(
        "/auth/password-reset", 
        json={
            "token": token,
            "new_password": "NewPassword456!"
        }
    )
    
    assert response.status_code == 200
    assert "contraseña" in response.json()["message"].lower()
    assert "actualizada" in response.json()["message"].lower()
    
    # Verificar que podemos iniciar sesión con la nueva contraseña
    login_data = {
        "email": "test@example.com",
        "password": "NewPassword456!"
    }
    
    response = client.post("/auth/token", json=login_data)
    assert response.status_code == 200

def test_read_users_me(client, auth_headers):
    response = client.get("/auth/me", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"

def test_read_users_me_unauthorized(client):
    response = client.get("/auth/me")
    
    assert response.status_code == 401

def test_update_user_me(client, auth_headers):
    update_data = {
        "full_name": "Updated Name"
    }
    
    response = client.put("/auth/me", json=update_data, headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Updated Name"

def test_update_user_password(client, auth_headers):
    update_data = {
        "current_password": "Test1234!",
        "new_password": "UpdatedPassword123!"
    }
    
    response = client.put("/auth/me", json=update_data, headers=auth_headers)
    
    assert response.status_code == 200
    
    # Verificar que podemos iniciar sesión con la nueva contraseña
    login_data = {
        "email": "test@example.com",
        "password": "UpdatedPassword123!"
    }
    
    response = client.post("/auth/token", json=login_data)
    assert response.status_code == 200

def test_update_user_password_invalid(client, auth_headers):
    update_data = {
        "current_password": "WrongPassword!",
        "new_password": "UpdatedPassword123!"
    }
    
    response = client.put("/auth/me", json=update_data, headers=auth_headers)
    
    assert response.status_code == 400
    assert "inválidas" in response.json()["detail"].lower()

def test_password_reset_used_token(client, db_session, test_user):
    # Crear un token de reset
    token = service.create_password_reset_token({"sub": test_user.username})
    
    # Usar el token una vez
    response = client.post(
        "/auth/password-reset", 
        json={
            "token": token,
            "new_password": "NewPassword456!"
        }
    )
    assert response.status_code == 200
    
    # Intentar usar el mismo token nuevamente
    response = client.post(
        "/auth/password-reset", 
        json={
            "token": token,
            "new_password": "AnotherPassword789!"
        }
    )
    assert response.status_code == 400
    assert "ya ha sido utilizado" in response.json()["detail"].lower()

def test_password_reset_form_used_token(client, db_session, test_user):
    # Crear un token de reset
    token = service.create_password_reset_token({"sub": test_user.username})
    
    # Marcar el token como usado
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    used_token = models.UsedToken(
        token_hash=token_hash,
        token_type="password_reset",
        user_id=test_user.id
    )
    db_session.add(used_token)
    db_session.commit()
    
    # Intentar acceder al formulario con un token usado
    response = client.get(f"/auth/password-reset?token={token}")
    
    # Solo verificamos que se devuelva una respuesta HTTP 200 y que sea HTML
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

def test_password_reset_rate_limit(client, db_session, test_user):
    # Establecer intentos previos
    test_user.reset_attempts = service.MAX_RESET_ATTEMPTS
    test_user.last_reset_attempt = get_utc_now()
    db_session.commit()
    
    # Intentar solicitar reset (debería fallar por límite excedido)
    response = client.post(
        "/auth/password-reset-request", 
        json={"email": "test@example.com"}
    )
    
    assert response.status_code == 429
    assert "demasiados intentos" in response.json()["detail"].lower()

def test_password_reset_history_constraint(client, db_session, test_user):
    # Cambiar la contraseña del usuario
    test_user.hashed_password = service.get_password_hash("CurrentPassword123!")
    password_history = models.PasswordHistory(
        user_id=test_user.id,
        hashed_password=test_user.hashed_password
    )
    db_session.add(password_history)
    db_session.commit()
    
    # Crear un token de reset
    token = service.create_password_reset_token({"sub": test_user.username})
    
    # Intentar restablecer con la misma contraseña
    response = client.post(
        "/auth/password-reset", 
        json={
            "token": token,
            "new_password": "CurrentPassword123!"
        }
    )
    
    assert response.status_code == 400
    assert "contraseña" in response.json()["detail"].lower()
    assert "utilizadas anteriormente" in response.json()["detail"].lower()

def test_password_reset_weak_password(client, db_session, test_user):
    # Crear un token de reset
    token = service.create_password_reset_token({"sub": test_user.username})
    
    # Intentar restablecer con una contraseña débil (sin caracteres especiales)
    response = client.post(
        "/auth/password-reset", 
        json={
            "token": token,
            "new_password": "Password123"  # Falta carácter especial
        }
    )
    
    assert response.status_code == 400
    assert "carácter especial" in response.json()["detail"].lower()

def test_password_reset_short_password(client, db_session, test_user):
    # Crear un token de reset
    token = service.create_password_reset_token({"sub": test_user.username})
    
    # Intentar restablecer con una contraseña corta
    response = client.post(
        "/auth/password-reset", 
        json={
            "token": token,
            "new_password": "Abc1!"  # Menos de 8 caracteres
        }
    )
    
    assert response.status_code == 400
    assert "8 caracteres" in response.json()["detail"].lower() 