from datetime import datetime
from enum import Enum
from typing import Optional, Union
from pydantic import BaseModel, Field, validator


# =========================================================================
# ENUMS
# =========================================================================
class RolEnum(str, Enum):
    administrador = "Administrador"
    supervisor = "Supervisor"
    tecnico = "Técnico"
    asistente = "Asistente Administrativo"


class EstadoIncidenciaEnum(str, Enum):
    # Estandarizado para PostgreSQL y vistas SQL
    pendiente = "PENDIENTE"
    en_proceso = "EN_PROCESO"
    resuelto = "RESUELTO"
    cerrado = "CERRADO"
    cancelado = "CANCELADO"

    @classmethod
    def _missing_(cls, value: object):
        # Tolera variantes con espacios o minúsculas que vengan de formularios web
        if isinstance(value, str):
            val_norm = value.strip().upper().replace(" ", "_")
            if val_norm in ["RESUELTA", "RESUELTO"]:
                return cls.resuelto
            for member in cls:
                if member.value == val_norm:
                    return member
        return None


# =========================================================================
# 1. ESQUEMAS PARA CATÁLOGOS (tipo_general)
# =========================================================================
class TipoGeneralBase(BaseModel):
    categoria: str = Field(..., max_length=50)  # UBICACION, ESTADO_EQUIPO, ACCION
    nombre: str = Field(..., max_length=150)
    descripcion: Optional[str] = None
    activo: bool = True


class TipoGeneralCreate(TipoGeneralBase):
    pass


class TipoGeneralResponse(TipoGeneralBase):
    id: int
    creado_en: Optional[datetime] = None
    actualizado_en: Optional[datetime] = None

    class Config:
        from_attributes = True


# =========================================================================
# 2. ESQUEMAS PARA USUARIOS
# =========================================================================
class UsuarioCreate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    email: Optional[str] = Field(None, max_length=150)
    password_hash: Optional[str] = Field(None, max_length=255)
    rol: RolEnum


class UsuarioResponse(BaseModel):
    id: int
    nombre: str
    email: Optional[str] = None
    rol: str
    activo: Union[bool, int]

    class Config:
        from_attributes = True


# =========================================================================
# 3. ESQUEMAS PARA EQUIPOS
# =========================================================================
class EquipoCreate(BaseModel):
    nombre: Optional[str] = Field(None, max_length=150)
    ubicacion: Optional[str] = Field(None, max_length=150)
    tipo: Optional[str] = Field("PC", max_length=30)
    piso: Optional[str] = Field(None, max_length=10)
    codigo_qr: Optional[str] = Field(None, max_length=100)
    
    # Nuevas llaves foráneas a tipo_general
    tipo_ubicacion_id: Optional[int] = None
    tipo_estado_id: Optional[int] = None

    @validator("tipo")
    def tipo_validar(cls, v):
        if v and v.lower() not in ["pc", "impresora"]:
            raise ValueError('Tipo debe ser "PC" o "Impresora"')
        return v.strip().capitalize() if v else "PC"


class EquipoResponse(BaseModel):
    id: int
    nombre: Optional[str] = None
    codigo_qr: str
    tipo_ubicacion_id: Optional[int] = None
    tipo_estado_id: Optional[int] = None
    ubicacion: Optional[str] = None
    tipo: Optional[str] = "PC"
    piso: Optional[str] = None
    activo: Union[bool, int] = True

    class Config:
        from_attributes = True


# =========================================================================
# 4. ESQUEMAS PARA INCIDENCIAS Y REPORTES EXTERNOS (QR)
# =========================================================================
class IncidenciaCreate(BaseModel):
    descripcion: str = Field(..., min_length=5, max_length=1000)
    equipo_id: int = Field(..., gt=0)
    tecnico_id: Optional[int] = Field(None, gt=0)
    reportado_por_nombre: Optional[str] = Field(None, max_length=150)
    reportado_por_cedula: Optional[str] = Field(None, max_length=50)


class IncidenciaReporteQR(BaseModel):
    descripcion: str = Field(..., min_length=5, max_length=1000)
    reportado_por_nombre: str = Field(..., min_length=3, max_length=150)
    reportado_por_cedula: str = Field(..., min_length=6, max_length=50)


