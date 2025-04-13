from fastapi import HTTPException, status

class AuthException(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail=detail)

class InvalidCredentialsException(AuthException):
    def __init__(self):
        super().__init__(
            detail="Credenciales inválidas",
            status_code=status.HTTP_401_UNAUTHORIZED
        )

class UserAlreadyExistsException(AuthException):
    def __init__(self):
        super().__init__(
            detail="El usuario ya existe",
            status_code=status.HTTP_400_BAD_REQUEST
        )

class UserNotFoundException(AuthException):
    def __init__(self):
        super().__init__(
            detail="Usuario no encontrado",
            status_code=status.HTTP_404_NOT_FOUND
        )

class InvalidTokenException(AuthException):
    def __init__(self):
        super().__init__(
            detail="Token inválido",
            status_code=status.HTTP_401_UNAUTHORIZED
        )

class TokenExpiredException(AuthException):
    def __init__(self):
        super().__init__(
            detail="Token expirado",
            status_code=status.HTTP_401_UNAUTHORIZED
        )

class PasswordHistoryException(AuthException):
    def __init__(self):
        super().__init__(
            detail="Esta contraseña ya ha sido utilizada anteriormente",
            status_code=status.HTTP_400_BAD_REQUEST
        ) 