import os
import subprocess
import tempfile
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette.background import BackgroundTasks

import schemas
from auth.dependencies import (
    ROL_ADMIN,
    ROL_SUPERVISOR,
    normalizar_rol,
    require_admin,
    require_panel,
)
from config import settings
from database import engine
from dependencies import get_db
from exceptions import DuplicateError
from models import Usuario, caracas_now
from services import incidencias as incidencias_service
from services.auditoria import registrar_accion
from services.usuarios import crear_usuario, listar_usuarios

router = APIRouter(prefix="/admin", tags=["Admin"])
templates = Jinja2Templates(directory="templates")


def render_template(template_name: str, context: dict, status_code: int = 200) -> HTMLResponse:
    template = templates.get_template(template_name)
    content = template.render(context)
    return HTMLResponse(content=content, status_code=status_code)


def _contexto_usuario(user: Usuario) -> dict:
    """Variables de rol comunes para las plantillas (siempre normalizadas)."""
    rol = normalizar_rol(user.rol)
    return {"usuario": user, "rol_usuario": rol, "es_admin": rol == ROL_ADMIN}


def _tecnicos_activos(db: Session) -> list[Usuario]:
    """Obtiene los usuarios con roles operativos o técnicos que estén activos."""
    roles_permitidos = [
        "técnico", "tecnico", "técnica", "tecnica",
        "asistente", "soporte", "supervisor", "administrador", "admin"
    ]
    return (
        db.query(Usuario)
        .filter(
            func.lower(Usuario.rol).in_(roles_permitidos),
            Usuario.activo.is_(True)
        )
        .order_by(Usuario.nombre)
        .all()
    )


def _primer_error(exc: ValidationError) -> str:
    errores = exc.errors()
    return errores[0].get("msg", "Datos inválidos") if errores else "Datos inválidos"


# ─── Dashboard (Administrador / Supervisor / Asistente) ─────────────────
@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_supervisor(
    request: Request,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_panel),
):
    incidencias = incidencias_service.listar_incidencias_dashboard(db)
    ahora = caracas_now()
    zona_caracas = ZoneInfo("America/Caracas")

    for inc in incidencias:
        if inc.fecha_reporte:
            fecha_segura = (
                inc.fecha_reporte.replace(tzinfo=zona_caracas)
                if inc.fecha_reporte.tzinfo is None
                else inc.fecha_reporte
            )
            diff = ahora - fecha_segura
            horas = int(diff.total_seconds() // 3600)
            minutos = int((diff.total_seconds() % 3600) // 60)
            inc.tiempo_transcurrido = f"{horas}h {minutos}m"
        else:
            inc.tiempo_transcurrido = "—"

    stats = incidencias_service.obtener_estadisticas(db)
    tecnicos = _tecnicos_activos(db)

    context = {
        "request": request,
        "incidencias": incidencias,
        "stats": stats,
        "tecnicos": tecnicos,
        "hospital_name": settings.hospital_name,
        "modo_supervisor": True,
        **_contexto_usuario(user),
    }
    return render_template("dashboard_admin.html", context)


# ─── Historial General de Incidencias ──────────────────────────────
@router.get("/historial-general", response_class=HTMLResponse)
def historial_general(
    request: Request,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_panel),
):
    todas_incidencias = incidencias_service.listar_incidencias(db)
    # Filtramos resueltas y cerradas tolerando variantes
    estados_resueltos = ["RESUELTO", "CERRADO", "Resuelta", "Resuelto", "Cerrado"]
    incidencias = [
        inc for inc in todas_incidencias
        if (inc.estado and inc.estado.strip() in estados_resueltos)
    ]

    ahora = caracas_now()
    zona_caracas = ZoneInfo("America/Caracas")

    for inc in incidencias:
        if inc.fecha_reporte:
            fecha_segura = (
                inc.fecha_reporte.replace(tzinfo=zona_caracas)
                if inc.fecha_reporte.tzinfo is None
                else inc.fecha_reporte
            )
            fecha_resolucion = inc.fecha_cierre or (inc.historial[0].fecha if inc.historial else fecha_segura)
            fecha_resolucion_segura = (
                fecha_resolucion.replace(tzinfo=zona_caracas)
                if fecha_resolucion.tzinfo is None
                else fecha_resolucion
            )
            inc.fecha_resolucion_str = fecha_resolucion_segura.strftime("%d/%m/%Y %H:%M")
            inc.fecha_mantenimiento = fecha_resolucion_segura + timedelta(days=90)
        else:
            inc.fecha_resolucion_str = "—"
            inc.fecha_mantenimiento = None

    context = {
        "request": request,
        "incidencias": incidencias,
        "hospital_name": settings.hospital_name,
        "modo_supervisor": True,
        **_contexto_usuario(user),
    }
    return render_template("historial_admin.html", context)


# ─── Gestión de Usuarios ───────────────────────────────────────────
@router.get("/usuarios", response_class=HTMLResponse)
def lista_usuarios(
    request: Request,
    inactivos: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_admin),
):
    viendo_inactivos = inactivos == "1"

    if viendo_inactivos:
        usuarios = db.query(Usuario).filter(Usuario.activo.is_(False)).order_by(Usuario.nombre).all()
    else:
        usuarios = db.query(Usuario).filter(Usuario.activo.is_(True)).order_by(Usuario.nombre).all()

    context = {
        "request": request,
        "usuarios": usuarios,
        "viendo_inactivos": viendo_inactivos,
        "error": error,
        "hospital_name": settings.hospital_name,
        **_contexto_usuario(user),
    }
    return render_template("admin_usuarios.html", context)


