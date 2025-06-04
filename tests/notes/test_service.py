import pytest
from uuid import uuid4, UUID
from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy.orm import Session
from src.notes.service import create_plant_note, update_plant_note, get_plant_notes
from src.notes.models import PlantNote
from src.notes.schemas import PlantNoteCreate, PlantNoteUpdate
from dataclasses import dataclass

@dataclass
class Plant:
    id: UUID

class DummyDB:
    def __init__(self):
        self.plants = {}
        # Cambia a: {plant_id: [note1, note2, ...]}
        self.notes = {}
    def query(self, model):
        self._query_model = model
        return self
    def filter(self, *args, **kwargs):
        self._filter_args = args
        return self
    def first(self):
        # Para Plant: busca por id
        if self._query_model == Plant:
            for arg in self._filter_args:
                if hasattr(arg, 'right') and hasattr(arg.right, 'value'):
                    plant_id = arg.right.value
                    return self.plants.get(plant_id)
            return None
        # Para PlantNote: busca por id
        if self._query_model == PlantNote:
            for arg in self._filter_args:
                if hasattr(arg, 'left') and hasattr(arg.left, 'name') and arg.left.name == 'id':
                    note_id = arg.right.value
                    for notes in self.notes.values():
                        for note in notes:
                            if note.id == note_id:
                                return note
            return None
        return None
    def add(self, obj):
        # obj debe tener plant_id
        plant_id = getattr(obj, 'plant_id', None)
        if plant_id is not None:
            if plant_id not in self.notes:
                self.notes[plant_id] = []
            self.notes[plant_id].append(obj)
    def commit(self):
        pass
    def refresh(self, obj):
        pass
    def all(self):
        # Devuelve todas las notas para el último filtro de plant_id
        if self._query_model == PlantNote:
            for arg in self._filter_args:
                if hasattr(arg, 'left') and hasattr(arg.left, 'name') and arg.left.name == 'plant_id':
                    plant_id = arg.right.value
                    return list(self.notes.get(plant_id, []))
        return []
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

# Prueba: crear varias notas para la misma planta y listarlas
def test_create_and_list_multiple_notes(dummy_db):
    db, plant_id = dummy_db
    note1 = create_plant_note(db, plant_id, PlantNoteCreate(text="Primera nota", observation_date=datetime.now()))
    note2 = create_plant_note(db, plant_id, PlantNoteCreate(text="Segunda nota", observation_date=datetime.now() + timedelta(days=1)))
    notes = get_plant_notes(db, plant_id)
    assert len(notes) == 2
    texts = [n.text for n in notes]
    assert "Primera nota" in texts
    assert "Segunda nota" in texts

# Prueba: actualizar una nota existente
def test_update_plant_note_success(dummy_db):
    db, plant_id = dummy_db
    note = create_plant_note(db, plant_id, PlantNoteCreate(text="Original", observation_date=datetime.now()))
    update_data = PlantNoteUpdate(text="Actualizada", observation_date=datetime.now() + timedelta(days=2))
    updated = update_plant_note(db, note.id, update_data)
    assert updated.text == "Actualizada"
    assert updated.observation_date.date() == (datetime.now() + timedelta(days=2)).date()

# Prueba: intentar actualizar una nota inexistente
def test_update_nonexistent_note(dummy_db):
    db, plant_id = dummy_db
    fake_note_id = uuid4()
    update_data = PlantNoteUpdate(text="No existe", observation_date=datetime.now())
    with pytest.raises(HTTPException) as exc:
        update_plant_note(db, fake_note_id, update_data)
    assert exc.value.status_code == 404

# Prueba: listar notas de una planta sin notas
def test_list_notes_empty(dummy_db):
    db, plant_id = dummy_db
    notes = get_plant_notes(db, plant_id)
    assert notes == []
