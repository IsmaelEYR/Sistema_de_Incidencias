from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from dependencies import get_db
from config import settings
import schemas
import models
from services import equipos as equipos_service
from services import incidencias as incidencias_service
from auth.dependencies import get_current_user_optional, normalizar_rol, ROLES_PANEL
from models import Usuario, caracas_now

router = APIRouter(tags=["Dashboard"])
templates = Jinja2Templates(directory="templates")


def render_template(template_name: str, context: dict, status_code: int = 200) -> HTMLResponse:
    template = templates.get_template(template_name)
    content = template.render(context)
    return HTMLResponse(content=content, status_code=status_code)


@router.get("/panel")
def panel_redireccion(user: Usuario = Depends(get_current_user_optional)):
    if not user:
        return RedirectResponse("/dashboard", status_code=303)
    if normalizar_rol(user.rol) in ROLES_PANEL:
        return RedirectResponse("/admin/dashboard", status_code=303)
    return RedirectResponse("/dashboard", status_code=303)


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_publico(
    request: Request,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user_optional),
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

    context = {
        "request": request,
        "incidencias": incidencias,
        "stats": stats,
        "hospital_name": settings.hospital_name,
        "user": user,
    }
    return render_template("dashboard_publico.html", context)


@router.get("/reportar/{codigo_qr}", response_class=HTMLResponse)
def formulario_reporte(
    codigo_qr: str,
    request: Request,
    exito: Optional[str] = None,
    ticket_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    equipo = equipos_service.obtener_equipo_por_codigo(db, codigo_qr)

    # Confirmación tras PRG: solo éxito + ticket que pertenece a este equipo.
    ticket_creado = None
    if exito == "1" and ticket_id:
        ticket_creado = (
            db.query(models.Incidencia)
            .filter(models.Incidencia.id == ticket_id, models.Incidencia.equipo_id == equipo.id)
            .first()
        )
    mostrar_exito = exito == "1" and ticket_creado is not None

    # Anti-duplicado en UI (no aplica al mostrar la confirmación de éxito)
    incidencia_activa = None
    if not mostrar_exito:
        estados_activos = ["PENDIENTE", "EN_PROCESO", "Pendiente", "En Proceso"]
        incidencia_activa = (
            db.query(models.Incidencia)
            .filter(
                models.Incidencia.equipo_id == equipo.id,
                models.Incidencia.estado.in_(estados_activos),
            )
            .order_by(models.Incidencia.fecha_reporte.desc())
            .first()
        )

    context = {
        "request": request,
        "equipo": equipo,
        "mostrar_exito": mostrar_exito,
        "ticket_id": ticket_id,
        "incidencia_activa": incidencia_activa,
        "hospital_name": settings.hospital_name,
    }
    return render_template("reportar.html", context)


@router.post("/reportar/{codigo_qr}")
def enviar_reporte(
    codigo_qr: str,
    descripcion: str = Form(..., min_length=5, max_length=1000),
    reportado_por_nombre: str = Form(..., min_length=3, max_length=150),
    reportado_por_cedula: str = Form(..., min_length=6, max_length=50),
    db: Session = Depends(get_db),
):
    from exceptions import DuplicateError

    datos = schemas.IncidenciaReporteQR(
        descripcion=descripcion,
        reportado_por_nombre=reportado_por_nombre,
        reportado_por_cedula=reportado_por_cedula,
    )
    try:
        nueva_incidencia = incidencias_service.crear_incidencia_por_qr(db, codigo_qr, datos)
        return RedirectResponse(
            url=f"/reportar/{codigo_qr}?exito=1&ticket_id={nueva_incidencia.id}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except DuplicateError:
        return RedirectResponse(
            url=f"/reportar/{codigo_qr}?error=duplicado",
            status_code=status.HTTP_303_SEE_OTHER,
        )