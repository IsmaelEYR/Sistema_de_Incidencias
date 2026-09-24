from sqlalchemy.orm import Session

import models
from exceptions import DuplicateError, NotFoundError


def obtener_usuario(db: Session, usuario_id: int) -> models.Usuario:
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not usuario:
        raise NotFoundError("Usuario", usuario_id)
    return usuario


def obtener_usuario_por_nombre(db: Session, nombre: str) -> models.Usuario | None:
    return db.query(models.Usuario).filter(models.Usuario.nombre == nombre).first()


def listar_usuarios(db: Session, inactivos: bool = False) -> list[models.Usuario]:
    query = db.query(models.Usuario)
    if inactivos:
        query = query.filter(models.Usuario.activo == 0)
    else:
        query = query.filter(models.Usuario.activo == 1)
    return query.order_by(models.Usuario.nombre).all()


def listar_usuarios_activos_por_rol(db: Session, rol: str) -> list[models.Usuario]:
    return (
        db.query(models.Usuario)
        .filter(models.Usuario.rol == rol, models.Usuario.activo == 1)
        .order_by(models.Usuario.nombre)
        .all()
    )


def crear_usuario(db: Session, datos) -> models.Usuario:
    existente = obtener_usuario_por_nombre(db, datos.nombre)
    if existente:
        raise DuplicateError("usuario", "nombre", datos.nombre)

    usuario = models.Usuario(
        nombre=datos.nombre,
        email=datos.email,
        password_hash=datos.password_hash,
        rol=datos.rol.value if hasattr(datos.rol, 'value') else datos.rol,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


def actualizar_usuario(db: Session, usuario_id: int, datos) -> models.Usuario:
    usuario = obtener_usuario(db, usuario_id)
    if datos.nombre != usuario.nombre:
        existente = obtener_usuario_por_nombre(db, datos.nombre)
        if existente:
            raise DuplicateError("usuario", "nombre", datos.nombre)
        usuario.nombre = datos.nombre
    
    if datos.email is not None:
        usuario.email = datos.email
    if datos.password_hash:
        usuario.password_hash = datos.password_hash
    if datos.rol:
        usuario.rol = datos.rol.value if hasattr(datos.rol, 'value') else datos.rol

    db.commit()
    db.refresh(usuario)
    return usuario


def eliminar_usuario(db: Session, usuario_id: int) -> None:
    usuario = obtener_usuario(db, usuario_id)
    # Hacemos un soft delete
    usuario.activo = 0
    db.commit()