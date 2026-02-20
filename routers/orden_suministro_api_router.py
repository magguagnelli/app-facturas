# routers/orden_suministro_api_router.py
from __future__ import annotations
from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse
from core.auth import require_login
from core.audit import audit, build_log

from services.orden_suministro_service import (
    get_os, create_os, update_os, list_proveedores_activos
)

router = APIRouter(prefix="/api")

def must_be_os_user(request: Request):
    user = require_login(request)
    if not user:
        return None
    if user.rol not in {"CAPTURISTA", "ADMIN"}:
        return None
    return user

@router.get("/proveedores")
def api_proveedores(request: Request, q: str | None = Query(default=None)):
    user = must_be_os_user(request)
    if not user:
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)

    rows = list_proveedores_activos(q)
    audit(user.correo, "API", "Listado proveedores (OS)", build_log(request, extra=f"q={q or ''} count={len(rows)}"))
    return {"data": rows}

@router.get("/ordenes-suministro/{orden_id}")
def api_get_os(request: Request, orden_id: int):
    user = must_be_os_user(request)
    if not user:
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)

    row = get_os(orden_id)
    if not row:
        return JSONResponse({"detail": "Not found"}, status_code=404)

    audit(user.correo, "VIEW_OS_FORM", "Visualización OS", build_log(request, extra=f"id={orden_id}"))
    return {"data": row}

@router.post("/ordenes-suministro")
async def api_create_os(request: Request):
    user = must_be_os_user(request)
    if not user:
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)

    payload = await request.json()
    new_id = create_os(payload)

    audit(user.correo, "CREATE_OS", "Creación orden de suministro", build_log(request, extra=f"id={new_id} partida={payload.get('partida')}"))
    return {"id": new_id}

@router.put("/ordenes-suministro/{orden_id}")
async def api_update_os(request: Request, orden_id: int):
    user = must_be_os_user(request)
    if not user:
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)

    payload = await request.json()
    update_os(orden_id, payload)

    audit(user.correo, "UPDATE_OS", "Actualización orden de suministro", build_log(request, extra=f"id={orden_id}"))
    return {"ok": True}
