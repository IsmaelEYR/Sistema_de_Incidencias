import datetime
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    inspect,
    text,
)
from sqlalchemy.orm import relationship

from database import Base, engine

try:
    import zoneinfo
    tz = zoneinfo.ZoneInfo("America/Caracas")
except ImportError:
    import pytz
    tz = pytz.timezone("America/Caracas")


def caracas_now():
    return datetime.datetime.now(tz)


# =========================================================================
# 1. TABLA MAESTRA DE PARÁMETROS Y CATÁLOGOS (tipo_general)
# =========================================================================
class TipoGeneral(Base):
    __tablename__ = "tipo_general"

    id = Column(BigInteger, primary_key=True, index=True)
    categoria = Column(String(50), nullable=False, index=True)  # UBICACION, ESTADO_EQUIPO, ACCION
    nombre = Column(String(150), nullable=False)
    descripcion = Column(Text, nullable=True)
    activo = Column(Boolean, default=True, nullable=False)
    creado_en = Column(DateTime(timezone=True), default=caracas_now)
    actualizado_en = Column(DateTime(timezone=True), default=caracas_now, onupdate=caracas_now)

    # Relaciones inversas hacia equipos e historial
    equipos_por_ubicacion = relationship(
        "Equipo",
        foreign_keys="[Equipo.tipo_ubicacion_id]",
        back_populates="rel_ubicacion",
    )
    equipos_por_estado = relationship(
        "Equipo",
        foreign_keys="[Equipo.tipo_estado_id]",
        back_populates="rel_estado",
    )
    historial_acciones = relationship(
        "HistorialIncidencia",
        foreign_keys="[HistorialIncidencia.tipo_accion_id]",
        back_populates="rel_accion",
    )


# =========================================================================
# 2. GESTIÓN DE USUARIOS
# =========================================================================
class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (UniqueConstraint("nombre", name="uq_usuario_nombre"),)

    id = Column(BigInteger, primary_key=True, index=True)
    nombre = Column(String(100), index=True, nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=True)
    password_hash = Column(String(255), nullable=True)
    rol = Column(String(50), nullable=False)  # Administrador, Supervisor, Asistente/Tecnico
    activo = Column(Boolean, default=True, nullable=False)

    incidencias = relationship("Incidencia", back_populates="tecnico")
    historial = relationship("HistorialIncidencia", back_populates="usuario")
    logs_auditoria = relationship("LogAuditoria", back_populates="usuario")


# =========================================================================
# 3. EQUIPOS E INVENTARIO BASE
# =========================================================================
class Equipo(Base):
    __tablename__ = "equipos"

    id = Column(BigInteger, primary_key=True, index=True)
    nombre = Column(String(150), index=True, nullable=False)
    codigo_qr = Column(String(100), unique=True, index=True, nullable=False)
    activo = Column(Boolean, default=True, nullable=False)

    # Llaves foráneas hacia tipo_general (Esquema 2.4)
    tipo_ubicacion_id = Column(BigInteger, ForeignKey("tipo_general.id"), nullable=True, index=True)
    tipo_estado_id = Column(BigInteger, ForeignKey("tipo_general.id"), nullable=True, index=True)

    # Columnas legacy mantenidas como opcionales para evitar romper migraciones
    ubicacion = Column(String(150), nullable=True)
    tipo = Column(String(30), nullable=True, default="PC")
    piso = Column(String(10), nullable=True)

    # Relaciones
    rel_ubicacion = relationship("TipoGeneral", foreign_keys=[tipo_ubicacion_id], back_populates="equipos_por_ubicacion")
    rel_estado = relationship("TipoGeneral", foreign_keys=[tipo_estado_id], back_populates="equipos_por_estado")
    incidencias = relationship("Incidencia", back_populates="equipo")
    detalle_pc = relationship("DetallePC", back_populates="equipo", uselist=False)


