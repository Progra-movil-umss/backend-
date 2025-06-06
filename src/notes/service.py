from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException
from src.notes.models import PlantNote
from src.notes.schemas import PlantNoteCreate, PlantNoteUpdate
from src.plants.models import Plant

def create_plant_note(db: Session, plant_id: UUID, note_data: PlantNoteCreate) -> PlantNote:
    # Validar existencia de la planta
    plant = db.query(Plant).filter(Plant.id == plant_id).first()
    if not plant:
        raise HTTPException(status_code=404, detail="La planta especificada no existe.")
    # Validar texto de la nota
    if not note_data.text or not note_data.text.strip():
        raise HTTPException(status_code=400, detail="El texto de la nota no puede estar vacío.")
    if len(note_data.text.strip()) < 3:
        raise HTTPException(status_code=400, detail="El texto de la nota debe tener al menos 3 caracteres.")
    # Validar fecha de observación
    if note_data.observation_date is None:
        raise HTTPException(status_code=400, detail="La fecha de la observación es obligatoria.")
    note = PlantNote(
        plant_id=plant_id,
        text=note_data.text.strip(),
        observation_date=note_data.observation_date
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note

def update_plant_note(db: Session, note_id: UUID, note_data: PlantNoteUpdate, user_id: UUID = None) -> PlantNote:
    note = db.query(PlantNote).filter(PlantNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Nota no encontrada")
    if user_id is not None and hasattr(note, 'user_id') and note.user_id != user_id:
        raise HTTPException(status_code=403, detail="No tienes permiso para editar esta nota")
    for key, value in note_data.dict(exclude_unset=True).items():
        setattr(note, key, value)
    db.commit()
    db.refresh(note)
    return note

def get_plant_notes(db: Session, plant_id: UUID) -> list[PlantNote]:
    return db.query(PlantNote).filter(PlantNote.plant_id == plant_id).order_by(PlantNote.observation_date.desc()).all()

def delete_plant_note(db: Session, note_id: UUID, user_id: UUID) -> None:
    note = db.query(PlantNote).filter(PlantNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Nota no encontrada")
    if note.user_id != user_id:
        raise HTTPException(status_code=403, detail="No tienes permiso para eliminar esta nota")
    db.delete(note)
    db.commit()
