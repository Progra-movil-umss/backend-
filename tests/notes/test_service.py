import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy.orm import Session
from src.notes.service import create_plant_note, update_plant_note, get_plant_notes
from src.notes.models import PlantNote
from src.notes.schemas import PlantNoteCreate, PlantNoteUpdate
from dataclasses import dataclass

@dataclass
class Plant:
    id: str

class DummyDB:
    def __init__(self):
        self.plants = {}
        self.notes = {}
    def query(self, model):
        if model == Plant:
            return self
        if model == PlantNote:
            return self
        return self
    def filter(self, *args, **kwargs):
        self._filter_args = args
        return self
    def first(self):
        # Simula que existe una planta
        if hasattr(self, '_filter_args') and self._filter_args:
            for arg in self._filter_args:
                if hasattr(arg, 'right') and hasattr(arg.right, 'value'):
                    plant_id = arg.right.value
                    return self.plants.get(plant_id)
        return None
    def add(self, obj):
        self.notes[obj.id] = obj
    def commit(self):
        pass
    def refresh(self, obj):
        pass
    def all(self):
        return list(self.notes.values())
    def order_by(self, *args, **kwargs):
        return self

@pytest.fixture
def dummy_db():
    db = DummyDB()
    # Agrega una planta simulada
    plant_id = uuid4()
    db.plants[plant_id] = Plant(id=plant_id)
    return db, plant_id

def test_create_plant_note_success(dummy_db):
    db, plant_id = dummy_db
    note_data = PlantNoteCreate(text="Nota válida", observation_date=datetime.now())
    note = create_plant_note(db, plant_id, note_data)
    assert note.text == "Nota válida"
    assert note.plant_id == plant_id

def test_create_plant_note_no_plant(dummy_db):
    db, _ = dummy_db
    note_data = PlantNoteCreate(text="Nota válida", observation_date=datetime.now())
    with pytest.raises(HTTPException) as exc:
        create_plant_note(db, uuid4(), note_data)
    assert exc.value.status_code == 404

def test_create_plant_note_empty_text(dummy_db):
    db, plant_id = dummy_db
    note_data = PlantNoteCreate(text=" ", observation_date=datetime.now())
    with pytest.raises(HTTPException) as exc:
        create_plant_note(db, plant_id, note_data)
    assert exc.value.status_code == 400

def test_create_plant_note_short_text(dummy_db):
    db, plant_id = dummy_db
    note_data = PlantNoteCreate(text="ok", observation_date=datetime.now())
    with pytest.raises(HTTPException) as exc:
        create_plant_note(db, plant_id, note_data)
    assert exc.value.status_code == 400
