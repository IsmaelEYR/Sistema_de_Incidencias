from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

import schemas
from dependencies import get_db
from services import usuarios as usuarios_service

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.get("/", response_model=list[schemas.UsuarioResponse])
def listar_usuarios(db: Session = Depends(get_db)):
    return usuarios_service.listar_usuarios(db)


@router.get("/{usuario_id}", response_model=schemas.UsuarioResponse)
def obtener_usuario(usuario_id: int, db: Session = Depends(get_db)):
    return usuarios_service.obtener_usuario(db, usuario_id)


@router.post("/", response_model=schemas.UsuarioResponse, status_code=status.HTTP_201_CREATED)
def crear_usuario(usuario: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    return usuarios_service.crear_usuario(db, usuario)
