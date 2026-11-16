from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

import os

import config  # noqa: F401  (carga .env antes de leer DATABASE_URL)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# URL de conexión a PostgreSQL (.env / variable de entorno DATABASE_URL).
# Fallback a 127.0.0.1 para evitar bloqueos por resolución IPv6 de 'localhost' en macOS.
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:1234567@127.0.0.1:5432/sistema_de_incidencias",
)

# connect_timeout corto: si la BD no responde, falla con error explícito en vez de congelarse
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 5},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass