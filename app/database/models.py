from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="operator") # operator, admin

class Inventory(Base):
    __tablename__ = "inventory"
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, index=True) # Código del producto
    pos_x = Column(Integer)
    pos_y = Column(Integer)
    status = Column(String, default="stored") # stored, in_transit, picked
    created_at = Column(DateTime(timezone=True), server_default=func.now()) # INDISPENSABLE PARA FIFO

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    action = Column(String)
    details = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())