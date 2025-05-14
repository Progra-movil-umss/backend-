from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional, Dict, Any, List, Union
from pydantic import PostgresDsn, validator, Field

class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Project"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: str = "5432"
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7 
    
    # Email
    SMTP_SERVER: str
    SMTP_PORT: int
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    SENDER_EMAIL: str
    URL: str

    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30
    PASSWORD_HISTORY_SIZE: int = 5
    
    # PlantNet API
    PLANTNET_API_URL: str
    PLANTNET_API_KEY: str
    PLANTNET_MAX_IMAGES: int
    PLANTNET_MAX_IMAGE_SIZE: int
    PLANTNET_INCLUDE_RELATED: bool
    PLANTNET_LANGUAGE: str
    PLANTNET_NB_RESULTS: int
    
    DO_SPACES_KEY: str
    DO_SPACES_SECRET: str
    DO_SPACES_ENDPOINT: str
    DO_SPACES_CDN_ENDPOINT: Optional[str] = None
    DO_SPACES_REGION: str
    DO_SPACES_BUCKET: str
    DO_SPACES_MAX_IMAGE_SIZE: int = 10 * 1024 * 1024  # 10MB default limit
    
    # Configuración de correo electrónico
    EMAIL_HOST: str = "smtp.gmail.com"
    EMAIL_PORT: int = 465
    EMAIL_USERNAME: str = "your-email@gmail.com"
    EMAIL_PASSWORD: str = "your-app-password"
    EMAIL_SENDER: str = "Flora Find <noreply@florafind.com>"
    
    # Configuración de Push Notifications (Expo)
    EXPO_ACCESS_TOKEN: Optional[str] = None
    
    # URL base de la aplicación (para enlaces en correos)
    BASE_URL: str = "https://florafind.com"
    MOBILE_APP_URL: str = "florafind://"
    
    # Temporizador para verificación de recordatorios (minutos)
    REMINDER_CHECK_INTERVAL: int = 15
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings() 