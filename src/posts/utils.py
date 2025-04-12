from typing import Optional

from src.posts import constants

def validate_title(title: str) -> Optional[str]:
    if len(title) < 3:
        return constants.TITLE_TOO_SHORT
    if len(title) > 100:
        return constants.TITLE_TOO_LONG
    return None

def validate_content(content: str) -> Optional[str]:
    if len(content) < 10:
        return constants.CONTENT_TOO_SHORT
    if len(content) > 5000:
        return constants.CONTENT_TOO_LONG
    return None 