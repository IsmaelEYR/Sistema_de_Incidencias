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
        
        # Crear usuario Administrador
        admin = Usuario(
            nombre="Admin",
            rol="Supervisor",
            activo=1,
            password_hash=hash_password("admin")
        )
        db.add(admin)
        db.commit()
        print("Base de datos reseteada con éxito. Usuario 'Admin' creado con clave 'admin'.")
    except Exception as e:
        db.rollback()
        print(f"Error reseteando DB: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    reset()
