from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import schemas
from config import settings
from dependencies import get_db
from exceptions import DuplicateError
from services import equipos as equipos_service
from auth.dependencies import require_role
from services.auditoria import registrar_accion

router = APIRouter(prefix="/equipos", tags=["Equipos"])
templates = Jinja2Templates(directory="templates")

UBICACIONES = [
    "Laboratorio", "RRHH", "Dirección", "Pagos", "Quirofano",
    "Ingeniería", "Administración", "Historias Médicas",
    "Bienes Nacionales", "Terapia Intensiva", "Trabajo Social",
    "Desarrollo", "Docencia", "Cardiologia", "Cardiovascular",
    "Emergencia", "Otros"
]

# Dependencia para requerir supervisor en las rutas web
require_supervisor = require_role("Supervisor")


# ═══════════════════════════════════════════════════════════════
# Rutas web (deben ir antes de /{id})
# ═══════════════════════════════════════════════════════════════

@router.get("/crear", response_class=HTMLResponse, dependencies=[Depends(require_supervisor)])
def formulario_crear_equipo(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="crear_equipo.html",
        context={
            "hospital_name": settings.hospital_name,
            "error": None,
            "ubicaciones": UBICACIONES,
        },
    )


@router.post("/crear", dependencies=[Depends(require_supervisor)])
def crear_equipo_desde_formulario(
    request: Request,
    ubicacion: str = Form(...),
    tipo: str = Form(...),
    piso: str = Form(None),
    nombre: str = Form(None),
    db: Session = Depends(get_db),
    user = Depends(require_supervisor),
):
    if ubicacion.lower() == "otros":
        ubicacion = request.form().get("ubicacion_otro", "").strip()
        if not ubicacion:
            return templates.TemplateResponse(
                request=request,
                name="crear_equipo.html",
                context={
                    "hospital_name": settings.hospital_name,
                    "error": "Debe especificar la ubicación cuando selecciona 'Otros'",
                    "ubicaciones": UBICACIONES,
                },
            )

    datos = schemas.EquipoCreate(
        nombre=nombre if nombre else None,
        ubicacion=ubicacion,
        tipo=tipo,
        piso=piso,
    )
    try:
        equipo_nuevo = equipos_service.crear_equipo(db, datos)
        registrar_accion(db, user.id, f"Creó equipo: {equipo_nuevo.nombre} (ID: {equipo_nuevo.id})")
        return RedirectResponse("/equipos/lista?mensaje=Equipo+creado", status_code=303)
    except DuplicateError as e:
        return templates.TemplateResponse(
            request=request,
            name="crear_equipo.html",
            context={
                "hospital_name": settings.hospital_name,
                "error": e.detail,
                "ubicaciones": UBICACIONES,
            },
        )
    except Exception as e:
        return templates.TemplateResponse(
            request=request,
            name="crear_equipo.html",
            context={
                "hospital_name": settings.hospital_name,
                "error": "Ha ocurrido un error interno al procesar la solicitud.",
                "ubicaciones": UBICACIONES,
            },
        )


@router.get("/lista", response_class=HTMLResponse, dependencies=[Depends(require_supervisor)])
def lista_equipos(request: Request, db: Session = Depends(get_db)):
    equipos = equipos_service.listar_equipos(db)
    return templates.TemplateResponse(
        request=request,
        name="lista_equipos.html",
        context={
            "equipos": equipos,
            "hospital_name": settings.hospital_name,
        },
    )


@router.get("/{id}/editar", response_class=HTMLResponse, dependencies=[Depends(require_supervisor)])
def editar_equipo_form(id: int, request: Request, db: Session = Depends(get_db)):
    equipo = equipos_service.obtener_equipo(db, id)
    return templates.TemplateResponse(
        request=request,
        name="editar_equipo.html",
        context={
            "equipo": equipo,
            "hospital_name": settings.hospital_name,
            "ubicaciones": UBICACIONES,
        },
    )


@router.post("/{id}/editar", dependencies=[Depends(require_supervisor)])
def actualizar_equipo(
    id: int,
    request: Request,
    ubicacion: str = Form(...),
    tipo: str = Form(...),
    piso: str = Form(None),
    nombre: str = Form(None),
    db: Session = Depends(get_db),
    user = Depends(require_supervisor),
):
    if ubicacion.lower() == "otros":
        ubicacion = request.form().get("ubicacion_otro", "").strip()
        if not ubicacion:
            equipo = equipos_service.obtener_equipo(db, id)
            return templates.TemplateResponse(
                request=request,
                name="editar_equipo.html",
                context={
                    "equipo": equipo,
                    "error": "Debe especificar la ubicación cuando selecciona 'Otros'",
                    "hospital_name": settings.hospital_name,
                    "ubicaciones": UBICACIONES,
                },
            )

    datos = schemas.EquipoCreate(
        nombre=nombre if nombre else None,
        ubicacion=ubicacion,
        tipo=tipo,
        piso=piso,
    )
    try:
        equipos_service.actualizar_equipo(db, id, datos)
        registrar_accion(db, user.id, f"Editó equipo ID {id}")
        return RedirectResponse("/equipos/lista?mensaje=Equipo+actualizado", status_code=303)
    except DuplicateError as e:
        equipo = equipos_service.obtener_equipo(db, id)
        return templates.TemplateResponse(
            request=request,
            name="editar_equipo.html",
            context={
                "equipo": equipo,
                "error": e.detail,
                "hospital_name": settings.hospital_name,
                "ubicaciones": UBICACIONES,
            },
        )


