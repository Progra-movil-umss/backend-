import os
import logging
from fastapi import APIRouter, UploadFile, HTTPException, status, File, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from PIL import Image
import io
import aiofiles
import tempfile
import subprocess
from typing import Optional, Dict, Any, List

from src.auth.service import get_current_user
from src.auth.schemas import User
from src.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()


class PlantNotFoundError(Exception):
    pass

@router.post("/identify", 
            tags=["plantas"],
            summary="Identificar una planta usando imágenes",
            description="Servicio de identificación de plantas usando imágenes. Requiere autenticación.",
            responses={
                200: {"description": "Identificación exitosa"},
                400: {"description": "Parámetros inválidos"},
                401: {"description": "No autorizado"},
                403: {"description": "Usuario inactivo"}
            })
async def plant_identification_endpoint(
        images: List[UploadFile] = File(..., description="Imágenes de la planta (máximo 5 archivos JPG o PNG)"),
        current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Identifica una planta utilizando una o más imágenes.
    
    - **images**: Lista de archivos de imagen (JPG/PNG)
    - **current_user**: Usuario autenticado
    
    Requiere token de autenticación en el header "Authorization: Bearer {token}"
    """
    try:
        settings = get_settings()

        if not current_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario inactivo"
            )

        if len(images) > settings.PLANTNET_MAX_IMAGES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Demasiadas imágenes. El máximo permitido es {settings.PLANTNET_MAX_IMAGES}"
            )

        if len(images) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debe proporcionar al menos una imagen"
            )

        temp_dir = tempfile.mkdtemp()
        file_paths = []

        for i, image in enumerate(images):
            if image.content_type not in ["image/jpeg", "image/png"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Formato de imagen no soportado en imagen {i + 1}. Use JPEG o PNG."
                )

            content = await image.read()

            if len(content) > settings.PLANTNET_MAX_IMAGE_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"La imagen {i + 1} es demasiado grande. El tamaño máximo es 50MB."
                )

            try:
                img = Image.open(io.BytesIO(content))
                img.verify()
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El archivo {i + 1} no es una imagen válida."
                )

            file_path = os.path.join(temp_dir, f"image_{i}_{image.filename}")
            async with aiofiles.open(file_path, 'wb') as out_file:
                await out_file.write(content)

            file_paths.append(file_path)

        include_related = "true" if settings.PLANTNET_INCLUDE_RELATED else "false"
        curl_command = [
            "curl", "-X", "POST",
            f"{settings.PLANTNET_API_URL}?include-related-images={include_related}&no-reject=false&nb-results={settings.PLANTNET_NB_RESULTS}&lang={settings.PLANTNET_LANGUAGE}&api-key={settings.PLANTNET_API_KEY}",
            "-H", "accept: application/json",
            "-H", "Content-Type: multipart/form-data"
        ]

        for file_path in file_paths:
            curl_command.extend(["-F", f"images=@{file_path}"])
            curl_command.extend(["-F", "organs=auto"])

        logger.info(f"Ejecutando comando curl: {' '.join(curl_command)}")

        process = subprocess.Popen(
            curl_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        stdout, stderr = process.communicate()

        for file_path in file_paths:
            if os.path.exists(file_path):
                os.remove(file_path)
        os.rmdir(temp_dir)

        if process.returncode != 0:
            logger.error(f"Error al ejecutar curl: {stderr}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Error al identificar la planta: {stderr}"
            )

        try:
            import json
            result = json.loads(stdout)
            return result
        except json.JSONDecodeError:
            logger.error(f"Error al decodificar la respuesta JSON: {stdout}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Error al procesar la respuesta del servicio de identificación de plantas"
            )

    except PlantNotFoundError as e:
        logger.error(f"Plant not found: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "The requested plant could not be found.", "results": []}
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.exception("Error inesperado en la identificación de plantas")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en el procesamiento de la solicitud: {str(e)}"
        )

async def identify_plant(
        images: List[UploadFile],
        current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    return await plant_identification_endpoint(images=images, current_user=current_user)
