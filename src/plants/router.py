from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body, UploadFile, File
from sqlalchemy.orm import Session

from src.auth.schemas import User
from src.auth.service import get_current_user
from src.database import get_db
from src.plants.schemas import (
    PlantCreate, PlantUpdate, PlantResponse, PlantListResponse
)
from src.plants.service import (
    create_plant, get_plant, get_plants, update_plant, delete_plant
)

router = APIRouter()


@router.post(
    "",
    response_model=PlantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una planta",
    description="Crea una nueva planta para el usuario autenticado."
)
async def create_plant_endpoint(
    plant_data: PlantCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return create_plant(db, current_user.id, plant_data)


@router.get(
    "/{plant_id}",
    response_model=PlantResponse,
    summary="Obtener una planta",
    description="Obtiene una planta específica por su ID."
)
async def get_plant_endpoint(
    plant_id: UUID = Path(..., description="ID de la planta"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return get_plant(db, plant_id, current_user.id)


@router.get(
    "",
    response_model=PlantListResponse,
    summary="Listar plantas",
    description="Lista las plantas del usuario autenticado."
)
async def list_plants_endpoint(
    skip: int = Query(0, description="Número de registros a saltar para paginación"),
    limit: int = Query(10, description="Número máximo de registros a devolver"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return get_plants(db, current_user.id, skip, limit)


@router.put(
    "/{plant_id}",
    response_model=PlantResponse,
    summary="Actualizar una planta",
    description="Actualiza una planta existente propiedad del usuario autenticado."
)
async def update_plant_endpoint(
    plant_data: PlantUpdate,
    plant_id: UUID = Path(..., description="ID de la planta"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return update_plant(db, plant_id, current_user.id, plant_data)


@router.delete(
    "/{plant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar una planta",
    description="Elimina una planta existente propiedad del usuario autenticado."
)
async def delete_plant_endpoint(
    plant_id: UUID = Path(..., description="ID de la planta"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    delete_plant(db, plant_id, current_user.id)
    return None 