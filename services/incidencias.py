from sqlalchemy.orm import Session, joinedload
from datetime import datetime

import models
import schemas
from models import caracas_now
from exceptions import ForeignKeyError, NotFoundError, DuplicateError
from services.equipos import obtener_equipo, obtener_equipo_por_codigo
from services.usuarios import obtener_usuario


def _normalizar_estado(estado_val) -> str:
    """Normaliza cualquier variante de estado al formato estándar en mayúsculas de PostgreSQL."""
    if not estado_val:
        return "PENDIENTE"
    if hasattr(estado_val, "value"):
        estado_val = estado_val.value
    val = str(estado_val).strip().upper().replace(" ", "_")
    if val in ["RESUELTA", "RESUELTO"]:
        return "RESUELTO"
    if val in ["PENDIENTE"]:
        return "PENDIENTE"
    if val in ["EN_PROCESO"]:
        return "EN_PROCESO"
    if val in ["CERRADO", "CERRADA"]:
        return "CERRADO"
    if val in ["CANCELADO", "CANCELADA"]:
        return "CANCELADO"
    return val


def _obtener_tipo_accion_id(db: Session, nombre_accion: str) -> int | None:
    """Obtiene el ID de tipo_general para la categoría ACCION si existe."""
    registro = db.query(models.TipoGeneral).filter(
        models.TipoGeneral.categoria == "ACCION",
        models.TipoGeneral.nombre.ilike(nombre_accion.strip())
    ).first()
    return registro.id if registro else None


def _validar_referencias(db: Session, equipo_id: int, tecnico_id: int | None) -> None:
    obtener_equipo(db, equipo_id)
    if tecnico_id is not None:
        try:
            obtener_usuario(db, tecnico_id)
        except NotFoundError:
            raise ForeignKeyError("usuario", "tecnico_id", tecnico_id)


def incidencia_a_detalle(incidencia: models.Incidencia) -> schemas.IncidenciaDetalleResponse:
    # Obtener nombre de ubicación (soporte esquema 2.4 y legacy)
    ubicacion_str = "—"
    estado_equipo_str = "—"
    if incidencia.equipo:
        if incidencia.equipo.rel_ubicacion:
            ubicacion_str = incidencia.equipo.rel_ubicacion.nombre
        elif incidencia.equipo.ubicacion:
            ubicacion_str = incidencia.equipo.ubicacion

        if incidencia.equipo.rel_estado:
            estado_equipo_str = incidencia.equipo.rel_estado.nombre

    # Formato amigable de duración
    duracion_formateada = None
    if incidencia.duracion_total_min is not None:
        horas = incidencia.duracion_total_min // 60
        minutos = incidencia.duracion_total_min % 60
        duracion_formateada = f"{horas}h {minutos}m"
    elif _normalizar_estado(incidencia.estado) in ["PENDIENTE", "EN_PROCESO"]:
        duracion_formateada = "En proceso"

    return schemas.IncidenciaDetalleResponse(
        id=incidencia.id,
        descripcion=incidencia.descripcion,
        estado=incidencia.estado,
        fecha_reporte=incidencia.fecha_reporte,
        equipo_id=incidencia.equipo_id,
        equipo_nombre=incidencia.equipo.nombre if incidencia.equipo else "—",
        ubicacion_actual=ubicacion_str,
        estado_operativo_maquina=estado_equipo_str,
        tecnico_id=incidencia.tecnico_id,
        tecnico_nombre=incidencia.tecnico.nombre if incidencia.tecnico else None,
        tecnico_email=incidencia.tecnico.email if (incidencia.tecnico and hasattr(incidencia.tecnico, "email")) else None,
        reportado_por_nombre=incidencia.reportado_por_nombre,
        reportado_por_cedula=incidencia.reportado_por_cedula,
        duracion_total_min=incidencia.duracion_total_min,
        duracion_total_formateada=duracion_formateada,
        detalle_verificacion_cierre=incidencia.detalle_verificacion_cierre,
    )


def listar_incidencias(db: Session) -> list[models.Incidencia]:
    return (
        db.query(models.Incidencia)
        .options(
            joinedload(models.Incidencia.equipo).joinedload(models.Equipo.rel_ubicacion),
            joinedload(models.Incidencia.equipo).joinedload(models.Equipo.rel_estado),
            joinedload(models.Incidencia.tecnico),
        )
        .order_by(models.Incidencia.fecha_reporte.desc())
        .all()
    )


