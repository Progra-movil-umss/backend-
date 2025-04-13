from datetime import datetime, timedelta
from typing import Optional, Tuple
import secrets

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from src.auth import models, schemas, email, exceptions, utils
from src.config import get_settings
from src.database import get_db

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
email_service = email.EmailService()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

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
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        return False
    
    reset_token = create_password_reset_token({"sub": user.username})
    return email_service.send_password_reset_email(email, reset_token)

def reset_password(db: Session, token: str, new_password: str) -> bool:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "password_reset":
            raise exceptions.InvalidTokenException()
        
        username: str = payload.get("sub")
        if username is None:
            raise exceptions.InvalidTokenException()
        
        user = db.query(models.User).filter(models.User.username == username).first()
        if not user:
            raise exceptions.UserNotFoundException()
        
        hashed_new_password = get_password_hash(new_password)
        recent_passwords = db.query(models.PasswordHistory).filter(
            models.PasswordHistory.user_id == user.id
        ).order_by(models.PasswordHistory.created_at.desc()).limit(
            settings.PASSWORD_HISTORY_SIZE
        ).all()
        
        for old_password in recent_passwords:
            if verify_password(new_password, old_password.hashed_password):
                raise exceptions.PasswordHistoryException()
        
        user.hashed_password = hashed_new_password
        password_history = models.PasswordHistory(
            user_id=user.id,
            hashed_password=hashed_new_password
        )
        db.add(password_history)
        db.commit()
        
        return True
    except jwt.ExpiredSignatureError:
        raise exceptions.TokenExpiredException()
    except jwt.JWTError:
        raise exceptions.InvalidTokenException()

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