from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from enum import Enum


class RolEnum(str, Enum):
    supervisor = "Supervisor"
    tecnico = "Técnico"
    asistente = "Asistente Administrativo"


class EstadoIncidenciaEnum(str, Enum):
    pendiente = "Pendiente"
    en_proceso = "En Proceso"
    resuelta = "Resuelta"
    cancelada = "Cancelada"



class UsuarioCreate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    email: Optional[str] = Field(None, max_length=150)
    password_hash: Optional[str] = Field(None, max_length=255)
    rol: RolEnum

class UsuarioResponse(BaseModel):
    id: int
    nombre: str
    email: Optional[str]
    rol: str
    activo: int

    class Config:
        from_attributes = True



class EquipoCreate(BaseModel):
    nombre: Optional[str] = Field(None, max_length=150)
    ubicacion: str = Field(..., max_length=150)
    tipo: str = Field(..., max_length=30)
    piso: Optional[str] = Field(None, max_length=10)
    codigo_qr: Optional[str] = Field(None, max_length=100)

    @validator('ubicacion')
    def ubicacion_validar(cls, v):
        permitidas = [
            "laboratorio", "rrhh", "dirección", "pagos", "quirofano",
            "ingeniería", "administración", "historias médicas",
            "bienes nacionales", "terapia intensiva", "trabajo social",
            "desarrollo", "docencia", "cardiologia", "cardiovascular",
            "emergencia", "otros"
        ]
        if v.lower() not in permitidas:
            raise ValueError(f"Ubicación no permitida. Opciones: {', '.join(permitidas)}")
        return v.strip()

    @validator('tipo')
    def tipo_validar(cls, v):
        if v.lower() not in ["pc", "impresora"]:
            raise ValueError('Tipo debe ser "PC" o "Impresora"')
        return v.strip().capitalize()


class EquipoResponse(BaseModel):
    id: int
    nombre: Optional[str] = None
    ubicacion: str
    codigo_qr: str
    tipo: str
    piso: Optional[str] = None

    class Config:
        from_attributes = True

class IncidenciaCreate(BaseModel):
    descripcion: str = Field(..., min_length=5, max_length=1000)
    equipo_id: int = Field(..., gt=0)
    tecnico_id: Optional[int] = Field(None, gt=0)


class IncidenciaReporteQR(BaseModel):
    descripcion: str = Field(..., min_length=5, max_length=1000)



class IncidenciaResponse(BaseModel):
    id: int
    descripcion: str
    estado: str
    fecha_reporte: datetime
    equipo_id: int
    tecnico_id: Optional[int]

    class Config:
        from_attributes = True


class IncidenciaUpdate(BaseModel):
    estado: Optional[EstadoIncidenciaEnum] = None
    tecnico_id: Optional[int] = Field(None, gt=0)


class IncidenciaDetalleResponse(BaseModel):
    id: int
    descripcion: str
    estado: str
    fecha_reporte: datetime
    equipo_id: int
    equipo_nombre: str
    equipo_ubicacion: str
    tecnico_id: Optional[int]
    tecnico_nombre: Optional[str]

    class Config:
        from_attributes = True

class MensajeResponse(BaseModel):
    mensaje: str
    version: str


class DetallePCCreate(BaseModel):
    pass

class DetallePCResponse(BaseModel):
    id: int
    equipo_id: int
    
    # Info General
    nombre_red: Optional[str] = None
    bien_nacional: Optional[str] = None
    marca_modelo_cpu: Optional[str] = None
    usuario_asignado: Optional[str] = None
    
    # Red y Software
    ip: Optional[str] = None
    tipo_ip: Optional[str] = None
    mac: Optional[str] = None
    sistema_operativo: Optional[str] = None
    version_so: Optional[str] = None
    dominio: Optional[str] = None
    antivirus: Optional[str] = None
    software_adicional: Optional[str] = None
    
    # Hardware
    procesador: Optional[str] = None
    ram_gb: Optional[int] = None
    ram_tipo: Optional[str] = None
    ram_slots: Optional[str] = None
    almacenamiento_tipo: Optional[str] = None
    almacenamiento_capacidad: Optional[str] = None
    puertos_video: Optional[str] = None
    
    # Perifericos
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
    
    # Cierre
    observaciones: Optional[str] = None
    fecha_levantamiento: Optional[datetime] = None

    class Config:
        from_attributes = True


class LogAuditoriaResponse(BaseModel):
    id: int
    usuario_id: Optional[int]
    accion: str
    fecha: datetime

    class Config:
        from_attributes = True