def listar_incidencias_dashboard(db: Session) -> list[models.Incidencia]:
    ahora = caracas_now()
    hoy_inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    
    estados_activos = ["PENDIENTE", "EN_PROCESO", "Pendiente", "En Proceso"]
    estados_resueltos = ["RESUELTO", "CERRADO", "Resuelta", "Cerrado"]

    return (
        db.query(models.Incidencia)
        .options(
            joinedload(models.Incidencia.equipo).joinedload(models.Equipo.rel_ubicacion),
            joinedload(models.Incidencia.equipo).joinedload(models.Equipo.rel_estado),
            joinedload(models.Incidencia.tecnico),
        )
        .filter(
            (models.Incidencia.estado.in_(estados_activos)) |
            ((models.Incidencia.estado.in_(estados_resueltos)) & (models.Incidencia.fecha_reporte >= hoy_inicio))
        )
        .order_by(models.Incidencia.fecha_reporte.desc())
        .all()
    )


def listar_incidencias_detalle(db: Session) -> list[schemas.IncidenciaDetalleResponse]:
    return [incidencia_a_detalle(i) for i in listar_incidencias(db)]


def obtener_incidencia(db: Session, incidencia_id: int) -> models.Incidencia:
    incidencia = (
        db.query(models.Incidencia)
        .options(
            joinedload(models.Incidencia.equipo).joinedload(models.Equipo.rel_ubicacion),
            joinedload(models.Incidencia.equipo).joinedload(models.Equipo.rel_estado),
            joinedload(models.Incidencia.tecnico),
        )
        .filter(models.Incidencia.id == incidencia_id)
        .first()
    )
    if not incidencia:
        raise NotFoundError("Incidencia", incidencia_id)
    return incidencia


def crear_incidencia(db: Session, datos: schemas.IncidenciaCreate, responsable_id: int | None = None) -> models.Incidencia:
    _validar_referencias(db, datos.equipo_id, datos.tecnico_id)
    
    ahora = caracas_now()
    incidencia = models.Incidencia(
        descripcion=datos.descripcion,
        equipo_id=datos.equipo_id,
        tecnico_id=datos.tecnico_id,
        reportado_por_nombre=datos.reportado_por_nombre,
        reportado_por_cedula=datos.reportado_por_cedula,
        estado="PENDIENTE",
        fecha_reporte=ahora,
        fecha_asignacion=ahora if datos.tecnico_id else None,
    )
    db.add(incidencia)
    db.flush()  # Asigna ID sin cerrar transacción
    
    # Actualizar estado de la máquina a EN_REVISION si existe en catálogo
    estado_en_revision = db.query(models.TipoGeneral).filter(
        models.TipoGeneral.categoria == "ESTADO_EQUIPO",
        models.TipoGeneral.nombre.ilike("EN_REVISION")
    ).first()
    if estado_en_revision and incidencia.equipo:
        incidencia.equipo.tipo_estado_id = estado_en_revision.id
        db.add(incidencia.equipo)

    tipo_accion_id = _obtener_tipo_accion_id(db, "CREACION")
    historial = models.HistorialIncidencia(
        incidencia_id=incidencia.id,
        usuario_id=responsable_id,
        tipo_accion_id=tipo_accion_id,
        accion="CREACION",
        estado_nuevo="PENDIENTE",
        detalle="Incidencia creada formalmente en el sistema",
        fecha=ahora,
    )
    db.add(historial)
    db.commit()
    db.refresh(incidencia)
    
    return incidencia


def crear_incidencia_por_qr(db: Session, codigo_qr: str, datos: schemas.IncidenciaReporteQR) -> models.Incidencia:
    equipo = obtener_equipo_por_codigo(db, codigo_qr)

    # Validar que no existan incidencias abiertas (anti-duplicado)
    estados_activos = ["PENDIENTE", "EN_PROCESO", "Pendiente", "En Proceso"]
    activa = db.query(models.Incidencia).filter(
        models.Incidencia.equipo_id == equipo.id,
        models.Incidencia.estado.in_(estados_activos)
    ).first()
    
    if activa:
        raise DuplicateError("incidencia", "equipo", f"{equipo.nombre} (Tiene la Incidencia #{activa.id} en curso)")

    ahora = caracas_now()
    incidencia = models.Incidencia(
        descripcion=datos.descripcion,
        equipo_id=equipo.id,
        reportado_por_nombre=datos.reportado_por_nombre,
        reportado_por_cedula=datos.reportado_por_cedula,
        estado="PENDIENTE",
        fecha_reporte=ahora,
    )
    db.add(incidencia)
    db.flush()

    # Poner la máquina en EN_REVISION
    estado_en_revision = db.query(models.TipoGeneral).filter(
        models.TipoGeneral.categoria == "ESTADO_EQUIPO",
        models.TipoGeneral.nombre.ilike("EN_REVISION")
    ).first()
    if estado_en_revision:
        equipo.tipo_estado_id = estado_en_revision.id
        db.add(equipo)

    tipo_accion_id = _obtener_tipo_accion_id(db, "CREACION")
    historial = models.HistorialIncidencia(
        incidencia_id=incidencia.id,
        usuario_id=None,
        tipo_accion_id=tipo_accion_id,
        accion="CREACION",
        estado_nuevo="PENDIENTE",
        detalle=f"Reporte QR emitido por {datos.reportado_por_nombre} (CI: {datos.reportado_por_cedula})",
        fecha=ahora,
    )
    db.add(historial)
    db.commit()
    db.refresh(incidencia)
    
    return incidencia