@router.post("/{id}/eliminar", dependencies=[Depends(require_supervisor)])
def eliminar_equipo(id: int, db: Session = Depends(get_db), user = Depends(require_supervisor)):
    equipos_service.eliminar_equipo(db, id)
    registrar_accion(db, user.id, f"Eliminó equipo ID {id}")
    return RedirectResponse("/equipos/lista?mensaje=Equipo+eliminado", status_code=303)


# ═══════════════════════════════════════════════════════════════
# Rutas de Detalles Técnicos de PC
# ═══════════════════════════════════════════════════════════════

@router.get("/{id}/detalles-tecnicos", response_class=HTMLResponse, dependencies=[Depends(require_supervisor)])
def detalles_tecnicos_pc(id: int, request: Request, db: Session = Depends(get_db)):
    equipo = equipos_service.obtener_equipo(db, id)
    if equipo.tipo.lower() != "pc":
        return RedirectResponse("/equipos/lista?error=El+equipo+no+es+PC", status_code=303)

    from models import Incidencia
    import datetime
    
    ultima_resuelta = db.query(Incidencia).filter(
        Incidencia.equipo_id == id,
        Incidencia.estado == "Resuelta"
    ).order_by(Incidencia.fecha_reporte.desc()).first()

    mantenimiento_info = None
    if ultima_resuelta and ultima_resuelta.fecha_reporte:
        fecha = ultima_resuelta.fecha_reporte
        prox = fecha + datetime.timedelta(days=90)
        mantenimiento_info = {
            "fecha": fecha.strftime("%d/%m/%Y"),
            "tecnico": ultima_resuelta.tecnico.nombre if ultima_resuelta.tecnico else "Desconocido",
            "proximo": prox.strftime("%d/%m/%Y")
        }

    return templates.TemplateResponse(
        request=request,
        name="detalle_pc.html",
        context={
            "equipo": equipo,
            "detalle": equipo.detalle_pc,
            "mantenimiento_info": mantenimiento_info,
            "hospital_name": settings.hospital_name,
        },
    )

@router.post("/{id}/detalles-tecnicos", dependencies=[Depends(require_supervisor)])
async def guardar_detalles_tecnicos(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
    user = Depends(require_supervisor)
):
    equipo = equipos_service.obtener_equipo(db, id)
    if equipo.tipo.lower() != "pc":
        return RedirectResponse("/equipos/lista?error=El+equipo+no+es+PC", status_code=303)
    
    form_data = await request.form()
    from models import DetallePC
    
    detalle = equipo.detalle_pc
    is_new = False
    if not detalle:
        detalle = DetallePC(equipo_id=id)
        is_new = True

    # 1. Info General
    detalle.nombre_red = form_data.get("nombre_red", "").strip()
    detalle.bien_nacional = form_data.get("bien_nacional", "").strip()
    detalle.marca_modelo_cpu = form_data.get("marca_modelo_cpu", "").strip()
    detalle.usuario_asignado = form_data.get("usuario_asignado", "").strip()
    
    # 2. Red y Software
    detalle.ip = form_data.get("ip", "").strip()
    detalle.tipo_ip = form_data.get("tipo_ip", "").strip()
    detalle.mac = form_data.get("mac", "").strip()
    detalle.sistema_operativo = form_data.get("sistema_operativo", "").strip()
    detalle.version_so = form_data.get("version_so", "").strip()
    detalle.dominio = form_data.get("dominio", "").strip()
    detalle.antivirus = form_data.get("antivirus", "").strip()
    detalle.software_adicional = form_data.get("software_adicional", "").strip()
    
    # 3. Hardware
    detalle.procesador = form_data.get("procesador", "").strip()
    ram_gb_val = form_data.get("ram_gb", "").strip()
    detalle.ram_gb = int(ram_gb_val) if ram_gb_val.isdigit() else None
    detalle.ram_tipo = form_data.get("ram_tipo", "").strip()
    detalle.ram_slots = form_data.get("ram_slots", "").strip()
    detalle.almacenamiento_tipo = form_data.get("almacenamiento_tipo", "").strip()
    detalle.almacenamiento_capacidad = form_data.get("almacenamiento_capacidad", "").strip()
    
    # Puertos de video (checkboxes)
    puertos = []
    for p in ["hdmi", "displayport", "usb_c", "vga"]:
        if form_data.get(f"puerto_{p}"):
            puertos.append(p.upper().replace("_", "-"))
    detalle.puertos_video = ", ".join(puertos)
    
    # 4. Perifericos
    detalle.monitor_marca = form_data.get("monitor_marca", "").strip()
    detalle.monitor_modelo = form_data.get("monitor_modelo", "").strip()
    detalle.monitor_serial = form_data.get("monitor_serial", "").strip()
    detalle.monitor_bn = form_data.get("monitor_bn", "").strip()
    
    detalle.teclado_marca = form_data.get("teclado_marca", "").strip()
    detalle.teclado_serial = form_data.get("teclado_serial", "").strip()
    detalle.teclado_bn = form_data.get("teclado_bn", "").strip()
    
    detalle.mouse_marca = form_data.get("mouse_marca", "").strip()
    detalle.mouse_serial = form_data.get("mouse_serial", "").strip()
    detalle.mouse_bn = form_data.get("mouse_bn", "").strip()
    
    detalle.proteccion_electrica_tipo = form_data.get("proteccion_electrica_tipo", "").strip()
    detalle.proteccion_electrica_marca = form_data.get("proteccion_electrica_marca", "").strip()
    detalle.proteccion_electrica_bn = form_data.get("proteccion_electrica_bn", "").strip()
    
    detalle.impresora_marca = form_data.get("impresora_marca", "").strip()
    detalle.impresora_modelo = form_data.get("impresora_modelo", "").strip()
    detalle.impresora_ip = form_data.get("impresora_ip", "").strip()
    detalle.impresora_bn = form_data.get("impresora_bn", "").strip()
    
    # 5. Cierre
    detalle.observaciones = form_data.get("observaciones", "").strip()
    
    if is_new:
        db.add(detalle)
        registrar_accion(db, user.id, f"Añadió detalles técnicos avanzados al PC ID {id}")
    else:
        registrar_accion(db, user.id, f"Actualizó detalles técnicos avanzados del PC ID {id}")
        
    db.commit()
    return RedirectResponse(f"/equipos/{id}/detalles-tecnicos?mensaje=Ficha+Técnica+guardada", status_code=303)