class IncidenciaUpdate(BaseModel):
    estado: Optional[Union[EstadoIncidenciaEnum, str]] = None
    tecnico_id: Optional[int] = Field(None, gt=0)
    detalle_verificacion_cierre: Optional[str] = None


class IncidenciaResponse(BaseModel):
    id: int
    descripcion: str
    estado: str
    fecha_reporte: datetime
    equipo_id: int
    tecnico_id: Optional[int] = None
    reportado_por_nombre: Optional[str] = None
    reportado_por_cedula: Optional[str] = None

    # Métricas y SLAs
    fecha_asignacion: Optional[datetime] = None
    fecha_proceso: Optional[datetime] = None
    fecha_solucion: Optional[datetime] = None
    fecha_cierre: Optional[datetime] = None
    duracion_hasta_asignacion_min: Optional[int] = None
    duracion_proceso_min: Optional[int] = None
    duracion_solucion_min: Optional[int] = None
    duracion_total_min: Optional[int] = None
    duracion_total_horas: Optional[int] = None
    detalle_verificacion_cierre: Optional[str] = None

    class Config:
        from_attributes = True


class IncidenciaDetalleResponse(BaseModel):
    id: int
    descripcion: str
    estado: str
    fecha_reporte: datetime
    equipo_id: int
    equipo_nombre: Optional[str] = None
    ubicacion_actual: Optional[str] = None
    estado_operativo_maquina: Optional[str] = None
    
    # Técnico
    tecnico_id: Optional[int] = None
    tecnico_nombre: Optional[str] = None
    tecnico_email: Optional[str] = None

    # Reportante externo
    reportado_por_nombre: Optional[str] = None
    reportado_por_cedula: Optional[str] = None

    # SLAs y tiempos formateados
    duracion_total_min: Optional[int] = None
    duracion_total_formateada: Optional[str] = None
    detalle_verificacion_cierre: Optional[str] = None

    class Config:
        from_attributes = True


# =========================================================================
# 5. ESQUEMAS PARA DETALLE DE HARDWARE (detalle_pc)
# =========================================================================
class DetallePCCreate(BaseModel):
    usuario_asignado: Optional[str] = None
    nombre_red: Optional[str] = None
    bien_nacional: Optional[str] = None
    marca_modelo_cpu: Optional[str] = None
    ip: Optional[str] = None
    tipo_ip: Optional[str] = None
    mac: Optional[str] = None
    sistema_operativo: Optional[str] = None
    version_so: Optional[str] = None
    dominio: Optional[str] = None
    antivirus: Optional[str] = None
    software_adicional: Optional[str] = None
    procesador: Optional[str] = None
    ram_gb: Optional[int] = None
    ram_tipo: Optional[str] = None
    ram_slots: Optional[str] = None
    almacenamiento_tipo: Optional[str] = None
    almacenamiento_capacidad: Optional[str] = None
    puertos_video: Optional[str] = None
    monitor_marca: Optional[str] = None
    monitor_modelo: Optional[str] = None
    monitor_serial: Optional[str] = None
    monitor_bn: Optional[str] = None
    teclado_marca: Optional[str] = None
    teclado_serial: Optional[str] = None
    teclado_bn: Optional[str] = None
    mouse_marca: Optional[str] = None
    mouse_serial: Optional[str] = None
    mouse_bn: Optional[str] = None
    proteccion_electrica_tipo: Optional[str] = None
    proteccion_electrica_marca: Optional[str] = None
    proteccion_electrica_bn: Optional[str] = None
    impresora_marca: Optional[str] = None
    impresora_modelo: Optional[str] = None
    impresora_ip: Optional[str] = None
    impresora_bn: Optional[str] = None
    observaciones: Optional[str] = None


class DetallePCResponse(DetallePCCreate):
    id: int
    equipo_id: int
    fecha_levantamiento: Optional[datetime] = None

    class Config:
        from_attributes = True


# =========================================================================
# 6. ESQUEMAS DE AUDITORÍA Y RESPUESTAS GENÉRICAS
# =========================================================================
class LogAuditoriaResponse(BaseModel):
    id: int
    usuario_id: Optional[int] = None
    accion: str
    fecha: datetime

    class Config:
        from_attributes = True


class MensajeResponse(BaseModel):
    mensaje: str
    version: str