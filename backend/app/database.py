from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from psycopg2.extensions import register_adapter, AsIs
import uuid

# Adaptador de UUID para psycopg2
def add_uuid_adapter():
    def adapt_uuid(uuid_obj):
        return AsIs(f"'{uuid_obj}'")
    register_adapter(uuid.UUID, adapt_uuid)

add_uuid_adapter()

# Importa la configuración desde config.py
from .config import settings

# URL de la base de datos (se obtiene de las variables de entorno)
DATABASE_URL = settings.DATABASE_URL

# Crear el motor de SQLAlchemy
# pool_pre_ping=True ayuda a manejar conexiones inactivas
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Crear una SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para los modelos declarativos de SQLAlchemy
Base = declarative_base()

# Función de utilidad para obtener una sesión de base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()