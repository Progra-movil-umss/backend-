from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, and_, or_

from src.plants.models import Plant
from src.plants.schemas import PlantCreate, PlantUpdate, WikipediaInfo
from src.gardens.models import Garden
import wikipedia


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


def get_wikipedia_info(scientific_name: str) -> WikipediaInfo:
    try:
        wikipedia.set_lang("es")
        search_results = wikipedia.search(scientific_name, results=1)
        if not search_results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontró información en Wikipedia para {scientific_name}"
            )

        page = wikipedia.page(search_results[0])
        
        cultivation_section = None
        
        full_content = page.content
        
        if "== Cultivo ==" in full_content:
            start_index = full_content.find("== Cultivo ==")
            next_section = full_content.find("==", start_index + 12)
            if next_section != -1:
                cultivation_section = full_content[start_index:next_section].strip()
            else:
                cultivation_section = full_content[start_index:].strip()
            
            if cultivation_section:
                cultivation_section = cultivation_section.replace("== Cultivo ==", "").strip()
                import re
                cultivation_section = re.sub(r'\[\d+\]', '', cultivation_section)
        
        if not cultivation_section:
            for section in page.sections:
                if any(keyword in section.lower() for keyword in ['cultivo', 'cultivación', 'cuidados', 'cultivar']):
                    try:
                        section_content = wikipedia.page(f"{page.title}#{section}").content
                        if section_content:
                            cultivation_section = section_content
                            break
                    except:
                        continue
        
        if not cultivation_section:
            cultivation_section = "No se encontró información específica sobre cultivo para esta planta."
        
        images = page.images[:5] if page.images else []
        
        return WikipediaInfo(
            title=page.title,
            summary=page.summary,
            url=page.url,
            images=images,
            sections={"cultivo": cultivation_section}
        )
        
    except wikipedia.exceptions.DisambiguationError as e:
        try:
            page = wikipedia.page(e.options[0])
            return WikipediaInfo(
                title=page.title,
                summary=page.summary,
                url=page.url,
                images=page.images[:5] if page.images else [],
                sections={"cultivo": "No se encontró información específica sobre cultivo para esta planta."}
            )
        except:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se pudo encontrar información específica para {scientific_name}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener información de Wikipedia: {str(e)}"
        ) 