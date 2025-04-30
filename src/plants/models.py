import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.sql import func

from src.database import Base


class Plant(Base):
    __tablename__ = "plants"

    id = Column(PGUUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    alias = Column(String, nullable=False, index=True)
    image_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    garden_id = Column(PGUUID(as_uuid=True), ForeignKey("gardens.id", ondelete="CASCADE"), nullable=False)
    
    scientific_name_without_author = Column(String, nullable=False)
    genus = Column(String, nullable=False)
    family = Column(String, nullable=False)
    common_names = Column(JSON, nullable=False)
    
    user = relationship("User", back_populates="plants")
    garden = relationship("Garden", back_populates="plants")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'alias', name='uk_user_plant_alias'),
        {"sqlite_autoincrement": True}
    ) 