from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

import schemas
from dependencies import get_db
from services import incidencias as incidencias_service

router = APIRouter(prefix="/incidencias", tags=["Incidencias"])


@router.get("/", response_model=list[schemas.IncidenciaDetalleResponse])
def listar_incidencias(db: Session = Depends(get_db)):
    return incidencias_service.listar_incidencias_detalle(db)


@router.get("/{incidencia_id}", response_model=schemas.IncidenciaDetalleResponse)
def obtener_incidencia(incidencia_id: int, db: Session = Depends(get_db)):
    incidencia = incidencias_service.obtener_incidencia(db, incidencia_id)
    return incidencias_service.incidencia_a_detalle(incidencia)


@router.post("/", response_model=schemas.IncidenciaResponse, status_code=status.HTTP_201_CREATED)
def crear_incidencia(incidencia: schemas.IncidenciaCreate, db: Session = Depends(get_db)):
    return incidencias_service.crear_incidencia(db, incidencia)


@router.put("/{incidencia_id}", response_model=schemas.IncidenciaResponse)
def actualizar_incidencia(
    incidencia_id: int,
    datos: schemas.IncidenciaUpdate,
    db: Session = Depends(get_db),
):
    return incidencias_service.actualizar_incidencia(db, incidencia_id, datos)
