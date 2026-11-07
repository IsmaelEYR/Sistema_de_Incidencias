"""
Dependencias de autenticación y autorización.

Toda comparación de roles pasa por `normalizar_rol()`, que convierte cualquier
variante ("ADMIN", "Administrador", "admin ", "Técnico", "tecnico"...) a una
clave canónica en minúsculas y sin acentos. Así la BD, el JWT, los routers y
las plantillas Jinja2 hablan siempre el mismo idioma.
"""
import unicodedata
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from dependencies import get_db
from models import Usuario
from auth.jwt_utils import decodificar_token

# ─── Roles canónicos ───────────────────────────────────────────────
ROL_ADMIN = "administrador"
ROL_SUPERVISOR = "supervisor"
ROL_ASISTENTE = "asistente administrativo"
ROL_TECNICO = "tecnico"

# Alias aceptados → rol canónico (claves ya en minúsculas y sin acentos)
ROLE_ALIASES = {
    "admin": ROL_ADMIN,
    "administrador": ROL_ADMIN,
    "administradora": ROL_ADMIN,
    "administrator": ROL_ADMIN,
    "supervisor": ROL_SUPERVISOR,
    "supervisora": ROL_SUPERVISOR,
    "asistente": ROL_ASISTENTE,
    "asistente administrativo": ROL_ASISTENTE,
    "asistente administrativa": ROL_ASISTENTE,
    "tecnico": ROL_TECNICO,
    "tecnica": ROL_TECNICO,
}

# Grupos de uso frecuente
ROLES_GESTION_EQUIPOS = (ROL_ADMIN, ROL_SUPERVISOR)
ROLES_PANEL = (ROL_ADMIN, ROL_SUPERVISOR, ROL_ASISTENTE)


def normalizar_rol(rol: Optional[str]) -> str:
    """Devuelve el rol canónico (minúsculas, sin acentos, alias resueltos)."""
    if not rol:
        return ""
    limpio = unicodedata.normalize("NFKD", str(rol)).encode("ascii", "ignore").decode("ascii")
    limpio = " ".join(limpio.lower().split())
    return ROLE_ALIASES.get(limpio, limpio)


def es_admin(rol: Optional[str]) -> bool:
    return normalizar_rol(rol) == ROL_ADMIN


def _resolver_usuario(request: Request, db: Session) -> Optional[Usuario]:
    """Lee la cookie, valida el JWT y carga el usuario activo. Nunca lanza."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = decodificar_token(token)
    if not payload:
        return None
    user_id = payload.get("sub")
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return None

    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if user is None or not user.activo:
        return None

    # La BD es la fuente de verdad: si el rol cambió después de emitir el
    # token, se respeta el rol actual. El rol del JWT sólo es respaldo.
    rol = normalizar_rol(user.rol) or normalizar_rol(payload.get("rol"))
    request.state.usuario = user
    request.state.role = rol
    request.state.es_admin = rol == ROL_ADMIN
    return user


def get_current_user(request: Request, db: Session = Depends(get_db)) -> Usuario:
    """Usuario autenticado obligatorio. Lanza 401 si no hay sesión válida."""
    user = _resolver_usuario(request, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado o sesión expirada",
        )
    return user


def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> Optional[Usuario]:
    """Usuario autenticado opcional: devuelve None si el token falta, expiró o es inválido."""
    return _resolver_usuario(request, db)


def require_role(*roles: str):
    """
    Exige que el usuario tenga alguno de los roles indicados.
    - Comparación case-insensitive y tolerante a acentos/alias.
    - El Administrador tiene acceso a todo.
    """
    aceptados = {normalizar_rol(r) for r in roles}

    def dependency(request: Request, user: Usuario = Depends(get_current_user)) -> Usuario:
        rol_usuario = getattr(request.state, "role", None) or normalizar_rol(user.rol)
        if rol_usuario == ROL_ADMIN or rol_usuario in aceptados:
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para acceder a este recurso",
        )

    return dependency


# Dependencias listas para usar en los routers
require_admin = require_role(ROL_ADMIN)
require_gestion_equipos = require_role(*ROLES_GESTION_EQUIPOS)
require_panel = require_role(*ROLES_PANEL)