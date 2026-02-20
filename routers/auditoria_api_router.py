# routers/auditoria_api_router.py
from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse

from core.auth import require_admin
from core.audit import audit, build_log
from services.auditoria_service import search_auditoria

router = APIRouter(prefix="/api")

@router.get("/auditoria")
def api_auditoria(
    request: Request,
    correo: str | None = Query(default=None),
    accion: str | None = Query(default=None),
    q: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    limit: int = Query(default=100),
    offset: int = Query(default=0),
):
    admin = require_admin(request)
    if not admin:
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)

    result = search_auditoria(
        correo=correo,
        accion=accion,
        q=q,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )

    audit(
        correo=admin.correo,
        accion="API_AUDIT",
        descripcion="Consulta auditoría (API)",
        log_accion=build_log(request, extra=f"count={len(result['rows'])} offset={result['offset']}"),
    )

    return result