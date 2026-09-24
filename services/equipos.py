from io import BytesIO

import qrcode
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

import models
import schemas
from config import settings
from exceptions import DuplicateError, NotFoundError

# Mapeo de ubicaciones a abreviaturas para el código QR
UBICACION_ABREV = {
    "laboratorio": "LAB", "rrhh": "RRHH", "dirección": "DIR",
    "pagos": "PAG", "quirofano": "QRO", "ingeniería": "ING",
    "administración": "ADM", "historias médicas": "HM",
    "bienes nacionales": "BN", "terapia intensiva": "TI",
    "trabajo social": "TS", "desarrollo": "DES", "docencia": "DOC",
    "cardiologia": "CARDIO", "cardiovascular": "CARDVASC",
    "emergencia": "EMG", "otros": "OTRO"
}

def _generar_codigo_qr(equipo_id: int, ubicacion: str, piso: str | None, tipo: str) -> str:
    """Genera un código QR único basado en ubicación, piso, tipo e ID."""
    abrev = UBICACION_ABREV.get(ubicacion.lower(), "EQ")
    piso_str = f"P{piso}" if piso else "SINPISO"
    return f"{abrev}-{piso_str}-{tipo.upper()}-{equipo_id}"


def listar_equipos(db: Session) -> list[models.Equipo]:
    return db.query(models.Equipo).filter(models.Equipo.activo == 1).order_by(models.Equipo.nombre).all()


def obtener_equipo(db: Session, equipo_id: int) -> models.Equipo:
    equipo = db.query(models.Equipo).filter(models.Equipo.id == equipo_id).first()
    if not equipo:
        raise NotFoundError("Equipo", equipo_id)
    return equipo


def obtener_equipo_por_codigo(db: Session, codigo_qr: str) -> models.Equipo:
    equipo = db.query(models.Equipo).filter(models.Equipo.codigo_qr == codigo_qr).first()
    if not equipo:
        raise NotFoundError("Equipo", codigo_qr)
    return equipo


def crear_equipo(db: Session, datos: schemas.EquipoCreate) -> models.Equipo:
    # Si no se envía nombre, se genera automáticamente
    if not datos.nombre:
        datos.nombre = f"{datos.tipo.capitalize()} - {datos.ubicacion.title()}"
        if datos.piso:
            datos.nombre += f" Piso {datos.piso}"

    equipo = models.Equipo(
        nombre=datos.nombre,
        ubicacion=datos.ubicacion,
        tipo=datos.tipo,
        piso=datos.piso,
        codigo_qr=""  # temporal
    )
    db.add(equipo)
    db.flush()  # obtener id

    # Generar código QR definitivo con el id
    equipo.codigo_qr = _generar_codigo_qr(equipo.id, datos.ubicacion, datos.piso, datos.tipo)

    # Verificar duplicado
    existente = db.query(models.Equipo).filter(models.Equipo.codigo_qr == equipo.codigo_qr).first()
    if existente:
        db.rollback()
        raise DuplicateError("equipo", "código QR", equipo.codigo_qr)

    db.commit()
    db.refresh(equipo)
    return equipo


def actualizar_equipo(db: Session, equipo_id: int, datos: schemas.EquipoCreate) -> models.Equipo:
    equipo = obtener_equipo(db, equipo_id)

    if not datos.nombre:
        datos.nombre = f"{datos.tipo.capitalize()} - {datos.ubicacion.title()}"
        if datos.piso:
            datos.nombre += f" Piso {datos.piso}"

    equipo.nombre = datos.nombre
    equipo.ubicacion = datos.ubicacion
    equipo.tipo = datos.tipo
    equipo.piso = datos.piso

    # Re-generar QR si cambió ubicación, piso o tipo
    if (equipo.ubicacion != datos.ubicacion or
        equipo.piso != datos.piso or
        equipo.tipo != datos.tipo):
        nuevo_qr = _generar_codigo_qr(equipo.id, datos.ubicacion, datos.piso, datos.tipo)
        existe = db.query(models.Equipo).filter(
            models.Equipo.codigo_qr == nuevo_qr,
            models.Equipo.id != equipo.id
        ).first()
        if existe:
            raise DuplicateError("equipo", "código QR", nuevo_qr)
        equipo.codigo_qr = nuevo_qr

    db.commit()
    db.refresh(equipo)
    return equipo


def eliminar_equipo(db: Session, equipo_id: int) -> None:
    equipo = obtener_equipo(db, equipo_id)
    equipo.activo = 0
    db.commit()


def generar_qr_equipo(db: Session, equipo_id: int) -> StreamingResponse:
    equipo = obtener_equipo(db, equipo_id)
    url_reporte = f"{settings.base_url}/reportar/{equipo.codigo_qr}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(url_reporte)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#0d6e6e", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="image/png",
        headers={"Content-Disposition": f'inline; filename="qr-{equipo.codigo_qr}.png"'},
    )