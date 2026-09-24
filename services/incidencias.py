from sqlalchemy.orm import Session, joinedload

import models
import schemas
from exceptions import ForeignKeyError, NotFoundError
from services.equipos import obtener_equipo
from services.usuarios import obtener_usuario


def _validar_referencias(db: Session, equipo_id: int, tecnico_id: int | None) -> None:
    obtener_equipo(db, equipo_id)
    if tecnico_id is not None:
        try:
            obtener_usuario(db, tecnico_id)
        except NotFoundError:
            raise ForeignKeyError("usuario", "tecnico_id", tecnico_id)


def incidencia_a_detalle(incidencia: models.Incidencia) -> schemas.IncidenciaDetalleResponse:
    return schemas.IncidenciaDetalleResponse(
        id=incidencia.id,
        descripcion=incidencia.descripcion,
        estado=incidencia.estado,
        fecha_reporte=incidencia.fecha_reporte,
        equipo_id=incidencia.equipo_id,
        equipo_nombre=incidencia.equipo.nombre if incidencia.equipo else "—",
        equipo_ubicacion=incidencia.equipo.ubicacion if incidencia.equipo else "—",
        tecnico_id=incidencia.tecnico_id,
        tecnico_nombre=incidencia.tecnico.nombre if incidencia.tecnico else None,
    )


def listar_incidencias_dashboard(db: Session) -> list[models.Incidencia]:
    from models import caracas_now
    ahora = caracas_now()
    hoy_inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    
    return (
        db.query(models.Incidencia)
        .options(joinedload(models.Incidencia.equipo), joinedload(models.Incidencia.tecnico))
        .filter(
            (models.Incidencia.estado.in_(["Pendiente", "En Proceso"])) |
            ((models.Incidencia.estado == "Resuelta") & (models.Incidencia.fecha_reporte >= hoy_inicio))
        )
        .order_by(models.Incidencia.fecha_reporte.desc())
        .all()
    )

def listar_incidencias(db: Session) -> list[models.Incidencia]:
    return (
        db.query(models.Incidencia)
        .options(joinedload(models.Incidencia.equipo), joinedload(models.Incidencia.tecnico))
        .order_by(models.Incidencia.fecha_reporte.desc())
        .all()
    )

def listar_incidencias_detalle(db: Session) -> list[schemas.IncidenciaDetalleResponse]:
    return [incidencia_a_detalle(i) for i in listar_incidencias(db)]


def obtener_incidencia(db: Session, incidencia_id: int) -> models.Incidencia:
    incidencia = (
        db.query(models.Incidencia)
        .options(joinedload(models.Incidencia.equipo), joinedload(models.Incidencia.tecnico))
        .filter(models.Incidencia.id == incidencia_id)
        .first()
    )
    if not incidencia:
        raise NotFoundError("Incidencia", incidencia_id)
    return incidencia


def crear_incidencia(db: Session, datos: schemas.IncidenciaCreate, responsable_id: int | None = None) -> models.Incidencia:
    _validar_referencias(db, datos.equipo_id, datos.tecnico_id)
    incidencia = models.Incidencia(
        descripcion=datos.descripcion,
        equipo_id=datos.equipo_id,
        tecnico_id=datos.tecnico_id,
    )
    db.add(incidencia)
    db.commit()
    db.refresh(incidencia)
    
    historial = models.HistorialIncidencia(
        incidencia_id=incidencia.id,
        usuario_id=responsable_id,
        accion="CREACION",
        estado_nuevo="Pendiente",
        detalle="Incidencia creada"
    )
    db.add(historial)
    db.commit()
    
    return incidencia


def crear_incidencia_por_qr(db: Session, codigo_qr: str, datos: schemas.IncidenciaReporteQR) -> models.Incidencia:
    from exceptions import DuplicateError
    from services.equipos import obtener_equipo_por_codigo
    equipo = obtener_equipo_por_codigo(db, codigo_qr)

    activa = db.query(models.Incidencia).filter(
        models.Incidencia.equipo_id == equipo.id,
        models.Incidencia.estado.in_(["Pendiente", "En Proceso"])
    ).first()
    
    if activa:
        raise DuplicateError("incidencia", "equipo", equipo.nombre)

    incidencia = models.Incidencia(
        descripcion=datos.descripcion,
        equipo_id=equipo.id,
    )
    db.add(incidencia)
    db.commit()
    db.refresh(incidencia)
    
    historial = models.HistorialIncidencia(
        incidencia_id=incidencia.id,
        usuario_id=None,
        accion="CREACION",
        estado_nuevo="Pendiente",
        detalle="Incidencia creada vía reporte QR"
    )
    db.add(historial)
    db.commit()
    
    return incidencia


def actualizar_incidencia(db: Session, incidencia_id: int, datos: schemas.IncidenciaUpdate, responsable_id: int | None = None) -> models.Incidencia:
    incidencia = obtener_incidencia(db, incidencia_id)
    estado_anterior = incidencia.estado
    
    detalles = []
    
    if datos.tecnico_id is not None:
        try:
            obtener_usuario(db, datos.tecnico_id)
        except NotFoundError:
            raise ForeignKeyError("usuario", "tecnico_id", datos.tecnico_id)
        if incidencia.tecnico_id != datos.tecnico_id:
            detalles.append(f"Técnico asignado ID: {datos.tecnico_id}")
            incidencia.tecnico_id = datos.tecnico_id
            
    if datos.estado is not None:
        if incidencia.estado != datos.estado.value:
            detalles.append(f"Estado cambiado a {datos.estado.value}")
            incidencia.estado = datos.estado.value
            
    db.commit()
    db.refresh(incidencia)
    
    if detalles:
        historial = models.HistorialIncidencia(
            incidencia_id=incidencia.id,
            usuario_id=responsable_id,
            accion="ACTUALIZACION" if len(detalles) > 1 else ("CAMBIO_ESTADO" if datos.estado else "ASIGNACION"),
            estado_anterior=estado_anterior,
            estado_nuevo=incidencia.estado,
            detalle=" | ".join(detalles)
        )
        db.add(historial)
        db.commit()
        
    return incidencia


def obtener_estadisticas(db: Session) -> dict[str, int]:
    incidencias = db.query(models.Incidencia).all()
    return {
        "total": len(incidencias),
        "pendientes": sum(1 for i in incidencias if i.estado == "Pendiente"),
        "en_proceso": sum(1 for i in incidencias if i.estado == "En Proceso"),
        "resueltas": sum(1 for i in incidencias if i.estado == "Resuelta"),
    }