# routers/facturas_listado_api_router.py
"""
API Router para listado de facturas con paginación y exportación
"""
from __future__ import annotations

from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import FileResponse
import os

from core.auth import require_login
from core.audit import audit, build_log
from services.facturas_listado_service import (
    list_facturas_paginado,
    exportar_facturas_excel,
    get_filtros_opciones,
)
from starlette.background import BackgroundTask

router = APIRouter(prefix="/api/facturas-listado", tags=["facturas_listado_api"])


def _require_user(request: Request):
    """Requiere usuario autenticado con rol válido"""
    user = require_login(request)
    if not user or user.rol not in ("ADMIN", "CAPTURISTA", "RESP_FICALIZADOR"):
        raise HTTPException(status_code=401, detail="No autorizado")
    return user


@router.get("/lista")
def api_lista_facturas(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
    proveedor: str = Query(None),
    uuid: str = Query(None),
    area: int = Query(None),
    estatus_os: int = Query(None),
    fecha_inicio: str = Query(None),
    fecha_fin: str = Query(None),
):
    """
    Endpoint para listar facturas con paginación y filtros.
    
    Query params:
    - page: número de página (default: 1)
    - per_page: registros por página (default: 50, max: 500)
    - proveedor: filtro por RFC o razón social del proveedor
    - uuid: filtro por UUID (búsqueda parcial)
    - area: filtro por ID de área
    - estatus_os: filtro por ID de estado de orden
    - fecha_inicio: filtro fecha >= (formato: YYYY-MM-DD)
    - fecha_fin: filtro fecha <= (formato: YYYY-MM-DD)
    """
    user = _require_user(request)
    
    result = list_facturas_paginado(
        page=page,
        per_page=per_page,
        proveedor=proveedor,
        uuid=uuid,
        area=area,
        estatus_os=estatus_os,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
    )
    
    # Auditoría
    audit(
        user.correo,
        "LISTADO_FACTURAS",
        f"Consulta listado de facturas (página {page})",
        build_log(request)
    )
    
    return result


@router.get("/filtros")
def api_filtros_opciones(request: Request):
    """
    Endpoint para obtener las opciones disponibles para filtros.
    Retorna áreas y estados de orden.
    """
    _require_user(request)
    return get_filtros_opciones()


@router.get("/exportar-excel")
def api_exportar_excel(
    request: Request,
    proveedor: str = Query(None),
    uuid: str = Query(None),
    area: int = Query(None),
    estatus_os: int = Query(None),
    fecha_inicio: str = Query(None),
    fecha_fin: str = Query(None),
):
    """
    Endpoint para exportar facturas a Excel.
    Aplica los mismos filtros que el listado.
    """
    user = _require_user(request)
    
    filepath = exportar_facturas_excel(
        proveedor=proveedor,
        uuid=uuid,
        area=area,
        estatus_os=estatus_os,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
    )
    
    if not filepath:
        raise HTTPException(status_code=404, detail="No hay datos para exportar")
    
    # Auditoría
    audit(
        user.correo,
        "EXPORTAR_FACTURAS_EXCEL",
        f"Exportación de facturas a Excel",
        build_log(request)
    )
    
    # Generar nombre del archivo
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"facturas_{timestamp}.xlsx"
    
    def cleanup():
        """Eliminar archivo temporal después de enviarlo"""
        try:
            if os.path.exists(filepath):
                os.unlink(filepath)
        except Exception:
            pass
    
    return FileResponse(
        filepath,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        filename=filename,
        background=BackgroundTask(cleanup)
    )
