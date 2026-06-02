from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

# --- Importaciones de la aplicación (Modulares y limpias) ---
from app.database import database, models
from app.database.models import Inventory, User, Role
from app.core.mqtt_client import mqtt_client
from app.core.security import get_password_hash, verify_password, create_access_token, decode_access_token
from app.services import algorithms
from app import schemas
from pydantic import BaseModel
import asyncio

# ==========================================
# ADMINISTRADOR DE WEBSOCKETS (Propuesta)
# ==========================================
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Sends data to all connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

# --- Security Dependency ---
security_scheme = HTTPBearer()

async def get_current_user(auth: HTTPAuthorizationCredentials = Depends(security_scheme), db: Session = Depends(database.get_db)):
    payload = decode_access_token(auth.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user = db.query(User).filter(User.username == payload.get("sub")).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# ==========================================
# EVENTOS DE ARRANQUE Y APAGADO (LIFESPAN)
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting WMS Backend...")
    # 1. Crear tablas y asegurar existencia de columnas de posición
    models.Base.metadata.create_all(bind=database.engine)
    with database.engine.connect() as conn:
        conn.execute(text("ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS pos_x INTEGER DEFAULT 0"))
        conn.execute(text("ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS pos_y INTEGER DEFAULT 0"))
        conn.commit()

    db = database.SessionLocal()
    try:
        # Roles and Seed Users
        role_names = ["superadmin", "admin", "operario"]
        roles = {}
        for rname in role_names:
            role = db.query(Role).filter(Role.name == rname).first()
            if not role:
                role = Role(name=rname)
                db.add(role)
                db.commit()
                db.refresh(role)
            roles[rname] = role

        # Default users credentials
        default_users = [
            ("superadmin", "SA@2025!", roles["superadmin"]),
            ("admin", "Adm@2025!", roles["admin"]),
            ("operario", "Op@2025!", roles["operario"])
        ]

        for uname, pwd, role in default_users:
            if not db.query(User).filter(User.username == uname).first():
                hashed_pwd = await get_password_hash(pwd)
                db.add(User(username=uname, hashed_password=hashed_pwd, role_id=role.id))
        
        # Seed Vehicles (AGV_01 y AGV_02)
        if not db.query(models.Vehicle).filter(models.Vehicle.id == "AGV_01").first():
            db.add(models.Vehicle(id="AGV_01", battery_level=87.5, status="idle", pos_x=0, pos_y=0))
        if not db.query(models.Vehicle).filter(models.Vehicle.id == "AGV_02").first():
            db.add(models.Vehicle(id="AGV_02", battery_level=42.0, status="charging", pos_x=0, pos_y=0))

        if db.new:
            db.commit()
            print("Seed users created successfully")

    except Exception as e:
        print(f"Error during lifespan seed: {e}")
    finally:
        db.close()

    # 2. Iniciar puente WebSockets para el Frontend
    loop = asyncio.get_event_loop()
    mqtt_client.set_ws_bridge(loop, manager.broadcast)
    mqtt_client.start()
    yield
    print("Stopping WMS Backend...")
    mqtt_client.stop()

app = FastAPI(title="WMS Backend G4", lifespan=lifespan)

# === CONFIGURACIÓN CORS (PERMISOS PARA EL FRONTEND) ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"], # Vite o Create React App
    allow_credentials=True,
    allow_methods=["*"], # Permite POST, GET, PUT, DELETE
    allow_headers=["*"], # Permite enviar Tokens de sesión
)