def actualizar_incidencia(db: Session, incidencia_id: int, datos: schemas.IncidenciaUpdate, responsable_id: int | None = None) -> models.Incidencia:
    incidencia = obtener_incidencia(db, incidencia_id)
    estado_anterior = incidencia.estado
    ahora = caracas_now()
    
    detalles = []
    nombre_accion = "ACTUALIZACION"

    # 1. Asignación / Cambio de técnico
    if datos.tecnico_id is not None:
        try:
            tecnico = obtener_usuario(db, datos.tecnico_id)
        except NotFoundError:
            raise ForeignKeyError("usuario", "tecnico_id", datos.tecnico_id)
        
        if incidencia.tecnico_id != datos.tecnico_id:
            nombre_accion = "ASIGNACION"
            incidencia.tecnico_id = datos.tecnico_id
            incidencia.fecha_asignacion = ahora
            if incidencia.fecha_reporte:
                diff = int((ahora - incidencia.fecha_reporte).total_seconds() // 60)
                incidencia.duracion_hasta_asignacion_min = diff
            detalles.append(f"Técnico asignado: {tecnico.nombre} (ID: {datos.tecnico_id})")

    # 2. Cambio de Estado y SLAs
    if datos.estado is not None:
        nuevo_estado = _normalizar_estado(datos.estado)
        if _normalizar_estado(incidencia.estado) != nuevo_estado:
            nombre_accion = "CAMBIO_ESTADO"
            incidencia.estado = nuevo_estado
            detalles.append(f"Estado cambiado de {estado_anterior} a {nuevo_estado}")

            if nuevo_estado == "EN_PROCESO":
                incidencia.fecha_proceso = ahora

            elif nuevo_estado in ["RESUELTO", "CERRADO"]:
                nombre_accion = "RESOLUCION"
                incidencia.fecha_solucion = ahora
                incidencia.fecha_cierre = ahora
                
                # Cálculo de SLAs en minutos y horas
                if incidencia.fecha_reporte:
                    delta_total = int((ahora - incidencia.fecha_reporte).total_seconds() // 60)
                    incidencia.duracion_total_min = delta_total
                    incidencia.duracion_total_horas = delta_total // 60

                if incidencia.fecha_proceso:
                    incidencia.duracion_solucion_min = int((ahora - incidencia.fecha_proceso).total_seconds() // 60)

                # Liberar estado operativo del equipo a ACTIVO
                estado_activo = db.query(models.TipoGeneral).filter(
                    models.TipoGeneral.categoria == "ESTADO_EQUIPO",
                    models.TipoGeneral.nombre.ilike("ACTIVO")
                ).first()
                if estado_activo and incidencia.equipo:
                    incidencia.equipo.tipo_estado_id = estado_activo.id
                    db.add(incidencia.equipo)

    # 3. Verificación de cierre
    if getattr(datos, "detalle_verificacion_cierre", None):
        incidencia.detalle_verificacion_cierre = datos.detalle_verificacion_cierre
        detalles.append("Detalle de verificación de cierre registrado")

    # 4. Guardar cambios en DB y registrar auditoría
    if detalles:
        tipo_accion_id = _obtener_tipo_accion_id(db, nombre_accion)
        historial = models.HistorialIncidencia(
            incidencia_id=incidencia.id,
            usuario_id=responsable_id,
            tipo_accion_id=tipo_accion_id,
            accion=nombre_accion,
            estado_anterior=estado_anterior,
            estado_nuevo=incidencia.estado,
            detalle=" | ".join(detalles),
            fecha=ahora,
        )
        db.add(historial)
    
    db.add(incidencia)
    db.commit()
    db.refresh(incidencia)
        
    return incidencia


def obtener_estadisticas(db: Session) -> dict[str, int]:
    incidencias = db.query(models.Incidencia).all()
    
    pendientes = 0
    en_proceso = 0
    resueltas = 0
    
    for inc in incidencias:
        est = _normalizar_estado(inc.estado)
        if est == "PENDIENTE":
            pendientes += 1
        elif est == "EN_PROCESO":
            en_proceso += 1
        elif est in ["RESUELTO", "CERRADO"]:
            resueltas += 1

    return {
        "total": len(incidencias),
        "pendientes": pendientes,
        "en_proceso": en_proceso,
        "resueltas": resueltas,
    }