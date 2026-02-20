# routers/area_api_router.py
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from core.auth import require_login
from core.audit import audit, build_log
from services.area_service import (
    list_areas, insert_area, update_area, delete_area, area_name_exists
)

router = APIRouter(prefix="/api/areas")

def require_admin(request: Request):
    user = require_login(request)
    if not user or user.rol != "ADMIN":
        return None
    return user

# GET /api/areas
@router.get("")
def api_list_areas(request: Request):
    user = require_admin(request)
    if not user:
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)

    data = list_areas()
    audit(user.correo, "VIEW_AREA", "Listado de áreas", build_log(request, extra=f"count={len(data)}"))
    return {"data": data}

# POST /api/areas
@router.post("")
async def api_create_area(request: Request):
    user = require_admin(request)
    if not user:
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)

    payload = await request.json()
    nombre = (payload.get("nombre_area") or "").strip()
    desc = payload.get("desc_area")

    if not nombre:
        return JSONResponse({"detail": "nombre_area es obligatorio"}, status_code=400)

    if area_name_exists(nombre):
        return JSONResponse({"detail": "Ya existe un área con ese nombre."}, status_code=409)

    new_id = insert_area(nombre, (desc or "").strip() or None)
    audit(user.correo, "CREATE_AREA", f"Alta área {nombre}", build_log(request, extra=f"id={new_id}"))
    return {"ok": True, "id": new_id}

# PUT /api/areas/{area_id}
@router.put("/{area_id}")
async def api_update_area(request: Request, area_id: int):
    user = require_admin(request)
    if not user:
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)

    payload = await request.json()
    nombre = (payload.get("nombre_area") or "").strip()
    desc = payload.get("desc_area")

    if not nombre:
        return JSONResponse({"detail": "nombre_area es obligatorio"}, status_code=400)

    if area_name_exists(nombre, exclude_id=area_id):
        return JSONResponse({"detail": "Ya existe un área con ese nombre."}, status_code=409)

    update_area(area_id, nombre, (desc or "").strip() or None)
    audit(user.correo, "UPDATE_AREA", f"Edición área {area_id}", build_log(request))
    return {"ok": True}

# DELETE /api/areas/{area_id}
@router.delete("/{area_id}")
def api_delete_area(request: Request, area_id: int):
    user = require_admin(request)
    if not user:
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)

    delete_area(area_id)
    audit(user.correo, "DELETE_AREA", f"Baja área {area_id}", build_log(request))
    return {"ok": True}
