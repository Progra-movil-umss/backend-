import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy.orm import Session
from src.notes.service import create_plant_note, update_plant_note, get_plant_notes, delete_plant_note
from src.notes.models import PlantNote
from src.notes.schemas import PlantNoteCreate, PlantNoteUpdate
from dataclasses import dataclass
from uuid import UUID

@dataclass
class Plant:
    id: UUID
    user_id: UUID = None

class DummyDB:
    def __init__(self):
        self.plants = {}
        self.notes = {}
    def query(self, model):
        self._query_model = model
        self._filter_args = []
        self._filter_plant_id = None
        self._filter_note_id = None
        return self
    def filter(self, *args, **kwargs):
        self._filter_args = args
        if self._query_model == Plant:
            self._filter_plant_id = None
            for arg in args:
                # Handle direct UUID
                if isinstance(arg, UUID):
                    self._filter_plant_id = arg
                    break
                # Handle SQLAlchemy-like binary expressions (Plant.id == plant_id)
                if hasattr(arg, 'left') and hasattr(arg, 'right'):
                    # Try to match left to Plant.id and right to UUID
                    left = getattr(arg, 'left', None)
                    right = getattr(arg, 'right', None)
                    val = getattr(right, 'value', None) if hasattr(right, 'value') else right
                    if hasattr(left, 'name') and left.name == 'id':
                        # right.value is usually the UUID
                        if isinstance(val, UUID):
                            self._filter_plant_id = val
                            break
                        if isinstance(val, str):
                            try:
                                self._filter_plant_id = UUID(val)
                                break
                            except Exception:
                                pass
                # Handle direct value (sometimes just the UUID)
                if hasattr(arg, 'right') and hasattr(arg.right, 'value'):
                    val = arg.right.value
                    if isinstance(val, UUID):
                        self._filter_plant_id = val
                        break
                    if isinstance(val, str):
                        try:
                            self._filter_plant_id = UUID(val)
                            break
                        except Exception:
                            pass
            if self._filter_plant_id is None and len(self.plants) == 1:
                self._filter_plant_id = next(iter(self.plants.keys()))
        if self._query_model == PlantNote:
            for arg in args:
                if hasattr(arg, 'right') and hasattr(arg.right, 'value'):
                    self._filter_note_id = arg.right.value
        return self
    def first(self):
        if self._query_model == Plant:
            plant_id = getattr(self, '_filter_plant_id', None)
            if plant_id is not None:
                return self.plants.get(plant_id)
            # Si no hay filtro pero solo hay una planta, devuélvela
            if len(self.plants) == 1:
                return next(iter(self.plants.values()))
            return None
        if self._query_model == PlantNote:
            note_id = getattr(self, '_filter_note_id', None)
            if note_id is not None:
                return self.notes.get(note_id)
            return None
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

def test_delete_plant_note_only_owner(dummy_db):
    db, plant_id = dummy_db
    owner_id = uuid4()
    other_user_id = uuid4()
    # Simula que la planta tiene un user_id
    db.plants[plant_id].user_id = owner_id
    # Crea la nota y asígnale el user_id
    note = create_plant_note(db, plant_id, PlantNoteCreate(text="Original", observation_date=datetime.now()))
    note.user_id = owner_id
    db.notes[note.id] = note

    # El dueño puede eliminar
    try:
        delete_plant_note(db, note.id, owner_id)
    except Exception:
        pytest.fail("El dueño no pudo eliminar la nota")

    # Otro usuario NO puede eliminar
    note2 = create_plant_note(db, plant_id, PlantNoteCreate(text="Otra", observation_date=datetime.now()))
    note2.user_id = owner_id
    db.notes[note2.id] = note2
    with pytest.raises(HTTPException) as exc:
        delete_plant_note(db, note2.id, other_user_id)
    assert exc.value.status_code == 403

def test_update_plant_note_only_owner(dummy_db):
    db, plant_id = dummy_db
    owner_id = uuid4()
    other_user_id = uuid4()
    db.plants[plant_id].user_id = owner_id
    note = create_plant_note(db, plant_id, PlantNoteCreate(text="Original", observation_date=datetime.now()))
    note.user_id = owner_id
    db.notes[note.id] = note
    from src.notes.service import update_plant_note
    # El dueño puede editar
    try:
        update_plant_note(db, note.id, PlantNoteUpdate(text="Editada", observation_date=datetime.now()), user_id=owner_id)
    except Exception:
        pytest.fail("El dueño no pudo editar la nota")
    # Otro usuario NO puede editar
    with pytest.raises(HTTPException) as exc:
        update_plant_note(db, note.id, PlantNoteUpdate(text="Editada por otro", observation_date=datetime.now()), user_id=other_user_id)
    assert exc.value.status_code == 403
