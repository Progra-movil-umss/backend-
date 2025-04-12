from pydantic_settings import BaseSettings

class AuthSettings(BaseSettings):
    # JWT settings
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Password settings
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_MAX_LENGTH: int = 100
    
    class Config:
        env_prefix = "AUTH_"
        env_file = ".env" 