@router.get("/{id}/ficha-tecnica", response_class=HTMLResponse, dependencies=[Depends(require_supervisor)])
def ficha_tecnica_pc(id: int, request: Request, db: Session = Depends(get_db)):
    equipo = equipos_service.obtener_equipo(db, id)
    if equipo.tipo.lower() != "pc":
        return RedirectResponse("/equipos/lista?error=El+equipo+no+es+PC", status_code=303)

    from models import Incidencia
    import datetime
    
    ultima_resuelta = db.query(Incidencia).filter(
        Incidencia.equipo_id == id,
        Incidencia.estado == "Resuelta"
    ).order_by(Incidencia.fecha_reporte.desc()).first()

    mantenimiento_info = None
    if ultima_resuelta and ultima_resuelta.fecha_reporte:
        fecha = ultima_resuelta.fecha_reporte
        prox = fecha + datetime.timedelta(days=90)
        mantenimiento_info = {
            "fecha": fecha.strftime("%d/%m/%Y"),
            "tecnico": ultima_resuelta.tecnico.nombre if ultima_resuelta.tecnico else "Desconocido",
            "proximo": prox.strftime("%d/%m/%Y")
        }

    return templates.TemplateResponse(
        request=request,
        name="ficha_tecnica.html",
        context={
            "equipo": equipo,
            "detalle": equipo.detalle_pc,
            "mantenimiento_info": mantenimiento_info,
            "hospital_name": settings.hospital_name,
        },
    )


# ═══════════════════════════════════════════════════════════════
# Rutas API
# ═══════════════════════════════════════════════════════════════

@router.get("/", response_model=list[schemas.EquipoResponse])
def listar_equipos_api(db: Session = Depends(get_db), user = Depends(require_supervisor)):
    equipos = equipos_service.listar_equipos(db)
    return [schemas.EquipoResponse.model_validate(e) for e in equipos]


@router.get("/{id}", response_model=schemas.EquipoResponse)
def obtener_equipo_api(id: int, db: Session = Depends(get_db), user = Depends(require_supervisor)):
    equipo = equipos_service.obtener_equipo(db, id)
    return schemas.EquipoResponse.model_validate(equipo)


@router.post("/", response_model=schemas.EquipoResponse, status_code=201)
def crear_equipo_api(datos: schemas.EquipoCreate, db: Session = Depends(get_db), user = Depends(require_supervisor)):
    equipo = equipos_service.crear_equipo(db, datos)
    registrar_accion(db, user.id, f"Creó equipo vía API: {equipo.nombre} (ID: {equipo.id})")
    return schemas.EquipoResponse.model_validate(equipo)


@router.get("/{id}/qr")
def generar_qr(id: int, db: Session = Depends(get_db), user = Depends(require_supervisor)):
    return equipos_service.generar_qr_equipo(db, id)