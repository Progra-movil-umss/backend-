import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from typing import Generator, Dict, Any

from src.database import Base, get_db
from src.main import app
from src.auth import models, schemas, service

# Motor de base de datos en memoria para pruebas
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture
def db_engine():
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session(db_engine):
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def test_user(db_session):
    user_data = schemas.UserCreate(
        email="test@example.com",
        username="testuser",
        password="Test1234!"
    )
    user = service.create_user(db=db_session, user=user_data)
    return user

@pytest.fixture
def test_user_token(test_user):
    access_token = service.create_access_token(data={"sub": test_user.username})
    return access_token

@pytest.fixture
def test_superuser(db_session):
    user_data = schemas.UserCreate(
        email="admin@example.com",
        username="adminuser",
        password="Admin1234!"
    )
    user = service.create_user(db=db_session, user=user_data)
    # Convertir en superusuario
    user.is_superuser = True
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def test_superuser_token(test_superuser):
    access_token = service.create_access_token(data={"sub": test_superuser.username})
    return access_token

@pytest.fixture
def auth_headers(test_user_token):
    return {"Authorization": f"Bearer {test_user_token}"}

@pytest.fixture
def admin_headers(test_superuser_token):
    return {"Authorization": f"Bearer {test_superuser_token}"} 