from sqlalchemy import Column, DateTime, Integer, String, ForeignKey, Text, Boolean, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from src.database import Base

class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# Import all models to ensure they are registered with SQLAlchemy
from src.auth.models import User, PasswordHistory, UsedToken
from src.gardens.models import Garden
from src.plants.models import Plant

class SoundType(str, enum.Enum):
    WATER = "water"
    FERTILIZE = "fertilize"
    PRUNE = "prune"
    REPOT = "repot"
    HARVEST = "harvest"
    CUSTOM = "custom"

class NotificationType(str, enum.Enum):
    PUSH = "push"
    EMAIL = "email"
    BOTH = "both"

class ReminderFrequency(str, enum.Enum):
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"

class Reminder(Base):
    __tablename__ = "reminders"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)
    frequency = Column(Enum(ReminderFrequency), default=ReminderFrequency.ONCE)
    sound_type = Column(Enum(SoundType), default=SoundType.WATER)
    notification_type = Column(Enum(NotificationType), default=NotificationType.BOTH)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)
    
    # Relaciones
    user = relationship("User", back_populates="reminders")
    plant_reminders = relationship("PlantReminder", back_populates="reminder", cascade="all, delete-orphan")
    garden_reminders = relationship("GardenReminder", back_populates="reminder", cascade="all, delete-orphan")

class PlantReminder(Base):
    __tablename__ = "plant_reminders"
    
    id = Column(Integer, primary_key=True, index=True)
    reminder_id = Column(Integer, ForeignKey("reminders.id"), nullable=False)
    plant_id = Column(String, ForeignKey("plants.id"), nullable=False)
    
    # Relaciones
    reminder = relationship("Reminder", back_populates="plant_reminders")
    plant = relationship("Plant", back_populates="reminders")

class GardenReminder(Base):
    __tablename__ = "garden_reminders"
    
    id = Column(Integer, primary_key=True, index=True)
    reminder_id = Column(Integer, ForeignKey("reminders.id"), nullable=False)
    garden_id = Column(String, ForeignKey("gardens.id"), nullable=False)
    
    # Relaciones
    reminder = relationship("Reminder", back_populates="garden_reminders")
    garden = relationship("Garden", back_populates="reminders")