from database import SessionLocal
from models import Usuario, Equipo, Incidencia, HistorialIncidencia
from auth.jwt_utils import hash_password

def reset():
    db = SessionLocal()
    try:
        # Borrar en orden para evitar problemas de Foreign Keys
        db.query(HistorialIncidencia).delete()
        db.query(Incidencia).delete()
        db.query(Equipo).delete()
        db.query(Usuario).delete()
        
        # Crear usuario Administrador (credenciales definidas en config.py / variables de entorno)
        from config import settings
        admin = Usuario(
            nombre="admin",
            email=settings.admin_email,
            rol="Administrador",
            activo=True,
            password_hash=hash_password(settings.admin_password)
        )
        db.add(admin)
        db.commit()
        print("Base de datos reseteada con éxito. Usuario 'admin' creado con la clave definida en ADMIN_PASSWORD.")
    except Exception as e:
        db.rollback()
        print(f"Error reseteando DB: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    reset()
