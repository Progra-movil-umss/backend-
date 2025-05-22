from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, and_, or_

from src.plants.models import Plant
from src.plants.schemas import PlantCreate, PlantUpdate
from src.gardens.models import Garden


def create_plant(db: Session, user_id: UUID, plant_data: PlantCreate) -> Plant:
    existing_plant = db.query(Plant).filter(
        Plant.user_id == user_id,
        Plant.alias == plant_data.alias
    ).first()
    
    if existing_plant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe una planta con el alias '{plant_data.alias}' para este usuario"
        )
    
    db_plant = Plant(
        alias=plant_data.alias,
        image_url=plant_data.image_url,
        user_id=user_id,
        garden_id=plant_data.garden_id,
        scientific_name_without_author=plant_data.scientific_name_without_author,
        genus=plant_data.genus,
        family=plant_data.family,
        common_names=plant_data.common_names
    )
    
    try:
        db.add(db_plant)
        db.commit()
        db.refresh(db_plant)
        return db_plant
    except IntegrityError as e:
        db.rollback()
        if "uk_user_plant_alias" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe una planta con el alias '{plant_data.alias}' para este usuario"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear la planta: {str(e)}"
        )


def get_plant(db: Session, plant_id: UUID, user_id: UUID) -> Optional[Plant]:
    return db.query(Plant).filter(
        Plant.id == plant_id,
        Plant.user_id == user_id
    ).first()


def get_plant_by_alias(db: Session, user_id: UUID, alias: str) -> Optional[Plant]:
    return db.query(Plant).filter(
        Plant.user_id == user_id,
        Plant.alias == alias
    ).first()


def get_plants(db: Session, user_id: UUID, skip: int = 0, limit: int = 100) -> Dict[str, Any]:
    total = db.query(Plant).filter(Plant.user_id == user_id).count()
    plants = db.query(Plant).filter(
        Plant.user_id == user_id
    ).offset(skip).limit(limit).all()
    
    return {
        "items": plants,
        "total": total
    }


def update_plant(db: Session, plant_id: UUID, user_id: UUID, plant_data: PlantUpdate) -> Plant:
    db_plant = get_plant(db, plant_id, user_id)
    
    if not db_plant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planta no encontrada"
        )
    
    if plant_data.alias and plant_data.alias != db_plant.alias:
        existing_plant = get_plant_by_alias(db, user_id, plant_data.alias)
        if existing_plant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe una planta con el alias '{plant_data.alias}' para este usuario"
            )
    
    update_data = plant_data.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_plant, key, value)
    
    try:
        db.commit()
        db.refresh(db_plant)
        return db_plant
    except IntegrityError as e:
        db.rollback()
        if "uk_user_plant_alias" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe una planta con el alias '{plant_data.alias}' para este usuario"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar la planta: {str(e)}"
        )


def delete_plant(db: Session, plant_id: UUID, user_id: UUID) -> None:
    db_plant = get_plant(db, plant_id, user_id)
    
    if not db_plant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planta no encontrada"
        )
    
    try:
        db.delete(db_plant)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar la planta: {str(e)}"
        )