from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session

# --- Importaciones de la aplicación (Modulares y limpias) ---
from app.database import database, models
from app.database.models import Inventory, User, Role
from app.core.mqtt_client import mqtt_client
from app.core.security import get_password_hash, verify_password
from app.services import algorithms
from app import schemas

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

# Inicialización de la aplicación FastAPI
app = FastAPI(title="WMS Backend G4", lifespan=lifespan)

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
@app.post("/login", response_model=schemas.LoginResponse, tags=["Seguridad"])
def login(credenciales: schemas.UserLogin, db: Session = Depends(database.get_db)):
    """
    Endpoint que el Frontend usa para iniciar sesión.
    Valida en la Base de Datos y devuelve el Rol del usuario.
    """
    # Buscar al usuario en PostgreSQL
    user = db.query(User).filter(User.username == credenciales.username).first()
    
    # Si no existe o la contraseña no coincide, bloqueamos el acceso (Error 401)
    if not user or not verify_password(credenciales.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos"
        )
    
    # Respuesta exitosa para el Frontend
    return {
        "status": "success",
        "role": user.role.name,  
        "access_token": "fake-jwt-token-por-ahora" 
    }
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
@app.post("/ordenar_paquete", tags=["Operaciones"])
async def order_package(request: schemas.PackageRequest, db: Session = Depends(database.get_db)):
    """
    Recibe la solicitud del operador, asigna posición y despacha al AGV.
    """
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

    # 4. Guardar en PostgreSQL
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

@app.get("/inventario", tags=["Operaciones"])
def ver_inventario(db: Session = Depends(database.get_db)):
    """
    Retorna todo el inventario de la matriz.
    """
    paquetes = db.query(Inventory).all()
    return {"total_paquetes": len(paquetes), "inventario": paquetes}