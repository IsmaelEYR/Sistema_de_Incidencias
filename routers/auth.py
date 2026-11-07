from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from dependencies import get_db
from config import settings
from models import Usuario
from auth.jwt_utils import verificar_password, crear_token
from auth.dependencies import normalizar_rol

router = APIRouter(tags=["Auth"])
templates = Jinja2Templates(directory="templates")

def render_template(template_name: str, context: dict, status_code: int = 200) -> HTMLResponse:
    """Renderiza una plantilla y devuelve HTMLResponse (evita el bug de TemplateResponse)."""
    template = templates.get_template(template_name)
    content = template.render(context)
    return HTMLResponse(content=content, status_code=status_code)

@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    context = {"request": request, "hospital_name": settings.hospital_name}
    return render_template("login.html", context)

@router.post("/login")
def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    login = (username or "").strip().lower()
    user = (
        db.query(Usuario)
        .filter(or_(func.lower(Usuario.nombre) == login, func.lower(Usuario.email) == login))
        .first()
    )
    if not user or not user.activo or not verificar_password(password, user.password_hash or ""):
        # Authentication failed – render login with error, no cookie.
        context = {
            "request": request,
            "hospital_name": settings.hospital_name,
            "error": "Credenciales inválidas",
        }
        return render_template("login.html", context, status_code=status.HTTP_401_UNAUTHORIZED)

    # Credentials valid – create JWT payload with normalized (canonical) role.
    payload = {
        "sub": str(user.id),
        "rol": normalizar_rol(user.rol),
    }
    token = crear_token(payload)

    # /panel decide el destino según el rol (admin/supervisor → panel admin).
    response = RedirectResponse("/panel", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=settings.jwt_expire_minutes * 60,
    )
    return response



@router.get("/logout")
def logout():
    response = RedirectResponse("/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key="access_token", path="/", httponly=True)
    return response