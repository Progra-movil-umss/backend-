from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, validator


class SimplePlantResponse(BaseModel):
    id: UUID
    alias: str
    image_url: Optional[str] = None
    scientific_name_without_author: str
    genus: str
    family: str
    common_names: List[str]

    class Config:
        from_attributes = True


class GardenBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=100, description="Nombre del jardín (entre 3 y 100 caracteres)")
    description: Optional[str] = Field(None, max_length=1000, description="Descripción del jardín (máximo 1000 caracteres)")
    image_url: Optional[str] = Field(None, description="URL de la imagen del jardín")
    
    @validator('name')
    def name_must_not_be_empty(cls, v):
        v = v.strip() if v else v
        if not v:
            raise ValueError('El nombre del jardín no puede estar vacío')
        return v


class GardenCreate(GardenBase):
    pass


class GardenUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=100, description="Nombre del jardín (entre 3 y 100 caracteres)")
    description: Optional[str] = Field(None, max_length=1000, description="Descripción del jardín (máximo 1000 caracteres)")
    image_url: Optional[str] = Field(None, description="URL de la imagen del jardín")
    
    @validator('name')
    def name_must_not_be_empty(cls, v):
        if v is not None:
            v = v.strip() if v else v
            if not v:
                raise ValueError('El nombre del jardín no puede estar vacío')
        return v


class GardenResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    plants: List[SimplePlantResponse] = []

    class Config:
        from_attributes = True


class GardenWithUserResponse(GardenResponse):
    user: Dict[str, Any]


class GardenListResponse(BaseModel):
    items: List[GardenResponse]
    total: int


class SimpleGardenResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    plant_count: int = 0

    class Config:
        from_attributes = True


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
    
    # Datos de identificación específicos
    scientific_name_without_author: Optional[str] = None
    genus: Optional[str] = None
    family: Optional[str] = None
    common_names: Optional[List[str]] = None


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


class PlantInGardenCreate(PlantBase):
    pass