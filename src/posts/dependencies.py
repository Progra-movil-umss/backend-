from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.database import get_db
from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.posts import models

def get_post_or_404(
    post_id: int,
    db: Session = Depends(get_db)
) -> models.Post:
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    return post

def verify_post_owner(
    post: models.Post = Depends(get_post_or_404),
    current_user: User = Depends(get_current_user)
) -> models.Post:
    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return post 