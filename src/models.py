from sqlalchemy import Column, DateTime
from sqlalchemy.sql import func

from src.database import Base

class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# Import all models to ensure they are registered with SQLAlchemy
from src.auth.models import User
from src.posts.models import Post

# Update User model to include posts relationship
User.posts = relationship("Post", back_populates="user") 