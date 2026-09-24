from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, inspect, text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base, engine


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (UniqueConstraint("nombre", name="uq_usuario_nombre"),)

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), index=True, nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=True)
    password_hash = Column(String(255), nullable=True)
    rol = Column(String(50), nullable=False)
    activo = Column(Integer, default=1, nullable=False)

    incidencias = relationship("Incidencia", back_populates="tecnico")
    historial = relationship("HistorialIncidencia", back_populates="usuario")
    logs_auditoria = relationship("LogAuditoria", back_populates="usuario")


class Equipo(Base):
    __tablename__ = "equipos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), index=True, nullable=False)
    ubicacion = Column(String(150), nullable=False)
    codigo_qr = Column(String(100), unique=True, index=True, nullable=False)
    tipo = Column(String(30), nullable=False, default="PC")
    piso = Column(String(10), nullable=True)
    activo = Column(Integer, default=1, nullable=False)

    incidencias = relationship("Incidencia", back_populates="equipo")
    detalle_pc = relationship("DetallePC", back_populates="equipo", uselist=False)


class Incidencia(Base):
    __tablename__ = "incidencias"

    id = Column(Integer, primary_key=True, index=True)
    descripcion = Column(String(1000), nullable=False)
    estado = Column(String(30), default="Pendiente", nullable=False)
    fecha_reporte = Column(DateTime(timezone=True), server_default=func.now())

    equipo_id = Column(Integer, ForeignKey("equipos.id"), nullable=False, index=True)
    tecnico_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True, index=True)

    equipo = relationship("Equipo", back_populates="incidencias")
    tecnico = relationship("Usuario", back_populates="incidencias")
    historial = relationship(
        "HistorialIncidencia",
        back_populates="incidencia",
        order_by="HistorialIncidencia.fecha.desc()",
    )


class HistorialIncidencia(Base):
    __tablename__ = "historial_incidencias"

    id = Column(Integer, primary_key=True, index=True)
    incidencia_id = Column(Integer, ForeignKey("incidencias.id"), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True, index=True)
    accion = Column(String(50), nullable=False)
    estado_anterior = Column(String(30), nullable=True)
    estado_nuevo = Column(String(30), nullable=True)
    detalle = Column(Text, nullable=True)
    fecha = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    incidencia = relationship("Incidencia", back_populates="historial")
    usuario = relationship("Usuario", back_populates="historial")


class DetallePC(Base):
    __tablename__ = "detalle_pc"

    id = Column(Integer, primary_key=True, index=True)
    equipo_id = Column(Integer, ForeignKey("equipos.id"), unique=True, nullable=False)
    
    # 1. Info General
    nombre_red = Column(String(100), nullable=True)
    bien_nacional = Column(String(100), nullable=True)
    marca_modelo_cpu = Column(String(150), nullable=True)
    usuario_asignado = Column(String(150), nullable=True)
    
    # 2. Red y Software
    ip = Column(String(50), nullable=True)
    tipo_ip = Column(String(30), nullable=True)
    mac = Column(String(50), nullable=True)
    sistema_operativo = Column(String(100), nullable=True)
    version_so = Column(String(100), nullable=True)
    dominio = Column(String(100), nullable=True)
    antivirus = Column(String(100), nullable=True)
    software_adicional = Column(Text, nullable=True)
    
    # 3. Hardware
    procesador = Column(String(150), nullable=True)
    ram_gb = Column(Integer, nullable=True)
    ram_tipo = Column(String(50), nullable=True)
    ram_slots = Column(String(50), nullable=True)
    almacenamiento_tipo = Column(String(50), nullable=True)
    almacenamiento_capacidad = Column(String(50), nullable=True)
    puertos_video = Column(String(200), nullable=True)
    
    # 4. Perifericos
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
    
    # 5. Cierre
    observaciones = Column(Text, nullable=True)
    fecha_levantamiento = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    equipo = relationship("Equipo", back_populates="detalle_pc")


class LogAuditoria(Base):
    __tablename__ = "log_auditoria"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True, index=True)
    accion = Column(String(255), nullable=False)
    fecha = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    usuario = relationship("Usuario", back_populates="logs_auditoria")


def _column_exists(table: str, column: str) -> bool:
    inspector = inspect(engine)
    if table not in inspector.get_table_names():
        return False
    return column in {c["name"] for c in inspector.get_columns(table)}


def migrate_db() -> None:
    Base.metadata.create_all(bind=engine)

    with engine.connect() as conn:
        if not _column_exists("usuarios", "email"):
            conn.execute(text("ALTER TABLE usuarios ADD COLUMN email VARCHAR(150)"))
        if not _column_exists("usuarios", "password_hash"):
            conn.execute(text("ALTER TABLE usuarios ADD COLUMN password_hash VARCHAR(255)"))
        if not _column_exists("usuarios", "activo"):
            conn.execute(text("ALTER TABLE usuarios ADD COLUMN activo INTEGER DEFAULT 1"))
        if not _column_exists("equipos", "tipo"):
            conn.execute(text("ALTER TABLE equipos ADD COLUMN tipo VARCHAR(30) DEFAULT 'PC'"))
        if not _column_exists("equipos", "piso"):
            conn.execute(text("ALTER TABLE equipos ADD COLUMN piso VARCHAR(10)"))
        if not _column_exists("equipos", "activo"):
            conn.execute(text("ALTER TABLE equipos ADD COLUMN activo INTEGER DEFAULT 1"))
        conn.commit()