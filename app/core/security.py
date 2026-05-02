import bcrypt

def get_password_hash(password: str) -> str:
    """Convierte la contraseña en un hash ilegible usando bcrypt nativo"""
    # bcrypt requiere que los textos se conviertan a bytes
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(pwd_bytes, salt)
    
    # Lo devolvemos como string para guardarlo en PostgreSQL
    return hashed_bytes.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si la contraseña del Front coincide con el hash de la DB"""
    plain_password_bytes = plain_password.encode('utf-8')
    hashed_password_bytes = hashed_password.encode('utf-8')
    
    return bcrypt.checkpw(plain_password_bytes, hashed_password_bytes)