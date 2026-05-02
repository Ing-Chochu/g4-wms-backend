from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Estructura: postgresql+psycopg://usuario:contraseña@servidor:puerto/base_de_datos
# ⚠️ CAMBIA 'tu_contraseña' por la tuya.
SQLALCHEMY_DATABASE_URL = "postgresql+psycopg://postgres:unipam2114@localhost:5432/wms_db"

# Para PostgreSQL ya no usamos el connect_args de SQLite. Es mucho más limpio.
engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()