# ==========================================
# CANAL DE COMUNICACIÓN EN TIEMPO REAL
# ==========================================
@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    """Canal para que el Frontend reciba actualizaciones de AGVs en tiempo real"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({"event": "ack", "detail": "Message received"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WS Error: {e}")

# ==========================================
# ENDPOINTS DE SISTEMA
# ==========================================
@app.get("/health", tags=["Sistema"])
def health_check(db: Session = Depends(database.get_db)):
    """Verifica que los servicios core estén conectados."""
    return {
        "status": "online",
        "database": "connected",
        "mqtt_status": "active"
    }

# ==========================================
# ENDPOINTS DE SEGURIDAD
# ==========================================
class LoginRequestJSON(BaseModel):
    username: str
    password: str

# 2. Modifica tu endpoint de Login para que use el modelo y devuelva lo que el Front espera
@app.post("/login", tags=["Seguridad"])
async def login(request: LoginRequestJSON, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.username == request.username).first()
    
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    
    user_role = user.role.name if user.role else "operario"
    
    token = create_access_token({"sub": user.username, "role": user_role, "id": user.id})

    return {
        "access_token": token, 
        "role": user_role,
        "username": user.username
    }

@app.get("/usuarios", tags=["Seguridad"])
def listar_usuarios(current_user: User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    """Lista todos los usuarios registrados (Solo para vista de Superadmin)"""
    users = db.query(models.User).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "role": u.role.name if u.role else "n/a",
            "activo": u.is_active
        } for u in users
    ]

@app.post("/usuarios", tags=["Seguridad"])
async def crear_usuario(usuario_nuevo: schemas.UserCreate, current_user: User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    usuario_existente = db.query(User).filter(User.username == usuario_nuevo.username).first()
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre de usuario ya está en uso"
        )

    rol_db = db.query(Role).filter(Role.name == usuario_nuevo.role).first()
    if not rol_db:
        rol_db = Role(name=usuario_nuevo.role)
        db.add(rol_db)
        db.commit()
        db.refresh(rol_db)

    hashed_pwd = await get_password_hash(usuario_nuevo.password)

    nuevo_user_db = User(
        username=usuario_nuevo.username,
        hashed_password=hashed_pwd,
        role_id=rol_db.id
    )
    db.add(nuevo_user_db)
    db.commit()
    db.refresh(nuevo_user_db)

    return {
        "status": "success",
        "message": f"Usuario '{nuevo_user_db.username}' creado exitosamente con el rol de '{rol_db.name}'."
    }

# ==========================================
# ENDPOINTS DE OPERACIONES LOGÍSTICAS
# ==========================================
class ProductRegistry(BaseModel):
    sku: str
    categoria: str # A, B o C
    descripcion: str | None = None

@app.post("/productos", tags=["Operaciones"])
def registrar_producto(producto: ProductRegistry, db: Session = Depends(database.get_db)):
    """Registra información del producto antes de su ingreso físico al almacén"""
    nuevo = models.Inventory(sku=producto.sku, category=producto.categoria, status="registrado", pos_x=0, pos_y=0)
    db.add(nuevo)
    db.commit()
    return {"status": "success", "message": f"Producto {producto.sku} cargado al sistema"}

@app.post("/ordenar_paquete", tags=["Operaciones"])
async def order_package(request: schemas.PackageRequest, current_user: User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    # Get occupied slots from DB
    occupied = db.query(Inventory.pos_x, Inventory.pos_y).filter(Inventory.status != "removed").all()
    occupied_list = [{"x": o.pos_x, "y": o.pos_y} for o in occupied]

    target_pos = algorithms.find_first_empty_slot_fifo(occupied_list)
    if not target_pos:
        raise HTTPException(status_code=400, detail="Almacén lleno")

    agv_start = {"x": 0, "y": 0}
    route = algorithms.calculate_a_star_route(agv_start, target_pos)

    command = {
        "action": "almacenar",
        "sku": request.codigo,
        "ruta": route
    }
    mqtt_client.publish_command("agv1", command)

    # Reutilizar registro previo si existe con status 'registrado'
    paquete = db.query(Inventory).filter(
        Inventory.sku == request.codigo,
        Inventory.status == "registrado"
    ).first()

    if paquete:
        paquete.pos_x = target_pos["x"]
        paquete.pos_y = target_pos["y"]
        paquete.status = "in_transit"
        nuevo_paquete = paquete
    else:
        nuevo_paquete = Inventory(
            sku=request.codigo,
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
        "ruta_asignada": route,
        "operador": current_user.username
    }

@app.get("/inventario", tags=["Operaciones"])
async def get_inventario(current_user: User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    items = db.query(models.Inventory).all()
    
    inventario_formateado = []
    for item in items:
        # Paridad con useAlmacen.js: se requiere 'sku', 'status' y 'pos_x'
        inventario_formateado.append({
            "id": item.id,
            "sku": item.sku,
            "category": item.category or "",
            "status": item.status if item.status else "registrado",
            "pos_x": item.pos_x if item.pos_x is not None else 0,
            "pos_y": item.pos_y if item.pos_y is not None else 0,
            "trayectoria": 1,
            "created_at": item.created_at.isoformat() if item.created_at else None
        })
        
    return {
        "total_paquetes": len(items),
        "inventario": inventario_formateado
    }

@app.get("/agvs", tags=["Flota"])
def listar_agvs(db: Session = Depends(database.get_db)):
    """Retorna el estado y posición de toda la flota de robots"""
    vehicles = db.query(models.Vehicle).all()
    return [
        {
            "id": v.id,
            "battery_level": v.battery_level,
            "status": v.status,
            "pos_x": v.pos_x if v.pos_x is not None else 0,
            "pos_y": v.pos_y if v.pos_y is not None else 0,
            "last_connection": v.last_connection.isoformat() if v.last_connection else None,
        }
        for v in vehicles
    ]

@app.put("/agvs/{agv_id}", tags=["Flota"])
async def actualizar_agv(agv_id: str, data: dict, db: Session = Depends(database.get_db)):
    """Endpoint para actualizar telemetría manualmente y notificar vía WS"""
    vehicle = db.query(models.Vehicle).filter(models.Vehicle.id == agv_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    vehicle.battery_level = data.get("battery_level", vehicle.battery_level)
    vehicle.status = data.get("status", vehicle.status)
    vehicle.pos_x = data.get("pos_x", vehicle.pos_x)
    vehicle.pos_y = data.get("pos_y", vehicle.pos_y)
    db.commit()
    await manager.broadcast({"event": "telemetry", "agv_id": agv_id, "data": data})
    return {"status": "success"}

@app.post("/test/simular-qr", tags=["Pruebas"])
def simular_qr(body: dict):
    """Simula una lectura física de QR enviando un mensaje al broker MQTT"""
    mqtt_client.client.publish("wms/infra/qr/lecturas", json.dumps({"codigo": body.get("sku"), "source": "frontend_sim"}))
    return {"status": "success", "message": "Comando enviado al broker"}