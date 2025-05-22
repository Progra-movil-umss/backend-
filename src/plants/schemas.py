from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, validator


class PlantBase(BaseModel):
    alias: str = Field(..., max_length=100, description="Alias único para la planta")
    image_url: Optional[str] = Field(None, description="URL de la imagen de la planta")
    
    scientific_name_without_author: str = Field(..., description="Nombre científico sin autor")
    genus: str = Field(..., description="Género de la planta")
    family: str = Field(..., description="Familia de la planta")
    common_names: List[str] = Field(..., description="Nombres comunes de la planta")


class PlantCreate(PlantBase):
    garden_id: UUID = Field(..., description="ID del jardín donde se ubicará la planta")


class PlantUpdate(BaseModel):
    alias: Optional[str] = Field(None, max_length=100, description="Alias único para la planta")
    image_url: Optional[str] = Field(None, description="URL de la imagen de la planta")
    
    scientific_name_without_author: Optional[str] = None
    genus: Optional[str] = None
    family: Optional[str] = None
    common_names: Optional[List[str]] = None


class SimpleGardenInfo(BaseModel):
    id: UUID
    name: str

    class Config:
        from_attributes = True


class PlantResponse(BaseModel):
    id: UUID
    garden_id: UUID
    user_id: UUID
    alias: str
    image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    scientific_name_without_author: str
    genus: str
    family: str
    common_names: List[str]

    class Config:
        from_attributes = True


class PlantWithGardenResponse(PlantResponse):
    garden_name: str


class PlantListResponse(BaseModel):
    items: List[PlantResponse]
    total: int