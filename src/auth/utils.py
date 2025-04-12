import re
from typing import Optional

from src.auth import constants

def validate_password(password: str) -> Optional[str]:
    if len(password) < 8:
        return constants.PASSWORD_TOO_SHORT
    if len(password) > 100:
        return constants.PASSWORD_TOO_LONG
    return None

def validate_email(email: str) -> Optional[str]:
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email):
        return constants.INVALID_EMAIL
    return None

def validate_username(username: str) -> Optional[str]:
    username_regex = r'^[a-zA-Z0-9_-]{3,20}$'
    if not re.match(username_regex, username):
        return constants.INVALID_USERNAME
    return None 