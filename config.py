import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_title: str = "Sistema de Incidencias - Soporte Técnico"
    app_description: str = "API para la gestión de reportes mediante códigos QR"
    app_version: str = "3.0.0"
    hospital_name: str = "Hospital Dr. Miguel Pérez Carreño"
    base_url: str = os.getenv("BASE_URL", "http://127.0.0.1:8000")

    jwt_secret: str = os.getenv("JWT_SECRET", "cambiar-esta-clave-en-produccion-hospital-2026")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))

    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    notify_email: str = os.getenv("NOTIFY_EMAIL", "")
    webhook_url: str = os.getenv("WEBHOOK_URL", "")

    admin_email: str = os.getenv("ADMIN_EMAIL", "admin@hospital.com")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "admin123")
    admin_nombre: str = os.getenv("ADMIN_NOMBRE", "Administrador")


settings = Settings()
