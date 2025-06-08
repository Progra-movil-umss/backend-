from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field

class PlantNoteBase(BaseModel):
    text: str = Field(..., description="Texto de la nota/observación")
    color: Optional[str] = Field(None, description="Color de la nota (ej: 'red', 'blue', 'green')")
    observation_date: datetime = Field(..., description="Fecha de la observación o evento importante")

class PlantNoteCreate(PlantNoteBase):
    pass

class PlantNoteUpdate(BaseModel):
    text: Optional[str] = Field(None, description="Texto de la nota/observación")
    color: Optional[str] = Field(None, description="Color de la nota (ej: 'red', 'blue', 'green')")
    observation_date: Optional[datetime] = Field(None, description="Fecha de la observación o evento importante")

class PlantNoteResponse(PlantNoteBase):
    id: UUID
    plant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
