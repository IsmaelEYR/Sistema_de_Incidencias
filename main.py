from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError

import models
import schemas
from config import settings
from database import engine

models.Base.metadata.create_all(bind=engine)
models.migrate_db()

app = FastAPI(
    title=settings.app_title,
    description=settings.app_description,
    version=settings.app_version,
)

app.mount("/static", StaticFiles(directory="static"), name="static")

from routers import auth, admin, dashboard, equipos, incidencias, usuarios

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(dashboard.router)
app.include_router(equipos.router)
app.include_router(incidencias.router)
app.include_router(usuarios.router)

# 5. Manejador global de errores de integridad
@app.exception_handler(IntegrityError)
async def integrity_error_handler(_: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=409,
        content={"detail": "Conflicto de integridad en la base de datos. Verifique duplicados."},
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        # Sin sesión o sesión expirada → al login (y se limpia la cookie inválida)
        if exc.status_code == 401:
            response = RedirectResponse(url="/login", status_code=303)
            response.delete_cookie(key="access_token", path="/")
            return response
        # Con sesión pero sin permisos / recurso inexistente → página de error,
        # NO se expulsa al usuario al login.
        if exc.status_code in (403, 404, 501):
            from fastapi.templating import Jinja2Templates
            from config import settings as _settings
            html = Jinja2Templates(directory="templates").get_template("error.html").render(
                request=request,
                status_code=exc.status_code,
                detail=exc.detail,
                hospital_name=_settings.hospital_name,
            )
            return HTMLResponse(content=html, status_code=exc.status_code)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None)
    )


@app.get("/", response_model=schemas.MensajeResponse)
def ruta_principal():
    return schemas.MensajeResponse(
        mensaje="Servidor del sistema de incidencias operativo.",
        version=settings.app_version,
    )# Trigger reload
