from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from src.database import get_db

router = APIRouter()

# Elimino cualquier import y endpoint relacionado con notas de planta