# =========================================================================
# 4. HARDWARE DETALLADO (1 a 1 con Equipo)
# =========================================================================
class DetallePC(Base):
    __tablename__ = "detalle_pc"

    id = Column(BigInteger, primary_key=True, index=True)
    equipo_id = Column(BigInteger, ForeignKey("equipos.id"), unique=True, nullable=False)

    # 1. Info General y Asignación
    usuario_asignado = Column(String(150), nullable=True)
    nombre_red = Column(String(100), nullable=True)
    bien_nacional = Column(String(100), nullable=True)
    marca_modelo_cpu = Column(String(150), nullable=True)

    # 2. Red y Software
    ip = Column(String(50), nullable=True)
    tipo_ip = Column(String(30), nullable=True)
    mac = Column(String(50), nullable=True)
    dominio = Column(String(100), nullable=True)
    sistema_operativo = Column(String(100), nullable=True)
    version_so = Column(String(100), nullable=True)
    antivirus = Column(String(100), nullable=True)
    software_adicional = Column(Text, nullable=True)

    # 3. Hardware Interno
    procesador = Column(String(150), nullable=True)
    ram_gb = Column(Integer, nullable=True)
    ram_tipo = Column(String(50), nullable=True)
    ram_slots = Column(String(50), nullable=True)
    almacenamiento_tipo = Column(String(50), nullable=True)
    almacenamiento_capacidad = Column(String(50), nullable=True)
    puertos_video = Column(String(200), nullable=True)

    # 4. Periféricos y Protección
    monitor_marca = Column(String(100), nullable=True)
    monitor_modelo = Column(String(100), nullable=True)
    monitor_serial = Column(String(100), nullable=True)
    monitor_bn = Column(String(100), nullable=True)

    teclado_marca = Column(String(100), nullable=True)
    teclado_serial = Column(String(100), nullable=True)
    teclado_bn = Column(String(100), nullable=True)

    mouse_marca = Column(String(100), nullable=True)
    mouse_serial = Column(String(100), nullable=True)
    mouse_bn = Column(String(100), nullable=True)

    proteccion_electrica_tipo = Column(String(100), nullable=True)
    proteccion_electrica_marca = Column(String(100), nullable=True)
    proteccion_electrica_bn = Column(String(100), nullable=True)

    impresora_marca = Column(String(100), nullable=True)
    impresora_modelo = Column(String(100), nullable=True)
    impresora_ip = Column(String(50), nullable=True)
    impresora_bn = Column(String(100), nullable=True)

    # 5. Observaciones y Control
    observaciones = Column(Text, nullable=True)
    fecha_levantamiento = Column(DateTime(timezone=True), default=caracas_now, onupdate=caracas_now)

    equipo = relationship("Equipo", back_populates="detalle_pc")


# =========================================================================
# 5. GESTIÓN Y CICLO DE INCIDENCIAS (SLA + Reporte Externo)
# =========================================================================
class Incidencia(Base):
    __tablename__ = "incidencias"

    id = Column(BigInteger, primary_key=True, index=True)
    descripcion = Column(String(1000), nullable=False)
    estado = Column(String(30), default="PENDIENTE", nullable=False, index=True)  # PENDIENTE, EN_PROCESO, RESUELTO

    # Datos de captura de reporte externo (médicos / enfermeros)
    reportado_por_nombre = Column(String(150), nullable=True)
    reportado_por_cedula = Column(String(50), nullable=True)

    # Trazabilidad de tiempos y medición SLA
    fecha_reporte = Column(DateTime(timezone=True), default=caracas_now, index=True)
    fecha_asignacion = Column(DateTime(timezone=True), nullable=True)
    fecha_proceso = Column(DateTime(timezone=True), nullable=True)
    fecha_solucion = Column(DateTime(timezone=True), nullable=True)
    fecha_cierre = Column(DateTime(timezone=True), nullable=True)

    duracion_hasta_asignacion_min = Column(Integer, nullable=True)
    duracion_proceso_min = Column(Integer, nullable=True)
    duracion_solucion_min = Column(Integer, nullable=True)
    duracion_total_min = Column(Integer, nullable=True)
    duracion_total_horas = Column(Integer, nullable=True)

    # Verificación de cierre validado por usuario
    detalle_verificacion_cierre = Column(Text, nullable=True)

    # Relaciones relacionales
    equipo_id = Column(BigInteger, ForeignKey("equipos.id"), nullable=False, index=True)
    tecnico_id = Column(BigInteger, ForeignKey("usuarios.id"), nullable=True, index=True)

    equipo = relationship("Equipo", back_populates="incidencias")
    tecnico = relationship("Usuario", back_populates="incidencias")
    historial = relationship(
        "HistorialIncidencia",
        back_populates="incidencia",
        order_by="HistorialIncidencia.fecha.desc()",
    )


