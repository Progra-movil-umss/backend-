from pydantic_settings import BaseSettings
from functools import lru_cache

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
    FRONTEND_URL: str = "http://localhost:8000"

    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 1
    PASSWORD_HISTORY_SIZE: int = 5
    
    # PlantNet API
    PLANTNET_API_URL: str
    PLANTNET_API_KEY: str
    PLANTNET_MAX_IMAGES: int
    PLANTNET_MAX_IMAGE_SIZE: int
    PLANTNET_INCLUDE_RELATED: bool
    PLANTNET_LANGUAGE: str
    PLANTNET_NB_RESULTS: int
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings() 