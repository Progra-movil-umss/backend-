from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from src.auth import service, schemas, exceptions
from src.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

templates = Jinja2Templates(directory="src/templates")

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
    user = service.authenticate_user(db, login_data.email, login_data.password)
    if not user:
        raise exceptions.InvalidCredentialsException()

    access_token = service.create_access_token(
        data={"sub": user.username}
    )
    refresh_token = service.create_refresh_token(
        data={"sub": user.username}
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
            data={"sub": user.username}
        )
        new_refresh_token = service.create_refresh_token(
            data={"sub": user.username}
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
    service.request_password_reset(db, reset_request.email)
    return {"message": "Si el correo existe, se ha enviado un enlace para restablecer la contraseña"}

@router.get("/password-reset", response_class=HTMLResponse)
def get_password_reset_form(request: Request, token: str) -> Any:
    return templates.TemplateResponse("email/reset_password.html", {"request": request, "token": token})

@router.post("/password-reset")
def reset_password(
    reset_data: schemas.PasswordReset,
    db: Session = Depends(get_db)
) -> Any:
    try:
        service.reset_password(db, reset_data.token, reset_data.new_password)
        return {"message": "Contraseña actualizada exitosamente"}
    except (exceptions.InvalidTokenException, exceptions.TokenExpiredException, exceptions.PasswordHistoryException) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/me", response_model=schemas.User)
def read_users_me(
    current_user: schemas.User = Depends(service.get_current_user)
) -> Any:
    return current_user

@router.put("/me", response_model=schemas.User)
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