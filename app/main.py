from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# --- Importaciones de la aplicación (Modulares y limpias) ---
from app.database import database, models
from app.database.models import Inventory, User, Role
from app.core.mqtt_client import mqtt_client
from app.core.security import get_password_hash, verify_password
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
        """Envía datos (como posición de AGVs) a todos los clientes conectados"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

# ==========================================
# EVENTOS DE ARRANQUE Y APAGADO (LIFESPAN)
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Arrancando WMS Backend...")
    
    # 1. Crear las tablas automáticamente en PostgreSQL
    models.Base.metadata.create_all(bind=database.engine)
    
    # 2. Inyección de datos semilla (Crear Admin por defecto)
    db = database.SessionLocal()
    try:
        # Verificar si el rol admin existe
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if not admin_role:
            admin_role = Role(name="admin")
            db.add(admin_role)
            db.commit()
            db.refresh(admin_role)

        # Verificar si el usuario admin existe
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            hashed_pwd = get_password_hash("admin123")
            nuevo_admin = User(username="admin", hashed_password=hashed_pwd, role_id=admin_role.id)
            db.add(nuevo_admin)
            db.commit()
            print("✅ Usuario Administrador creado por defecto (admin / admin123)")
    finally:
        db.close()

    # 3. Arrancar el cliente MQTT para los AGVs
    mqtt_client.start()
    
    yield # Aquí el servidor se queda corriendo y escuchando peticiones
    
    # 4. Lógica de apagado seguro
    print("🛑 Apagando WMS Backend...")
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
            # Mantiene la conexión viva y puede recibir comandos del Front
            data = await websocket.receive_text()
            # Ejemplo: El front pide un reset manual
            await websocket.send_json({"event": "ack", "detail": "Comando recibido"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"Error en WS: {e}")

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
    # Buscamos al usuario
    user = db.query(models.User).filter(models.User.username == request.username).first()
    
    # Validamos (Asegúrate de importar bcrypt o tu validador de contraseñas)
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    
    # El Front espera el rol como string para manejar la UI jerárquica
    user_role = user.role.name if user.role else "operario"
    
    return {
        "access_token": "token-jwt-simulado-123", 
        "role": user_role,
        "username": user.username
    }

@app.get("/usuarios", tags=["Seguridad"])
def listar_usuarios(db: Session = Depends(database.get_db)):
    """Lista todos los usuarios registrados (Solo para vista de Superadmin)"""
    users = db.query(models.User).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "role": u.role.name if u.role else "n/a",
            "hashed_password": u.hashed_password
        } for u in users
    ]

@app.post("/usuarios", tags=["Seguridad"])
def crear_usuario(usuario_nuevo: schemas.UserCreate, db: Session = Depends(database.get_db)):
    """
    Endpoint para registrar un nuevo usuario en el sistema.
    """
    # 1. Verificar si el nombre de usuario ya está ocupado
    usuario_existente = db.query(User).filter(User.username == usuario_nuevo.username).first()
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre de usuario ya está en uso"
        )

    # 2. Verificar si el rol solicitado existe. Si no, lo creamos para no bloquear el sistema.
    rol_db = db.query(Role).filter(Role.name == usuario_nuevo.role).first()
    if not rol_db:
        rol_db = Role(name=usuario_nuevo.role)
        db.add(rol_db)
        db.commit()
        db.refresh(rol_db)

    # 3. Encriptar la contraseña (¡Nunca en texto plano!)
    hashed_pwd = get_password_hash(usuario_nuevo.password)

    # 4. Guardar el nuevo usuario en PostgreSQL
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
    descripcion: str | None = None

@app.post("/productos", tags=["Operaciones"])
def registrar_producto(producto: ProductRegistry, db: Session = Depends(database.get_db)):
    """Registra información del producto antes de su ingreso físico al almacén"""
    nuevo = models.Inventory(sku=producto.sku, status="registrado", pos_x=0, pos_y=0)
    db.add(nuevo)
    db.commit()
    return {"status": "success", "message": f"Producto {producto.sku} cargado al sistema"}

@app.post("/ordenar_paquete", tags=["Operaciones"])
async def order_package(request: schemas.PackageRequest, db: Session = Depends(database.get_db)):
    target_pos = algorithms.find_first_empty_slot_fifo()
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
        "ruta_asignada": route
    }

@app.get("/inventario", tags=["Operaciones"])
async def get_inventario(db: Session = Depends(database.get_db)):
    items = db.query(models.Inventory).all()
    
    inventario_formateado = []
    for item in items:
        # Paridad con useAlmacen.js: se requiere 'sku', 'status' y 'pos_x'
        inventario_formateado.append({
            "id": item.id,
            "sku": item.sku,
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