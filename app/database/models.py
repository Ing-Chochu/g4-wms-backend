from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func, text
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from .database import Base

# ==========================================
# 1. RAMA DE CIBERSEGURIDAD (RBAC)
# ==========================================
class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True) # Ej: admin, operador
    users = relationship("User", back_populates="role")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    role_id = Column(Integer, ForeignKey("roles.id")) # Relación con tabla Roles
    session_token = Column(String, nullable=True)
    
    role = relationship("Role", back_populates="users")

# ==========================================
# 2. RAMA DE OPERACIÓN (Núcleo Logístico)
# ==========================================
class Inventory(Base):
    __tablename__ = "inventory"
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, index=True)
    category = Column(String, nullable=True) # A, B o C
    pos_x = Column(Integer)
    pos_y = Column(Integer)
    status = Column(String, default="stored") 
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Vehicle(Base):
    __tablename__ = "vehicles"
    id = Column(String, primary_key=True, index=True) # Ej: agv1, agv2
    battery_level = Column(Float, default=100.0)
    status = Column(String, default="idle") # idle, moving, charging, error
    last_connection = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    pos_x = Column(Integer, nullable=True, default=0)
    pos_y = Column(Integer, nullable=True, default=0)
    modelo = Column(String, nullable=True)
    capacidad_kg = Column(Float, nullable=True)
    velocidad_max = Column(Float, nullable=True)
    autonomia_min = Column(Integer, nullable=True)
    ubicacion_inicial = Column(String, nullable=True)
    descripcion = Column(String, nullable=True)

class TelemetryLog(Base):
    __tablename__ = "telemetry_logs"
    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(String, ForeignKey("vehicles.id"))
    battery_level = Column(Float)
    status = Column(String)
    pos_x = Column(Integer, default=0)
    pos_y = Column(Integer, default=0)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class WorkOrder(Base):
    __tablename__ = "work_orders"
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String)
    status = Column(String, default="pending") # pending, assigned, completed
    assigned_agv = Column(String, ForeignKey("vehicles.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# ==========================================
# 3. RAMA DE AUDITORÍA (Trazabilidad)
# ==========================================
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True) # ¿Quién lo hizo?
    action = Column(String) # Ej: "LOGIN", "ORDEN_CREADA"
    details = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

def purge_old_data(db_session):
    """Elimina datos antiguos para optimizar el performance de PostgreSQL"""
    # Purga de telemetría > 24 horas
    telemetry_limit = datetime.now() - timedelta(hours=24)
    db_session.query(TelemetryLog).filter(TelemetryLog.timestamp < telemetry_limit).delete()
    
    # Purga de logs de auditoría > 30 días
    logs_limit = datetime.now() - timedelta(days=30)
    db_session.query(AuditLog).filter(AuditLog.timestamp < logs_limit).delete()
    
    db_session.commit()