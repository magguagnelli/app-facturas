import secrets
import string
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def generate_temp_password(length: int = 12) -> str:
    # Evita caracteres que rompen URLs/regex y confunden
    alphabet = string.ascii_letters + string.digits + "!@#$%&*_-"
    return "".join(secrets.choice(alphabet) for _ in range(length))