@router.get("/usuarios/crear", response_class=HTMLResponse)
def form_crear_usuario(request: Request, user: Usuario = Depends(require_admin)):
    context = {
        "request": request,
        "hospital_name": settings.hospital_name,
        "editando": False,
        "usuario_form": None,
        **_contexto_usuario(user),
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
    user: Usuario = Depends(require_admin),
):
    from auth.jwt_utils import hash_password

    password_hash = hash_password(password) if password else None
    try:
        datos = schemas.UsuarioCreate(
            nombre=nombre,
            email=email or None,
            password_hash=password_hash,
            rol=rol,
        )
        crear_usuario(db, datos)
        registrar_accion(db, user.id, f"Creó usuario: {nombre}")
        return RedirectResponse("/admin/usuarios", status_code=303)
    except (DuplicateError, ValidationError) as e:
        error = e.detail if isinstance(e, DuplicateError) else _primer_error(e)
        context = {
            "request": request,
            "hospital_name": settings.hospital_name,
            "editando": False,
            "usuario_form": None,
            "error": error,
            **_contexto_usuario(user),
        }
        code = status.HTTP_409_CONFLICT if isinstance(e, DuplicateError) else status.HTTP_422_UNPROCESSABLE_ENTITY
        return render_template("admin_usuario_form.html", context, status_code=code)


@router.get("/usuarios/{id}/editar", response_class=HTMLResponse)
def form_editar_usuario(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_admin),
):
    from services.usuarios import obtener_usuario

    usuario_editar = obtener_usuario(db, id)
    context = {
        "request": request,
        "hospital_name": settings.hospital_name,
        "editando": True,
        "usuario_form": usuario_editar,
        **_contexto_usuario(user),
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
    user: Usuario = Depends(require_admin),
):
    from auth.jwt_utils import hash_password
    from services.usuarios import actualizar_usuario, obtener_usuario

    password_hash = hash_password(password) if password else None

    try:
        datos = schemas.UsuarioCreate(
            nombre=nombre,
            email=email or None,
            password_hash=password_hash,
            rol=rol,
        )
        actualizar_usuario(db, id, datos)
        registrar_accion(db, user.id, f"Editó usuario ID {id}")
        return RedirectResponse("/admin/usuarios", status_code=303)
    except (DuplicateError, ValidationError) as e:
        error = e.detail if isinstance(e, DuplicateError) else _primer_error(e)
        usuario_editar = obtener_usuario(db, id)
        context = {
            "request": request,
            "hospital_name": settings.hospital_name,
            "editando": True,
            "usuario_form": usuario_editar,
            "error": error,
            **_contexto_usuario(user),
        }
        code = status.HTTP_409_CONFLICT if isinstance(e, DuplicateError) else status.HTTP_422_UNPROCESSABLE_ENTITY
        return render_template("admin_usuario_form.html", context, status_code=code)


@router.post("/usuarios/{id}/eliminar")
def eliminar_usuario_post(
    id: int,
    password_confirmacion: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_admin),
):
    from auth.jwt_utils import verificar_password
    from services.usuarios import eliminar_usuario, obtener_usuario

    usuario_a_eliminar = obtener_usuario(db, id)

    if usuario_a_eliminar.id == user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes eliminar tu propio usuario mientras tienes la sesión activa",
        )

    if normalizar_rol(usuario_a_eliminar.rol) == ROL_SUPERVISOR:
        if not password_confirmacion or not verificar_password(
            password_confirmacion, usuario_a_eliminar.password_hash or ""
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Contraseña incorrecta para eliminar supervisor",
            )

    eliminar_usuario(db, id)
    registrar_accion(db, user.id, f"Eliminó usuario ID {id} (Rol: {usuario_a_eliminar.rol})")
    return RedirectResponse("/admin/usuarios", status_code=303)


