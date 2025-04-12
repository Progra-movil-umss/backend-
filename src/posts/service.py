from typing import List, Optional
from sqlalchemy.orm import Session

from src.posts import models, schemas
from src.posts.exceptions import (
    PostCreateException,
    PostUpdateException,
    PostDeleteException
)

def create_post(db: Session, post: schemas.PostCreate, user_id: int) -> models.Post:
    try:
        db_post = models.Post(**post.model_dump(), user_id=user_id)
        db.add(db_post)
        db.commit()
        db.refresh(db_post)
        return db_post
    except Exception as e:
        db.rollback()
        raise PostCreateException(str(e))

def get_posts(db: Session, skip: int = 0, limit: int = 100) -> List[models.Post]:
    return db.query(models.Post).offset(skip).limit(limit).all()

def get_post(db: Session, post_id: int) -> Optional[models.Post]:
    return db.query(models.Post).filter(models.Post.id == post_id).first()

def update_post(
    db: Session,
    post_id: int,
    post: schemas.PostUpdate,
    user_id: int
) -> Optional[models.Post]:
    try:
        db_post = db.query(models.Post).filter(
            models.Post.id == post_id,
            models.Post.user_id == user_id
        ).first()
        
        if not db_post:
            return None
            
        update_data = post.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_post, key, value)
            
        db.commit()
        db.refresh(db_post)
        return db_post
    except Exception as e:
        db.rollback()
        raise PostUpdateException(str(e))

def delete_post(db: Session, post_id: int, user_id: int) -> bool:
    try:
        db_post = db.query(models.Post).filter(
            models.Post.id == post_id,
            models.Post.user_id == user_id
        ).first()
        
        if not db_post:
            return False
            
        db.delete(db_post)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise PostDeleteException(str(e)) 