from fastapi import HTTPException, status


class GardenNotFoundException(HTTPException):
    def __init__(self, garden_id):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jardín no encontrado"
        )


class GardenForbiddenException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para acceder a este jardín"
        )


class PlantNotFoundException(HTTPException):
    def __init__(self, plant_id):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planta no encontrada"
        )


class GardenCreationException(HTTPException):
    def __init__(self, detail="No se pudo crear el jardín"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


class PlantCreationException(HTTPException):
    def __init__(self, detail="No se pudo crear la planta"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


class GardenUpdateException(HTTPException):
    def __init__(self, detail="No se pudo actualizar el jardín"):
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