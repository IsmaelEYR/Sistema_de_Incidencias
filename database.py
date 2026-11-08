from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# URL de conexión a PostgreSQL (configurable mediante variable de entorno DATABASE_URL)
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:1234567@localhost:5432/sistema_de_incidencias",
)

# IMPORTANTE: Eliminamos connect_args ya que no es necesario para PostgreSQL
engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass