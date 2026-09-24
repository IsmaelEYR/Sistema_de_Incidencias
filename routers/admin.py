from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from dependencies import get_db
from config import settings
import schemas
from models import Usuario
from services import incidencias as incidencias_service
from services.usuarios import listar_usuarios, crear_usuario
from exceptions import DuplicateError
from auth.dependencies import require_role
from services.auditoria import registrar_accion

router = APIRouter(prefix="/admin", tags=["Admin"])
templates = Jinja2Templates(directory="templates")

require_supervisor = require_role("Supervisor")

def render_template(template_name: str, context: dict, status_code: int = 200) -> HTMLResponse:
    template = templates.get_template(template_name)
    content = template.render(context)
    return HTMLResponse(content=content, status_code=status_code)


# ─── Dashboard Supervisor ──────────────────────────────────────────
@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_supervisor(request: Request, db: Session = Depends(get_db),
                         user: Usuario = Depends(require_supervisor)):
    incidencias = incidencias_service.listar_incidencias(db)
    ahora = datetime.utcnow()
    for inc in incidencias:
        if inc.fecha_reporte:
            fecha = inc.fecha_reporte.replace(tzinfo=None) if inc.fecha_reporte.tzinfo else inc.fecha_reporte
            diff = ahora - fecha
            horas = int(diff.total_seconds() // 3600)
            minutos = int((diff.total_seconds() % 3600) // 60)
            inc.tiempo_transcurrido = f"{horas}h {minutos}m"
        else:
            inc.tiempo_transcurrido = "—"
    stats = incidencias_service.obtener_estadisticas(db)
    tecnicos = db.query(Usuario).filter(Usuario.rol == "Técnico", Usuario.activo == 1).all()

    context = {
        "request": request,
        "incidencias": incidencias,
        "stats": stats,
        "tecnicos": tecnicos,
        "hospital_name": settings.hospital_name,
        "modo_supervisor": True
    }
    return render_template("dashboard_admin.html", context)


# ─── Gestión de Usuarios ───────────────────────────────────────────
@router.get("/usuarios", response_class=HTMLResponse)
def lista_usuarios(request: Request, db: Session = Depends(get_db),
                   user: Usuario = Depends(require_supervisor)):
    usuarios = listar_usuarios(db)
    context = {
        "request": request,
        "usuarios": usuarios,
        "hospital_name": settings.hospital_name
    }
    return render_template("admin_usuarios.html", context)


@router.get("/usuarios/crear", response_class=HTMLResponse)
def form_crear_usuario(request: Request, user: Usuario = Depends(require_supervisor)):
    context = {
        "request": request,
        "hospital_name": settings.hospital_name,
        "editando": False,
        "usuario": None
    }
    return render_template("admin_usuario_form.html", context)


@router.post("/usuarios/crear")
def crear_usuario_post(
    request: Request,
    nombre: str = Form(...),
    email: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    rol: str = Form(...),
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_supervisor)
):
    from auth.jwt_utils import hash_password
    password_hash = hash_password(password) if password else None
    datos = schemas.UsuarioCreate(
        nombre=nombre,
        email=email,
        password_hash=password_hash,
        rol=rol
    )
    try:
        crear_usuario(db, datos)
        registrar_accion(db, user.id, f"Creó usuario: {nombre}")
        return RedirectResponse("/admin/usuarios", status_code=303)
    except DuplicateError as e:
        context = {
            "request": request,
            "hospital_name": settings.hospital_name,
            "editando": False,
            "error": e.detail
        }
        return render_template("admin_usuario_form.html", context)


@router.get("/usuarios/{id}/editar", response_class=HTMLResponse)
def form_editar_usuario(id: int, request: Request, db: Session = Depends(get_db), user: Usuario = Depends(require_supervisor)):
    from services.usuarios import obtener_usuario
    usuario_editar = obtener_usuario(db, id)
    context = {
        "request": request,
        "hospital_name": settings.hospital_name,
        "editando": True,
        "usuario": usuario_editar
    }
    return render_template("admin_usuario_form.html", context)


@router.post("/usuarios/{id}/editar")
def editar_usuario_post(
    id: int,
    request: Request,
    nombre: str = Form(...),
    email: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    rol: str = Form(...),
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_supervisor)
):
    from auth.jwt_utils import hash_password
    from services.usuarios import actualizar_usuario, obtener_usuario
    
    password_hash = hash_password(password) if password else None
    
    datos = schemas.UsuarioCreate(
        nombre=nombre,
        email=email,
        password_hash=password_hash,
        rol=rol
    )
    try:
        actualizar_usuario(db, id, datos)
        registrar_accion(db, user.id, f"Editó usuario ID {id}")
        return RedirectResponse("/admin/usuarios", status_code=303)
    except DuplicateError as e:
        usuario_editar = obtener_usuario(db, id)
        context = {
            "request": request,
            "hospital_name": settings.hospital_name,
            "editando": True,
            "usuario": usuario_editar,
            "error": e.detail
        }
        return render_template("admin_usuario_form.html", context)


@router.post("/usuarios/{id}/eliminar")
def eliminar_usuario_post(
    id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_supervisor)
):
    from services.usuarios import eliminar_usuario
    eliminar_usuario(db, id)
    registrar_accion(db, user.id, f"Eliminó usuario ID {id}")
    return RedirectResponse("/admin/usuarios", status_code=303)


# ─── Detalle de incidencia ─────────────────────────────────────────
@router.get("/incidencias/{id}/detalle", response_class=HTMLResponse)
def detalle_incidencia_admin(id: int, request: Request, db: Session = Depends(get_db),
                             user: Usuario = Depends(require_supervisor)):
    incidencia = incidencias_service.obtener_incidencia(db, id)
    ahora = datetime.utcnow()
    if incidencia.fecha_reporte:
        fecha = incidencia.fecha_reporte.replace(tzinfo=None) if incidencia.fecha_reporte.tzinfo else incidencia.fecha_reporte
        diff = ahora - fecha
        horas = int(diff.total_seconds() // 3600)
        minutos = int((diff.total_seconds() % 3600) // 60)
        tiempo_abierta = f"{horas}h {minutos}m"
    else:
        tiempo_abierta = "—"

    tecnicos = db.query(Usuario).filter(Usuario.rol == "Técnico", Usuario.activo == 1).all()

    context = {
        "request": request,
        "incidencia": incidencia,
        "tiempo_abierta": tiempo_abierta,
        "tecnicos": tecnicos,
        "hospital_name": settings.hospital_name,
        "modo_supervisor": True
    }
    return render_template("detalle_incidencia.html", context)


# ─── Actualizar incidencia ─────────────────────────────────────────
@router.post("/incidencias/{id}/actualizar")
def actualizar_incidencia_admin(
    id: int,
    accion: str = Form(...),
    nuevo_estado: Optional[str] = Form(None),
    tecnico_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_supervisor)
):
    kwargs = {}
    if accion == "cambiar_estado" and nuevo_estado:
        kwargs["estado"] = nuevo_estado
    elif accion == "asignar_tecnico" and tecnico_id:
        kwargs["tecnico_id"] = tecnico_id
        kwargs["estado"] = "En Proceso"

    datos = schemas.IncidenciaUpdate(**kwargs)

    incidencias_service.actualizar_incidencia(db, id, datos, responsable_id=user.id)
    registrar_accion(db, user.id, f"Actualizó incidencia #{id}: {accion}")
    return RedirectResponse("/admin/dashboard", status_code=303)


# ─── Historial de Movimientos ──────────────────────────────────────
@router.get("/auditoria", response_class=HTMLResponse)
def vista_auditoria(request: Request, db: Session = Depends(get_db), user: Usuario = Depends(require_supervisor)):
    from models import LogAuditoria
    logs = db.query(LogAuditoria).order_by(LogAuditoria.id.desc()).all()
    context = {
        "request": request,
        "logs": logs,
        "hospital_name": settings.hospital_name
    }
    return render_template("auditoria.html", context)


# ─── Copia de Seguridad ────────────────────────────────────────────
@router.get("/backup", dependencies=[Depends(require_supervisor)])
def descargar_backup():
    from fastapi.responses import FileResponse
    return FileResponse(
        path="hospital_incidencias.db",
        media_type="application/octet-stream",
        filename=f"backup_incidencias_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    )