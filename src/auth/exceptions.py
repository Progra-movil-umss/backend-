from fastapi import HTTPException, status

class AuthException(HTTPException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )

class InvalidCredentialsException(AuthException):
    def __init__(self):
        super().__init__(detail="Invalid credentials")

class UserNotFoundException(AuthException):
    def __init__(self):
        super().__init__(detail="User not found")

class UserAlreadyExistsException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists"
        )

class InvalidTokenException(AuthException):
    def __init__(self):
        super().__init__(detail="Invalid token")

class TokenExpiredException(AuthException):
    def __init__(self):
        super().__init__(detail="Token has expired") 