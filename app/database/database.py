from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# Nota: Se usa 'postgresql+psycopg' para la versión 3 del driver. 
# Si usas la versión clásica, cambia a 'postgresql+psycopg2'.
# En despliegue LAN, asegúrate de que la DB esté corriendo en localhost o usa la IP del servidor DB.
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:unipam2114@localhost:5432/wms_db")

engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# En SQLAlchemy 2.0+, la forma recomendada es heredar de DeclarativeBase
class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()