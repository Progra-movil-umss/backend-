from fastapi import APIRouter, Depends

from src.auth.service import get_current_user
from src.plants import service
from src.plants.schemas import (
    WikipediaInfo
)

router = APIRouter()


@router.get("/wikipedia/{scientific_name}", response_model=WikipediaInfo)
async def get_plant_wikipedia_info(
    scientific_name: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Obtiene información detallada de una planta desde Wikipedia usando su nombre científico.
    """
    return service.get_wikipedia_info(scientific_name)

