from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

from src.gardens.models import Garden
from src.gardens.schemas import GardenCreate, GardenUpdate
from src.plants.models import Plant
from src.plants.schemas import PlantCreate, PlantUpdate
from src.storage.service import storage_service
from src.storage.constants import GARDEN_IMAGES_FOLDER, PLANT_IMAGES_FOLDER
from src.storage.exceptions import (
    FileTooBigException, InvalidFileTypeException, UploadFailedException
)
from src.storage.schemas import StorageResponse


def create_garden(db: Session, user_id: UUID, garden_data: GardenCreate):
    existing = db.query(Garden).filter(
        Garden.user_id == user_id, 
        Garden.name == garden_data.name
    ).first()
    
    if existing:
        raise ValueError(f"Ya existe un jardín con el nombre '{garden_data.name}'")
    
    try:
        garden = Garden(
            user_id=user_id,
            **garden_data.dict()
        )
        db.add(garden)
        db.commit()
        db.refresh(garden)
        return garden
    except IntegrityError:
        db.rollback()
        raise ValueError("No se pudo crear el jardín. Posible duplicado.")


def get_garden(db: Session, garden_id: UUID, user_id: UUID) -> Garden:
    garden = db.query(Garden).filter(
        Garden.id == garden_id,
        Garden.user_id == user_id
    ).first()
    
    if not garden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jardín no encontrado"
        )
    
    return garden


def get_gardens(
    db: Session, 
    user_id: UUID
) -> Dict[str, Any]:
    query = db.query(Garden).filter(Garden.user_id == user_id)
    
    total = query.count()
    gardens = query.order_by(Garden.created_at.desc()).all()
    
    return {
        "items": gardens,
        "total": total
    }


def update_garden(db: Session, garden_id: UUID, user_id: UUID, garden_data: GardenUpdate) -> Garden:
    garden = get_garden(db, garden_id, user_id)
    
    if garden_data.name and garden_data.name != garden.name:
        existing = db.query(Garden).filter(
            Garden.user_id == user_id, 
            Garden.name == garden_data.name,
            Garden.id != garden_id
        ).first()
        
        if existing:
            raise ValueError(f"Ya existe un jardín con el nombre '{garden_data.name}'")
    
    garden_data_dict = garden_data.dict(exclude_unset=True)
    for key, value in garden_data_dict.items():
        setattr(garden, key, value)
    
    garden.updated_at = datetime.now()
    
    db.commit()
    db.refresh(garden)
    return garden


def delete_garden(db: Session, garden_id: UUID, user_id: UUID) -> bool:
    garden = get_garden(db, garden_id, user_id)
    
    db.delete(garden)
    db.commit()
    return True


def add_plant_to_garden(
    db: Session, 
    garden_id: UUID, 
    user_id: UUID, 
    plant_data: PlantCreate
) -> Plant:
    garden = get_garden(db, garden_id, user_id)
    
    existing_plant = db.query(Plant).filter(
        Plant.user_id == user_id,
        Plant.alias == plant_data.alias
    ).first()
    
    if existing_plant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe una planta con el alias '{plant_data.alias}' para este usuario"
        )
    
    try:
        plant = Plant(
            alias=plant_data.alias,
            image_url=plant_data.image_url,
            scientific_name_without_author=plant_data.scientific_name_without_author,
            genus=plant_data.genus,
            family=plant_data.family,
            common_names=plant_data.common_names,
            garden_id=garden_id,
            user_id=user_id
        )
        
        db.add(plant)
        db.commit()
        db.refresh(plant)
        return plant
    except IntegrityError as e:
        db.rollback()
        if "uk_user_plant_alias" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe una planta con el alias '{plant_data.alias}' para este usuario"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pudo agregar la planta al jardín. Error: {str(e)}"
        )


def get_garden_plant(
    db: Session, 
    plant_id: UUID, 
    garden_id: UUID, 
    user_id: UUID
) -> Plant:
    garden = get_garden(db, garden_id, user_id)
    
    plant = db.query(Plant).filter(
        Plant.id == plant_id,
        Plant.garden_id == garden_id,
        Plant.user_id == user_id
    ).first()
    
    if not plant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planta no encontrada en el jardín"
        )
    
    return plant


def update_garden_plant(
    db: Session, 
    plant_id: UUID, 
    garden_id: UUID, 
    user_id: UUID,
    plant_data: PlantUpdate
) -> Plant:
    plant = get_garden_plant(db, plant_id, garden_id, user_id)
    
    if plant_data.alias and plant_data.alias != plant.alias:
        existing_plant = db.query(Plant).filter(
            Plant.user_id == user_id,
            Plant.alias == plant_data.alias,
            Plant.id != plant_id
        ).first()
        
        if existing_plant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe una planta con el alias '{plant_data.alias}' para este usuario"
            )
    
    plant_data_dict = plant_data.dict(exclude_unset=True)
    for key, value in plant_data_dict.items():
        setattr(plant, key, value)
    
    plant.updated_at = datetime.now()
    
    try:
        db.commit()
        db.refresh(plant)
        return plant
    except IntegrityError as e:
        db.rollback()
        if "uk_user_plant_alias" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe una planta con el alias '{plant_data.alias}' para este usuario"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pudo actualizar la planta. Error: {str(e)}"
        )


def delete_garden_plant(db: Session, plant_id: UUID, garden_id: UUID, user_id: UUID) -> bool:
    plant = get_garden_plant(db, plant_id, garden_id, user_id)
    
    db.delete(plant)
    db.commit()
    return True


