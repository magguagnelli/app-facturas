from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from core.auth import require_login
from core.audit import audit, build_log

templates = Jinja2Templates(directory="templates")
router = APIRouter()

def ctx(request: Request, user, **extra):
    return {
        "request": request,
        "user_role": user.rol,
        "user_name": user.nombre,
        "user_email": user.correo,
        **extra,
    }

