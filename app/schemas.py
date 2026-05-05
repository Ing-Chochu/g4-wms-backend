from pydantic import BaseModel

# ==========================================
# CONTRATOS PARA EL LOGIN
# ==========================================
class UserLogin(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    status: str
    role: str
    access_token: str # Usaremos esto para que el Front mantenga la sesión

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "operador" # Si el Front no manda un rol, por defecto será 'operador' para evitar dar permisos de Admin por error.

# ==========================================
# CONTRATOS PARA OPERACIONES
# ==========================================
class PackageRequest(BaseModel):
    codigo: str
    peso: float # Si el Front manda "quince", Pydantic lo bloquea automáticamente.