# ─── Detalle de incidencia ─────────────────────────────────────────
@router.get("/incidencias/{id}/detalle", response_class=HTMLResponse)
def detalle_incidencia_admin(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_panel),
):
    incidencia = incidencias_service.obtener_incidencia(db, id)
    ahora = caracas_now()
    zona_caracas = ZoneInfo("America/Caracas")

    if incidencia.fecha_reporte:
        fecha_segura = (
            incidencia.fecha_reporte.replace(tzinfo=zona_caracas)
            if incidencia.fecha_reporte.tzinfo is None
            else incidencia.fecha_reporte
        )
        diff = ahora - fecha_segura
        horas = int(diff.total_seconds() // 3600)
        minutos = int((diff.total_seconds() % 3600) // 60)
        tiempo_abierta = f"{horas}h {minutos}m"
    else:
        tiempo_abierta = "—"

    tecnicos = _tecnicos_activos(db)

    context = {
        "request": request,
        "incidencia": incidencia,
        "tiempo_abierta": tiempo_abierta,
        "tecnicos": tecnicos,
        "hospital_name": settings.hospital_name,
        "modo_supervisor": True,
        **_contexto_usuario(user),
    }
    return render_template("detalle_incidencia.html", context)


# ─── Actualizar incidencia ─────────────────────────────────────────
@router.post("/incidencias/{id}/actualizar")
def actualizar_incidencia_admin(
    id: int,
    accion: str = Form(...),
    nuevo_estado: Optional[str] = Form(None),
    tecnico_id: Optional[str] = Form(None),
    detalle_cierre: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_panel),
):
    kwargs = {}

    # Limpieza de técnico_id
    id_tecnico_int = None
    if tecnico_id and str(tecnico_id).strip() not in ["", "None", "0"]:
        try:
            id_tecnico_int = int(tecnico_id)
        except ValueError:
            id_tecnico_int = None

    if accion == "cambiar_estado" and nuevo_estado:
        kwargs["estado"] = nuevo_estado
        if detalle_cierre:
            kwargs["detalle_verificacion_cierre"] = detalle_cierre
    elif accion == "asignar_tecnico" and id_tecnico_int:
        kwargs["tecnico_id"] = id_tecnico_int
        kwargs["estado"] = "EN_PROCESO"
    elif accion == "cerrar_caso":
        kwargs["estado"] = "RESUELTO"
        if detalle_cierre:
            kwargs["detalle_verificacion_cierre"] = detalle_cierre

    datos = schemas.IncidenciaUpdate(**kwargs)

    incidencias_service.actualizar_incidencia(db, id, datos, responsable_id=user.id)
    registrar_accion(db, user.id, f"Actualizó incidencia #{id}: {accion}")
    return RedirectResponse("/admin/dashboard", status_code=303)


# ─── Historial de Movimientos ──────────────────────────────────────
@router.get("/auditoria", response_class=HTMLResponse)
def vista_auditoria(
    request: Request,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_admin),
):
    from models import LogAuditoria

    logs = db.query(LogAuditoria).order_by(LogAuditoria.id.desc()).all()
    context = {
        "request": request,
        "logs": logs,
        "hospital_name": settings.hospital_name,
        **_contexto_usuario(user),
    }
    return render_template("auditoria.html", context)


# ─── Copia de Seguridad PostgreSQL (pg_dump) ───────────────────────
@router.get("/backup", dependencies=[Depends(require_admin)])
def descargar_backup(background_tasks: BackgroundTasks):
    db_url = engine.url
    db_name = db_url.database or "sistema_de_incidencias"
    db_user = db_url.username or "postgres"
    db_host = db_url.host or "localhost"
    db_port = str(db_url.port or 5432)
    db_password = db_url.password or ""

    env = os.environ.copy()
    if db_password:
        env["PGPASSWORD"] = db_password

    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_file = tempfile.NamedTemporaryFile(
        delete=False, prefix=f"backup_{db_name}_{now_str}_", suffix=".sql"
    )
    temp_path = temp_file.name
    temp_file.close()

    cmd = [
        "pg_dump",
        "-h", db_host,
        "-p", db_port,
        "-U", db_user,
        "-F", "p",
        "--clean",
        "--if-exists",
        "-f", temp_path,
        db_name,
    ]

    try:
        subprocess.run(cmd, env=env, check=True)
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al generar backup con pg_dump: {str(e)}",
        )

    background_tasks.add_task(lambda: os.remove(temp_path) if os.path.exists(temp_path) else None)

    return FileResponse(
        path=temp_path,
        filename=f"backup_hospital_{now_str}.sql",
        media_type="application/sql",
    )