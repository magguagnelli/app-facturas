import os
from dataclasses import dataclass
from typing import Optional
from itsdangerous import URLSafeSerializer, BadSignature
from fastapi import Request

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
SESSION_COOKIE = "session"
serializer = URLSafeSerializer(SECRET_KEY, salt="session-v1")

@dataclass
class UserSession:
    id: int
    correo: str
    nombre: str
    rol: str
    estatus: str

def get_current_user(request: Request) -> Optional[UserSession]:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    try:
        data = serializer.loads(token)
        return UserSession(
            id=int(data.get("id", 0)),
            correo=str(data.get("correo", "")),
            nombre=str(data.get("nombre", "")),
            rol=str(data.get("rol", "")),
            estatus=str(data.get("estatus", "")),
        )
    except (BadSignature, ValueError, TypeError):
        return None

def require_login(request: Request) -> Optional[UserSession]:
    user = get_current_user(request)
    if not user:
        return None
    if user.estatus != "ACTIVO":
        return None
    return user

def require_admin(request: Request) -> Optional[UserSession]:
    user = require_login(request)
    if not user:
        return None
    if user.rol != "ADMIN":
        return None
    return user
