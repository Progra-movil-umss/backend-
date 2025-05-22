import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.sql import func
from src.database import Base

class PlantNote(Base):
    __tablename__ = "plant_notes"

    id = Column(PGUUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    plant_id = Column(PGUUID(as_uuid=True), ForeignKey("plants.id", ondelete="CASCADE"), nullable=False)
    text = Column(String, nullable=False)
    observation_date = Column(DateTime(timezone=True), nullable=False, default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    plant = relationship("Plant", back_populates="notes")