# =========================================================================
# 6. HISTORIAL Y TRAZABILIDAD DE INCIDENCIAS
# =========================================================================
class HistorialIncidencia(Base):
    __tablename__ = "historial_incidencias"

    id = Column(BigInteger, primary_key=True, index=True)
    incidencia_id = Column(BigInteger, ForeignKey("incidencias.id"), nullable=False, index=True)
    usuario_id = Column(BigInteger, ForeignKey("usuarios.id"), nullable=True, index=True)
    tipo_accion_id = Column(BigInteger, ForeignKey("tipo_general.id"), nullable=True, index=True)

    accion = Column(String(50), nullable=False)  # CREACION, ASIGNACION, CAMBIO_ESTADO, RESOLUCION
    estado_anterior = Column(String(30), nullable=True)
    estado_nuevo = Column(String(30), nullable=True)
    detalle = Column(Text, nullable=True)
    fecha = Column(DateTime(timezone=True), default=caracas_now, index=True)

    incidencia = relationship("Incidencia", back_populates="historial")
    usuario = relationship("Usuario", back_populates="historial")
    rel_accion = relationship("TipoGeneral", foreign_keys=[tipo_accion_id], back_populates="historial_acciones")


# =========================================================================
# 7. AUDITORÍA GENERAL DEL SISTEMA
# =========================================================================
class LogAuditoria(Base):
    __tablename__ = "log_auditoria"

    id = Column(BigInteger, primary_key=True, index=True)
    usuario_id = Column(BigInteger, ForeignKey("usuarios.id"), nullable=True, index=True)
    accion = Column(String(255), nullable=False)
    fecha = Column(DateTime(timezone=True), default=caracas_now, index=True)

    usuario = relationship("Usuario", back_populates="logs_auditoria")


# =========================================================================
# MIGRACIÓN AUTOMÁTICA SEGURA DE COLUMNAS
# =========================================================================
def _column_exists(table: str, column: str) -> bool:
    inspector = inspect(engine)
    if table not in inspector.get_table_names():
        return False
    return column in {c["name"] for c in inspector.get_columns(table)}


def migrate_db() -> None:
    Base.metadata.create_all(bind=engine)

    with engine.connect() as conn:
        # Migraciones en equipos
        if not _column_exists("equipos", "tipo_ubicacion_id"):
            conn.execute(text("ALTER TABLE equipos ADD COLUMN tipo_ubicacion_id BIGINT REFERENCES tipo_general(id)"))
        if not _column_exists("equipos", "tipo_estado_id"):
            conn.execute(text("ALTER TABLE equipos ADD COLUMN tipo_estado_id BIGINT REFERENCES tipo_general(id)"))

        # Migraciones en incidencias
        if not _column_exists("incidencias", "reportado_por_nombre"):
            conn.execute(text("ALTER TABLE incidencias ADD COLUMN reportado_por_nombre VARCHAR(150)"))
        if not _column_exists("incidencias", "reportado_por_cedula"):
            conn.execute(text("ALTER TABLE incidencias ADD COLUMN reportado_por_cedula VARCHAR(50)"))
        if not _column_exists("incidencias", "fecha_asignacion"):
            conn.execute(text("ALTER TABLE incidencias ADD COLUMN fecha_asignacion TIMESTAMPTZ"))
        if not _column_exists("incidencias", "fecha_proceso"):
            conn.execute(text("ALTER TABLE incidencias ADD COLUMN fecha_proceso TIMESTAMPTZ"))
        if not _column_exists("incidencias", "fecha_solucion"):
            conn.execute(text("ALTER TABLE incidencias ADD COLUMN fecha_solucion TIMESTAMPTZ"))
        if not _column_exists("incidencias", "duracion_hasta_asignacion_min"):
            conn.execute(text("ALTER TABLE incidencias ADD COLUMN duracion_hasta_asignacion_min INTEGER"))
        if not _column_exists("incidencias", "duracion_proceso_min"):
            conn.execute(text("ALTER TABLE incidencias ADD COLUMN duracion_proceso_min INTEGER"))
        if not _column_exists("incidencias", "duracion_solucion_min"):
            conn.execute(text("ALTER TABLE incidencias ADD COLUMN duracion_solucion_min INTEGER"))

        # Migraciones en historial_incidencias
        if not _column_exists("historial_incidencias", "tipo_accion_id"):
            conn.execute(text("ALTER TABLE historial_incidencias ADD COLUMN tipo_accion_id BIGINT REFERENCES tipo_general(id)"))

        conn.commit()