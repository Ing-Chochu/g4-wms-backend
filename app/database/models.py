from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
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
    
    role = relationship("Role", back_populates="users")

# ==========================================
# 2. RAMA DE OPERACIÓN (Núcleo Logístico)
# ==========================================
class Inventory(Base):
    __tablename__ = "inventory"
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, index=True)
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