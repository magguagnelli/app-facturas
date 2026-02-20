# routers/area_router.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from core.auth import require_admin
from core.audit import audit, build_log

templates = Jinja2Templates(directory="templates")
router = APIRouter()

@router.get("/areas", response_class=HTMLResponse)
def page_areas(request: Request):
    admin = require_admin(request)
    if not admin:
        return RedirectResponse(url="/home", status_code=302)

    audit(
        correo=admin.correo,
        accion="VIEW_AREAS",
        descripcion="Acceso a Lista de Áreas",
        log_accion=build_log(request),
    )

    return templates.TemplateResponse(
        "areas.html",
        {
            "request": request,
            "user_role": admin.rol,
            "user_name": admin.nombre,
            "user_email": admin.correo,
        },
    )