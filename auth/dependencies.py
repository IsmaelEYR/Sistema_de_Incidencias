from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from dependencies import get_db          # ← corregido
from models import Usuario
from auth.jwt_utils import decodificar_token

def get_current_user(request: Request, db: Session = Depends(get_db)) -> Usuario:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
    payload = decodificar_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token sin usuario")
    user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")
    request.state.usuario = user
    return user

def get_current_user_optional(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = decodificar_token(token)
    if payload is None:
        return None
    user_id = payload.get("sub")
    if user_id is None:
        return None
    user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
    if user:
        request.state.usuario = user
    return user

def require_role(role: str):
    def dependency(user: Usuario = Depends(get_current_user)) -> Usuario:
        # El Asistente Administrativo hereda los permisos del Supervisor
        allowed_roles = [role]
        if role == "Supervisor":
            allowed_roles.append("Asistente Administrativo")
            
        if user.rol not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos")
        return user
    return dependency