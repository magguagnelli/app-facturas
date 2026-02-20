# routers/entidad_api_router.py
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import psycopg

from core.auth import require_admin
from core.audit import audit, build_log
from services.entidad_service import (
    list_entidades, get_entidad, create_entidad, update_entidad
)

router = APIRouter(prefix="/api")

@router.get("/entidades")
def api_list_entidades(request: Request):
    admin = require_admin(request)
    if not admin:
        return JSONResponse({"detail":"Unauthorized"}, status_code=401)

    return {"data": list_entidades()}

@router.get("/entidades/{eid}")
def api_get_entidad(request: Request, eid: str):
    admin = require_admin(request)
    if not admin:
        return JSONResponse({"detail":"Unauthorized"}, status_code=401)

    row = get_entidad(eid)
    if not row:
        return JSONResponse({"detail":"Not found"}, status_code=404)

    return {"data": row}

@router.post("/entidades")
async def api_create_entidad(request: Request):
    admin = require_admin(request)
    if not admin:
        return JSONResponse({"detail":"Unauthorized"}, status_code=401)

    payload = await request.json()

    try:
        create_entidad(payload)
    except psycopg.errors.UniqueViolation:
        return JSONResponse({"detail":"La entidad ya existe."}, status_code=409)
    except ValueError as e:
        return JSONResponse({"detail": str(e)}, status_code=400)

    audit(
        admin.correo,
        "CREATE_ENTIDAD",
        "Alta de entidad",
        build_log(request, extra=f"id={payload.get('id')}"),
    )
    return {"ok": True}

@router.put("/entidades/{eid}")
async def api_update_entidad(request: Request, eid: str):
    admin = require_admin(request)
    if not admin:
        return JSONResponse({"detail":"Unauthorized"}, status_code=401)

    payload = await request.json()

    try:
        update_entidad(eid, payload)
    except ValueError as e:
        return JSONResponse({"detail": str(e)}, status_code=400)

    audit(
        admin.correo,
        "UPDATE_ENTIDAD",
        "Cambio de entidad",
        build_log(request, extra=f"id={eid}"),
    )
    return {"ok": True}
