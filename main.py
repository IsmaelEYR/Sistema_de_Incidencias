from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
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
    if exc.status_code in (401, 403) and "text/html" in accept:
        if request.url.path.startswith("/admin") or request.url.path.startswith("/equipos") or request.url.path.startswith("/dashboard") or request.url.path.startswith("/panel"):
            return RedirectResponse(url="/login", status_code=303)
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
