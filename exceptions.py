from fastapi import HTTPException, status


class DuplicateError(HTTPException):
    def __init__(self, resource: str, field: str, value: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un {resource} con {field} '{value}'.",
        )


class NotFoundError(HTTPException):
    def __init__(self, resource: str, identifier: str | int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} no encontrado(a): {identifier}.",
        )


class ForeignKeyError(HTTPException):
    def __init__(self, resource: str, field: str, value: int):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No existe {resource} con {field}={value}.",
        )
