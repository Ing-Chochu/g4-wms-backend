import bcrypt
import asyncio
from fastapi.concurrency import run_in_threadpool

async def get_password_hash(password: str) -> str:
    """Convierte la contraseña en un hash ilegible usando bcrypt nativo"""
    # Ejecutamos bcrypt en un hilo del pool para no bloquear el event loop de FastAPI
    def hash_task():
        pwd_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')
    
    return await run_in_threadpool(hash_task)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si la contraseña del Front coincide con el hash de la DB"""
    plain_password_bytes = plain_password.encode('utf-8')
    hashed_password_bytes = hashed_password.encode('utf-8')
    
    return bcrypt.checkpw(plain_password_bytes, hashed_password_bytes)