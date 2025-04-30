from fastapi import HTTPException, status


class PlantNotFoundException(HTTPException):
    def __init__(self, plant_id):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Planta con ID {plant_id} no encontrada"
        )


class PlantCreationException(HTTPException):
    def __init__(self, detail="No se pudo crear la planta"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


class PlantUpdateException(HTTPException):
    def __init__(self, detail="No se pudo actualizar la planta"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


class PlantDeletionException(HTTPException):
    def __init__(self, detail="No se pudo eliminar la planta"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


class PlantInGardenNotFoundException(HTTPException):
    def __init__(self, assignment_id):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Relación planta-jardín con ID {assignment_id} no encontrada"
        )


class PlantAlreadyInGardenException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta planta ya está en el jardín"
        )


class PlantInGardenCreationException(HTTPException):
    def __init__(self, detail="No se pudo agregar la planta al jardín"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


class PlantInGardenUpdateException(HTTPException):
    def __init__(self, detail="No se pudo actualizar la información de la planta en el jardín"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


class PlantInGardenDeletionException(HTTPException):
    def __init__(self, detail="No se pudo eliminar la planta del jardín"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        ) 