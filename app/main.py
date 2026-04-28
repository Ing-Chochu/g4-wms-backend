from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.database import models, database
from app.core.mqtt_client import mqtt_client # El archivo que creamos antes
from contextlib import asynccontextmanager
from app.database.models import Inventory

# Crear las tablas automáticamente al iniciar (Magia de SQLAlchemy)
models.Base.metadata.create_all(bind=database.engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Lógica de arranque
    print("🚀 Arrancando WMS Backend...")
    mqtt_client.start()
    yield
    # Lógica de apagado
    print("🛑 Apagando WMS Backend...")
    mqtt_client.stop()

app = FastAPI(title="WMS Backend G4", lifespan=lifespan)

# Endpoint de prueba para verificar que la DB y API funcionan
@app.get("/health")
def health_check(db: Session = Depends(database.get_db)):
    return {
        "status": "online",
        "database": "connected",
        "mqtt_status": "active"
    }

# ... (Tu código actual de imports, lifespan y /health se queda arriba) ...

from pydantic import BaseModel
from app.database.models import Inventory
from app.services import algorithms

# Modelo de Pydantic para validar los datos que envía el Frontend
class PackageRequest(BaseModel):
    sku: str
    peso: float

@app.post("/ordenar_paquete", tags=["Operaciones"])
async def order_package(request: PackageRequest, db: Session = Depends(database.get_db)):
    # 1. Aplicar Algoritmo LIFO/FIFO para encontrar espacio
    target_pos = algorithms.find_first_empty_slot_fifo()
    if not target_pos:
        return {"error": "Almacén lleno"}

    # 2. Calcular Ruta A*
    agv_start = {"x": 0, "y": 0}
    route = algorithms.calculate_a_star_route(agv_start, target_pos)

    # 3. Enviar Comando al Robot Físico vía MQTT
    command = {
        "action": "almacenar",
        "sku": request.sku,
        "ruta": route
    }
    mqtt_client.publish_command("agv1", command)

    # 4. GUARDAR EN LA BASE DE DATOS
    nuevo_paquete = Inventory(
        sku=request.sku,
        pos_x=target_pos["x"],
        pos_y=target_pos["y"],
        status="in_transit"
    )
    db.add(nuevo_paquete)
    db.commit()
    db.refresh(nuevo_paquete)

    return {
        "status": "Orden guardada en Base de Datos",
        "id_paquete": nuevo_paquete.id,
        "asignacion_fifo": target_pos,
        "ruta_asignada": route
    }

# NUEVO ENDPOINT PARA VER EL INVENTARIO
@app.get("/inventario", tags=["Operaciones"])
def ver_inventario(db: Session = Depends(database.get_db)):
    paquetes = db.query(Inventory).all()
    return {"total_paquetes": len(paquetes), "inventario": paquetes}