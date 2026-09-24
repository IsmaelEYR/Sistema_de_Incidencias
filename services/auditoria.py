from sqlalchemy.orm import Session
from models import LogAuditoria

def registrar_accion(db: Session, usuario_id: int | None, accion: str) -> LogAuditoria:
    log = LogAuditoria(usuario_id=usuario_id, accion=accion)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
