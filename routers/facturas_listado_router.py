# routers/facturas_listado_router.py
"""
Router de páginas para el listado de facturas
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from core.auth import require_login
from core.audit import audit, build_log

router = APIRouter(tags=["facturas_listado_pages"])

templates = Jinja2Templates(directory="templates")


@router.get("/facturas/listado", response_class=HTMLResponse)
def facturas_listado_page(request: Request):
    """Página de listado de facturas con filtros y paginación"""
    user = require_login(request)
    if not user:
        return RedirectResponse(url="/", status_code=302)
    
    if user.rol not in {"CAPTURISTA", "ADMIN", "RESP_FICALIZADOR"}:
        return RedirectResponse(url="/home", status_code=302)
    
    audit(
        correo=user.correo,
        accion="VIEW_FACTURAS_LISTADO",
        descripcion="Acceso a listado completo de facturas",
        log_accion=build_log(request),
    )
    
    return templates.TemplateResponse(
        "facturas_listado.html",
        {
            "request": request,
            "user_role": user.rol,
            "user_name": user.nombre,
            "user_email": user.correo,
        }
    )
