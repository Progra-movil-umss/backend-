from datetime import timedelta
from typing import Any
import hashlib

from fastapi import APIRouter, Depends, HTTPException, Request, status, Security
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from jose import jwt

from src.auth import service, schemas, exceptions, models
from src.database import get_db
from src.config import get_settings
from src.validators.password import validate_password

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()

templates = Jinja2Templates(directory="src/templates")

settings = get_settings()

@router.post("/register", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)) -> Any:
    try:
        return service.create_user(db=db, user=user)
    except exceptions.UserAlreadyExistsException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/token", response_model=schemas.Token)
def login_for_access_token(
    login_data: schemas.LoginRequest,
    db: Session = Depends(get_db)
) -> Any:
    user = service.authenticate_user(db, login_data.username_or_email, login_data.password)
    if not user:
        raise exceptions.InvalidCredentialsException()

    access_token = service.create_access_token(
        data={"sub": str(user.id)}
    )
    refresh_token = service.create_refresh_token(
        data={"sub": str(user.id)}
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token
    }

@router.post("/refresh", response_model=schemas.Token)
def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
) -> Any:
    try:
        user = service.get_user_from_token(db, refresh_token)
        access_token = service.create_access_token(
            data={"sub": str(user.id)}
        )
        new_refresh_token = service.create_refresh_token(
            data={"sub": str(user.id)}
        )
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "refresh_token": new_refresh_token
        }
    except (exceptions.InvalidTokenException, exceptions.TokenExpiredException) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

@router.post("/password-reset-request")
def request_password_reset(
    reset_request: schemas.PasswordResetRequest,
    db: Session = Depends(get_db)
) -> Any:
    """
    Endpoint para solicitar el restablecimiento de contraseña.
    Recibe un email y envía un enlace de restablecimiento si el usuario existe.
    """
    try:
        service.request_password_reset(db, reset_request.email)
        return {"message": "Si el correo existe, se ha enviado un enlace para restablecer la contraseña"}
    except exceptions.RateLimitException as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e)
        )

@router.get("/password-reset", response_class=HTMLResponse)
def get_password_reset_form(request: Request, token: str) -> Any:
    """
    Endpoint para mostrar el formulario de restablecimiento de contraseña.
    Valida el token antes de mostrar el formulario.
    """
    try:
        # Validar el token y obtener información para la respuesta
        template_data = service.validate_password_reset_form_token(token)
        
        # Si el token es válido, mostrar el formulario
        if "error" not in template_data:
            return templates.TemplateResponse(
                request,
                "email/reset_password.html", 
                {"token": token}
            )
        
        # Si hay error, mostrar página de error
        return templates.TemplateResponse(
            request,
            "email/reset_password_error.html", 
            template_data
        )
    except jwt.ExpiredSignatureError:
        return templates.TemplateResponse(
            request,
            "email/reset_password_error.html", 
            {
                "title": "Enlace invalido",
                "message": "Este enlace de restablecimiento de contraseña ha expirado o ya fue usado. Por favor, solicita uno nuevo."
            }
        )
    except jwt.JWTError:
        return templates.TemplateResponse(
            request,
            "email/reset_password_error.html", 
            {
                "title": "Enlace inválido", 
                "message": "Este enlace de restablecimiento de contraseña no es válido o ha sido modificado."
            }
        )

@router.post("/password-reset")
async def reset_password(
    request: Request,
    db: Session = Depends(get_db)
) -> Any:
    """
    Endpoint para restablecer la contraseña usando un token.
    
    Recibe:
    - token: Token de restablecimiento de contraseña
    - new_password: Nueva contraseña
    
    Realiza validaciones de longitud y seguridad de la contraseña.
    """
    try:
        body = await request.json()
        
        if "token" not in body or "new_password" not in body:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Falta el token o la nueva contraseña"
            )
            
        token = body["token"]
        new_password = body["new_password"]
        
        # Todas las validaciones de contraseña ahora están en service.reset_password
        service.reset_password(db, token, new_password)
        return {"message": "Contraseña actualizada exitosamente"}
        
    except (exceptions.InvalidTokenException, exceptions.TokenExpiredException, 
            exceptions.PasswordHistoryException, exceptions.InvalidPasswordException) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/me", response_model=schemas.User, 
            responses={401: {"description": "No autorizado"}},
            summary="Obtener perfil de usuario actual")
def read_users_me(
    current_user: schemas.User = Depends(service.get_current_user)
) -> Any:
    return current_user

@router.put("/me", response_model=schemas.User,
           responses={401: {"description": "No autorizado"}, 400: {"description": "Datos inválidos"}},
           summary="Actualizar perfil de usuario")
def update_user_me(
    user_update: schemas.UserUpdate,
    current_user: schemas.User = Depends(service.get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    try:
        return service.update_user(
            db=db,
            user_id=current_user.id,
            user_update=user_update,
            current_password=user_update.current_password
        )
    except (exceptions.InvalidCredentialsException, exceptions.PasswordHistoryException) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )