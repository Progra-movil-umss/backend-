from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from fastapi import UploadFile

class OrganType(str, Enum):
    AUTO = "auto"
    LEAF = "leaf"
    FLOWER = "flower"
    FRUIT = "fruit"
    BARK = "bark"
    HABIT = "habit"
    OTHER = "other"

class IdentificationRequestForm(BaseModel):
    image: UploadFile
    organ: str = Field(default=OrganType.AUTO, description="Órgano de la planta en la imagen")
    include_related_images: bool = Field(default=True, description="Incluir imágenes relacionadas en los resultados")
    lang: str = Field(default="es", description="Idioma para los resultados (siempre español)")
    
    class Config:
        arbitrary_types_allowed = True

class Result(BaseModel):
    score: float
    species: Dict[str, Any]
    gbif: Dict[str, Any]
    
class IdentificationResponse(BaseModel):
    results: List[Result] = Field(..., description="Lista de posibles especies identificadas")
    language: str = Field(..., description="Idioma de los resultados")
    preferedReferential: Optional[str] = Field(None, description="Referencial preferido")
    version: str = Field(..., description="Versión de la API")
    remainingIdentificationRequests: int = Field(..., description="Solicitudes de identificación restantes")
    language: str = Field(..., description="Idioma de los resultados") 