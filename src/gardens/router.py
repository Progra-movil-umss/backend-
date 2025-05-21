from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, UploadFile, File, Form, Body
from sqlalchemy.orm import Session

from src.auth.schemas import User
from src.auth.service import get_current_user
from src.database import get_db
from src.gardens.schemas import (
    GardenCreate, GardenUpdate, GardenResponse, GardenListResponse,
    PlantInGardenCreate
)
from src.plants.schemas import (
    PlantCreate, PlantUpdate, PlantResponse
)
from src.gardens.service import (
    create_garden, get_garden, get_gardens, update_garden, delete_garden,
    add_plant_to_garden, get_garden_plant, get_garden_plants,
    update_garden_plant, delete_garden_plant, count_plants_by_garden,
    upload_garden_image, upload_plant_image, get_plant_by_id, 
    update_plant_by_id, delete_plant_by_id
)
from src.gardens.exceptions import (
    GardenNotFoundException, GardenCreationException, GardenForbiddenException
)
from src.storage.exceptions import (
    FileTooBigException, InvalidFileTypeException, UploadFailedException
)

router = APIRouter()


@router.post(
    "",
    response_model=GardenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un jardín",
    description="Crea un nuevo jardín para el usuario autenticado.",
)
async def create_garden_endpoint(
        name: str = Form(..., description="Nombre del jardín"),
        description: Optional[str] = Form(None, description="Descripción del jardín"),
        image: Optional[UploadFile] = File(None, description="Imagen para el jardín (opcional)"),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    try:
        garden_data = GardenCreate(
            name=name,
            description=description
        )

        if image:
            try:
                image_url = await upload_garden_image(image, current_user.id)
                
                if image_url:
                    garden_data.image_url = image_url
            except (FileTooBigException, InvalidFileTypeException, UploadFailedException) as e:
                raise e

        return create_garden(db, current_user.id, garden_data)
    except Exception as e:
        raise GardenCreationException(str(e))


@router.get(
    "",
    response_model=GardenListResponse,
    summary="Listar jardines",
    description="Lista los jardines del usuario autenticado.",
)
async def list_gardens_endpoint(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    return get_gardens(db, current_user.id)


@router.put(
    "/{garden_id}",
    response_model=Dict[str, Any],
    summary="Actualizar un jardín",
    description="Actualiza un jardín existente propiedad del usuario autenticado.",
)
async def update_garden_endpoint(
        garden_id: UUID = Path(..., description="ID del jardín"),
        name: Optional[str] = Form(None, description="Nombre del jardín"),
        description: Optional[str] = Form(None, description="Descripción del jardín"),
        image: Optional[UploadFile] = File(None, description="Nueva imagen para el jardín (opcional)"),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    try:
        existing_garden = get_garden(db, garden_id, current_user.id)
        
        update_data = {}
        if name is not None and name.strip() != "":
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description

        garden_data = GardenUpdate(**update_data)

        if image and not image.filename == "":
            try:
                image_url = await upload_garden_image(image, current_user.id, garden_id)
                
                if image_url:
                    garden_data.image_url = image_url
            except (FileTooBigException, InvalidFileTypeException, UploadFailedException) as e:
                raise e

        updated_garden = update_garden(db, garden_id, current_user.id, garden_data)
        
        return {
            "message": f"Jardín '{updated_garden.name}' actualizado con éxito",
            "garden": updated_garden
        }
    except Exception as e:
        if "no encontrado" in str(e):
            raise GardenNotFoundException(garden_id)
        if "pertenece" in str(e).lower() or "propiedad" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para actualizar este jardín"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo actualizar el jardín"
        )


@router.delete(
    "/{garden_id}",
    status_code=status.HTTP_200_OK,
    summary="Eliminar un jardín",
    description="Elimina un jardín existente propiedad del usuario autenticado.",
)
async def delete_garden_endpoint(
        garden_id: UUID = Path(..., description="ID del jardín"),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    try:
        garden = get_garden(db, garden_id, current_user.id)
        garden_name = garden.name
        

        delete_garden(db, garden_id, current_user.id)
        return {"message": f"Jardín '{garden_name}' eliminado con éxito"}
    except Exception as e:
        if "no encontrado" in str(e):
            raise GardenNotFoundException(garden_id)
        if "pertenece" in str(e).lower() or "propiedad" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para eliminar este jardín"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo eliminar el jardín"
        )

@router.get(
    "/{garden_id}/plants",
    response_model=Dict[str, Any],
    summary="Listar plantas de un jardín",
    description="Lista todas las plantas de un jardín específico.",
)
async def list_plants_endpoint(
        garden_id: UUID = Path(..., description="ID del jardín"),
        skip: int = Query(0, description="Número de registros a saltar para paginación"),
        limit: int = Query(50, description="Número máximo de registros a devolver"),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    try:
        result = get_garden_plants(db, garden_id, current_user.id, skip, limit)
        if result["total"] == 0:
            return {
                "items": [],
                "total": 0,
                "garden_name": result["garden_name"],
                "message": "Este jardín aún no tiene plantas. ¡Agrega algunas plantas!"
            }
        return result
    except Exception:
        raise GardenNotFoundException(garden_id)


@router.put(
    "/plants/{plant_id}",
    response_model=Dict[str, Any],
    summary="Actualizar una planta",
    description="Actualiza una planta específica propiedad del usuario autenticado.",
)
async def update_plant_endpoint(
        plant_id: UUID = Path(..., description="ID de la planta"),
        alias: Optional[str] = Form(None, description="Alias único para la planta"),
        image: Optional[UploadFile] = File(None, description="Nueva imagen para la planta (opcional)"),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):

    try:
        existing_plant = get_plant_by_id(db, plant_id, current_user.id)
        
        plant_update_data = {}
        
        if alias is not None and alias.strip() != "":
            plant_update_data["alias"] = alias

        clean_plant_data = PlantUpdate(**plant_update_data)

        if image and not image.filename == "":
            try:
                image_url = await upload_plant_image(image, current_user.id, plant_id)
                
                if image_url:
                    clean_plant_data.image_url = image_url
            except (FileTooBigException, InvalidFileTypeException, UploadFailedException) as e:
                raise e

        updated_plant = update_plant_by_id(db, plant_id, current_user.id, clean_plant_data)
        
        return {
            "message": f"Planta '{updated_plant.alias}' actualizada con éxito",
            "plant": updated_plant
        }
    except Exception as e:
        if "no encontrada" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Planta no encontrada"
            )
        if "pertenece" in str(e).lower() or "propiedad" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para actualizar esta planta"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error al actualizar la planta"
        )


@router.delete(
    "/plants/{plant_id}",
    status_code=status.HTTP_200_OK,
    summary="Eliminar una planta",
    description="Elimina una planta específica propiedad del usuario autenticado.",
)
async def delete_plant_endpoint(
        plant_id: UUID = Path(..., description="ID de la planta"),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):

    try:
        plant = get_plant_by_id(db, plant_id, current_user.id)
        alias = plant.alias
        delete_plant_by_id(db, plant_id, current_user.id)
        return {"message": f"Planta '{alias}' eliminada con éxito"}
    except Exception as e:
        if "no encontrada" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Planta no encontrada"
            )
        if "pertenece" in str(e).lower() or "propiedad" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para eliminar esta planta"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error al eliminar la planta"
        )


@router.post(
    "/{garden_id}/plants",
    response_model=PlantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar planta a jardín",
    description="Agrega una nueva planta a un jardín propiedad del usuario autenticado.",
)
async def add_plant_endpoint(
    garden_id: UUID = Path(..., description="ID del jardín"),
    plant_data: PlantInGardenCreate = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    try:
        full_plant_data = PlantCreate(
            **plant_data.dict(),
            garden_id=garden_id
        )
        
        return add_plant_to_garden(db, garden_id, current_user.id, full_plant_data)
    except Exception as e:
        if "no encontrado" in str(e):
            raise GardenNotFoundException(garden_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pudo agregar la planta al jardín: {str(e)}"
        )
