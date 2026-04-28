from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# El motor apuntará a un archivo local de SQLite por esta noche.
# Mañana, si quieres, cambias esta línea por la de PostgreSQL.
SQLALCHEMY_DATABASE_URL = "sqlite:///./wms_local.db"

# connect_args={"check_same_thread": False} es vital para que FastAPI y SQLite se entiendan
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Esta es la "Inyección de Dependencias" que usará FastAPI en cada Endpoint
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()