def get_garden_plants(
    db: Session, 
    garden_id: UUID, 
    user_id: UUID,
    skip: int = 0, 
    limit: int = 100
) -> Dict[str, Any]:
    garden = get_garden(db, garden_id, user_id)
    
    query = db.query(Plant).filter(
        Plant.garden_id == garden_id,
        Plant.user_id == user_id
    )
    
    total = query.count()
    plants = query.order_by(Plant.created_at.desc()).offset(skip).limit(limit).all()
    
    plants_list = []
    for plant in plants:
        plants_list.append({
            "id": plant.id,
            "alias": plant.alias,
            "scientific_name_without_author": plant.scientific_name_without_author,
            "genus": plant.genus,
            "family": plant.family,
            "common_names": plant.common_names,
            "image_url": plant.image_url,
            "garden_id": plant.garden_id,
            "user_id": plant.user_id,
            "created_at": plant.created_at,
            "updated_at": plant.updated_at
        })
    
    return {
        "items": plants_list,
        "total": total,
        "garden_name": garden.name
    }


def count_plants_by_garden(db: Session, garden_ids: List[UUID]) -> Dict[UUID, int]:
    if not garden_ids:
        return {}
    
    results = db.query(
        Plant.garden_id,
        func.count(Plant.id).label("count")
    ).filter(
        Plant.garden_id.in_(garden_ids)
    ).group_by(
        Plant.garden_id
    ).all()
    
    return {garden_id: count for garden_id, count in results}


def get_garden_with_plants(db: Session, garden_id: UUID, user_id: UUID) -> Dict[str, Any]:
    garden = get_garden(db, garden_id, user_id)
    
    plants = db.query(Plant).filter(
        Plant.garden_id == garden_id,
        Plant.user_id == user_id
    ).all()
    
    plant_count = len(plants)
    
    plants_list = []
    for plant in plants:
        plants_list.append({
            "id": plant.id,
            "alias": plant.alias,
            "scientific_name_without_author": plant.scientific_name_without_author,
            "genus": plant.genus,
            "family": plant.family,
            "common_names": plant.common_names,
            "image_url": plant.image_url,
            "garden_id": plant.garden_id,
            "user_id": plant.user_id,
            "created_at": plant.created_at,
            "updated_at": plant.updated_at
        })
    
    garden_dict = {
        "id": garden.id,
        "name": garden.name,
        "description": garden.description,
        "image_url": garden.image_url,
        "user_id": garden.user_id,
        "created_at": garden.created_at,
        "updated_at": garden.updated_at,
        "plants": plants_list,
        "plant_count": plant_count
    }
    
    return garden_dict


async def upload_garden_image(
    image: Optional[UploadFile],
    user_id: UUID,
    garden_id: Optional[UUID] = None
) -> Optional[str]:

    if not image or (hasattr(image, 'filename') and not image.filename):
        return None
        
    try:
        folder = (
            f"{GARDEN_IMAGES_FOLDER}/{user_id}/{garden_id}" 
            if garden_id 
            else f"{GARDEN_IMAGES_FOLDER}/{user_id}"
        )
        
        response = await storage_service.upload_image(image, folder=folder)
        
        return response.url
        
    except (FileTooBigException, InvalidFileTypeException, UploadFailedException) as e:
        raise e
        

async def upload_plant_image(
    image: Optional[UploadFile],
    user_id: UUID,
    plant_id: Optional[UUID] = None,
    garden_id: Optional[UUID] = None
) -> Optional[str]:

    if not image or (hasattr(image, 'filename') and not image.filename):
        return None
    
    if plant_id and not garden_id:
        from src.database import SessionLocal
        db = SessionLocal()
        try:
            plant = db.query(Plant).filter(Plant.id == plant_id).first()
            if plant:
                garden_id = plant.garden_id
        finally:
            db.close()
    
    if not garden_id:
        raise ValueError("Se requiere el garden_id para subir la imagen de la planta")
        
    try:
        folder = f"{GARDEN_IMAGES_FOLDER}/{user_id}/{garden_id}/plants"
        if plant_id:
            folder = f"{folder}/{plant_id}"
        
        response = await storage_service.upload_image(image, folder=folder)
        
        return response.url
        
    except (FileTooBigException, InvalidFileTypeException, UploadFailedException) as e:
        raise e


def get_plant_by_id(
    db: Session, 
    plant_id: UUID, 
    user_id: UUID
) -> Plant:
    plant = db.query(Plant).filter(
        Plant.id == plant_id,
        Plant.user_id == user_id
    ).first()
    
    if not plant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planta no encontrada"
        )
    
    return plant


def update_plant_by_id(
    db: Session, 
    plant_id: UUID, 
    user_id: UUID,
    plant_data: PlantUpdate
) -> Plant:
    plant = get_plant_by_id(db, plant_id, user_id)
    
    if plant_data.alias and plant_data.alias != plant.alias:
        existing_plant = db.query(Plant).filter(
            Plant.user_id == user_id,
            Plant.alias == plant_data.alias,
            Plant.id != plant_id
        ).first()
        
        if existing_plant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe una planta con el alias '{plant_data.alias}' para este usuario"
            )
    
    plant_data_dict = plant_data.dict(exclude_unset=True)
    for key, value in plant_data_dict.items():
        setattr(plant, key, value)
    
    plant.updated_at = datetime.now()
    
    try:
        db.commit()
        db.refresh(plant)
        return plant
    except IntegrityError as e:
        db.rollback()
        if "uk_user_plant_alias" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe una planta con el alias '{plant_data.alias}' para este usuario"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pudo actualizar la planta. Error: {str(e)}"
        )


def delete_plant_by_id(db: Session, plant_id: UUID, user_id: UUID) -> bool:
    plant = get_plant_by_id(db, plant_id, user_id)
    
    db.delete(plant)
    db.commit()
    return True 