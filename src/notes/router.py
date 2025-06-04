from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID
from src.database import get_db
from src.notes.service import create_plant_note, update_plant_note, get_plant_notes
from src.notes.schemas import PlantNoteCreate, PlantNoteUpdate, PlantNoteResponse

router = APIRouter()

@router.post("/{plant_id}/notes", response_model=PlantNoteResponse, status_code=201)
def add_plant_note(plant_id: UUID, note: PlantNoteCreate, db: Session = Depends(get_db)):
    return create_plant_note(db, plant_id, note)

@router.put("/notes/{note_id}", response_model=PlantNoteResponse)
def edit_plant_note(note_id: UUID, note: PlantNoteUpdate, db: Session = Depends(get_db)):
    return update_plant_note(db, note_id, note)

@router.get("/{plant_id}/notes", response_model=list[PlantNoteResponse])
def list_plant_notes(plant_id: UUID, db: Session = Depends(get_db)):
    return get_plant_notes(db, plant_id)
