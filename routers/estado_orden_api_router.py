# routers/estado_orden_api_router.py
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from core.auth import require_admin
from core.audit import audit, build_log
from services.estado_orden_service import (
    list_estado_orden, get_estado_orden, create_estado_orden, update_estado_orden
)

router = APIRouter(prefix="/api")

@router.get("/estado-orden")
def api_list(request: Request):
    admin = require_admin(request)
    if not admin:
        return JSONResponse({"detail":"Unauthorized"}, status_code=401)
    return {"data": list_estado_orden()}

@router.get("/estado-orden/{eid}")
def api_get(request: Request, eid: int):
    admin = require_admin(request)
    if not admin:
        return JSONResponse({"detail":"Unauthorized"}, status_code=401)

    row = get_estado_orden(eid)
    if not row:
        return JSONResponse({"detail":"Not found"}, status_code=404)
    return {"data": row}

@router.post("/estado-orden")
async def api_create(request: Request):
    admin = require_admin(request)
    if not admin:
        return JSONResponse({"detail":"Unauthorized"}, status_code=401)

    payload = await request.json()
    try:
        new_id = create_estado_orden(payload)
    except ValueError as e:
        return JSONResponse({"detail": str(e)}, status_code=400)

    audit(admin.correo, "CREATE_ESTORD", "Alta estado_orden", build_log(request, extra=f"id={new_id}"))
    return {"id": new_id}

@router.put("/estado-orden/{eid}")
async def api_update(request: Request, eid: int):
    admin = require_admin(request)
    if not admin:
        return JSONResponse({"detail":"Unauthorized"}, status_code=401)

    payload = await request.json()
    try:
        update_estado_orden(eid, payload)
    except ValueError as e:
        return JSONResponse({"detail": str(e)}, status_code=400)

    audit(admin.correo, "UPDATE_ESTORD", "Edición estado_orden", build_log(request, extra=f"id={eid}"))
    return {"ok": True}
