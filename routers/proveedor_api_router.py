# routers/proveedor_api_router.py
from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse
import psycopg

from core.auth import require_admin
from core.audit import audit, build_log

from services.proveedor_service import list_proveedores, get_proveedor, create_proveedor, update_proveedor

router = APIRouter(prefix="/api")

@router.get("/proveedores")
def api_list_prov(request: Request, q: str | None = Query(default=None)):
    admin = require_admin(request)
    if not admin:
        return JSONResponse({"detail":"Unauthorized"}, status_code=401)

    rows = list_proveedores(q)
    return {"data": rows}

@router.get("/proveedores/{prov_id}")
def api_get_prov(request: Request, prov_id: int):
    admin = require_admin(request)
    if not admin:
        return JSONResponse({"detail":"Unauthorized"}, status_code=401)

    row = get_proveedor(prov_id)
    if not row:
        return JSONResponse({"detail":"Not found"}, status_code=404)

    return {"data": row}

@router.post("/proveedores")
async def api_create_prov(request: Request):
    admin = require_admin(request)
    if not admin:
        return JSONResponse({"detail":"Unauthorized"}, status_code=401)

    payload = await request.json()

    try:
        new_id = create_proveedor(payload)
    except psycopg.errors.UniqueViolation:
        return JSONResponse({"detail":"RFC ya existe (debe ser único)."}, status_code=409)
    except ValueError as e:
        return JSONResponse({"detail": str(e)}, status_code=400)

    audit(admin.correo, "CREATE_PROV", "Alta de proveedor", build_log(request, extra=f"id={new_id} rfc={payload.get('rfc','')}"))
    return {"id": new_id}

@router.put("/proveedores/{prov_id}")
async def api_update_prov(request: Request, prov_id: int):
    admin = require_admin(request)
    if not admin:
        return JSONResponse({"detail":"Unauthorized"}, status_code=401)

    payload = await request.json()

    try:
        update_proveedor(prov_id, payload)
    except psycopg.errors.UniqueViolation:
        return JSONResponse({"detail":"RFC ya existe (debe ser único)."}, status_code=409)
    except ValueError as e:
        return JSONResponse({"detail": str(e)}, status_code=400)

    audit(admin.correo, "UPDATE_PROV", "Edición de proveedor", build_log(request, extra=f"id={prov_id} rfc={payload.get('rfc','')}"))
    return {"ok": True}
