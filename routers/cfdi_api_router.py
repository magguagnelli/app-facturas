# routers/cfdi_api_router.py
from __future__ import annotations

from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from core.db import get_conn

from datetime import date
from typing import Optional

from core.auth import require_login
from core.audit import audit, build_log

from services.cfdi_service import (
    list_facturas,
    get_factura_detalle,
    list_contratos,
    list_partidas_by_contrato,
    validate_cfdi,
    create_factura_and_os,
    update_factura_and_os,
    #delete_factura,
    set_cfdi_estatus,
)

router = APIRouter(prefix="/api/cfdi", tags=["cfdi_api"])

def _require_user(request: Request):
    user = require_login(request)
    if not user or user.rol not in ("ADMIN", "CAPTURISTA"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user

@router.get("")
def api_list(request: Request, q: str = ""):
    _require_user(request)
    return {"items": list_facturas(q)}

@router.get("/{cfdi_id}/detalle")
def api_detalle(request: Request, cfdi_id: int):
    _require_user(request)
    row = get_factura_detalle(cfdi_id)
    if not row:
        raise HTTPException(status_code=404, detail="Not Found")
    return {"item": row}

@router.get("/catalogos/contratos")
def api_contratos(request: Request):
    _require_user(request)
    return {"items": list_contratos()}

@router.get("/catalogos/contratos/{contrato_id}/partidas")
def api_partidas(request: Request, contrato_id: int):
    _require_user(request)
    return {"items": list_partidas_by_contrato(contrato_id)}

@router.post("/validar")
async def api_validar(request: Request, file: UploadFile = File(...)):
    user = _require_user(request)
    xml_bytes = await file.read()
    res = validate_cfdi(xml_bytes)

    audit(user.correo, "VALIDAR_CFDI_XML", "Validación XML CFDI (registro facturas)", build_log(request))
    return res

@router.post("/alta")
async def api_alta(
    request: Request,
    #Contrato
    partida_id: int = Form(...),
    mes_servicio: str = Form(...),
    fecha_orden: str = Form(""), #fecha Captura OS
    estatus_os: int = Form(...), #estatus Administrativo
    
    #CFDI
    file: UploadFile = File(...),
    proveedor_id: int = Form(...),
    fecha_recepcion: str = Form(...),#Fecha recepcion CFDI
    monto_partida: float = Form(0),    
    ieps: float = Form(0),
    descuento: float = Form(0),
    otras_contribuciones: float = Form(0),
    retenciones: float = Form(0),
    penalizacion: float = Form(0),
    deductiva: float = Form(0),
    importe_pago: float = Form(0),
    fecha_captura: Optional[str] = Form(None),
    observaciones_cfdi: Optional[str] = Form(None),

    #Complementaria
    orden_suministro: Optional[str] = Form(None),
    fecha_solicitud: Optional[str] = Form(None),
    folio_oficio: Optional[str] = Form(None),
    folio_interno: Optional[str] = Form(None),
    cuenta_bancaria: Optional[str] = Form(None),
    banco: Optional[str] = Form(None),   
    importe_p_compromiso: Optional[float] = Form(0),
    no_compromiso: Optional[int] = Form(0),
    fecha_pago: Optional[str] = Form(None),
    validacion: Optional[str] = Form(None),
    cincomillar: Optional[str] = Form(None),
    risr: Optional[str] = Form(None),
    riva: Optional[str] = Form(None),
    solicitud: Optional[str] = Form(None),
    observaciones_os: Optional[str] = Form(None),
    archivo: Optional[str] = Form(None),
    
    #facturacion
    fecha_fiscalizacion: Optional[str] = Form(None),
    fiscalizador: Optional[str] = Form(None),
    responsable_fis: Optional[str] = Form(None),
    fecha_carga_sicop: Optional[str] = Form(None),
    responsable_carga_sicop: Optional[str] = Form(None),
    numero_solicitud: Optional[str] = Form(None),
    clc: Optional[str] = Form(None),
    estatus_siaf: Optional[str] = Form(None),

    #devolucion
    oficio_dev: Optional[str] = Form(None),
    fecha_dev: Optional[str] = Form(None),
    motivo_dev: Optional[str] = Form(None),
):    
    
    user = _require_user(request)
    xml_bytes = await file.read()

    # Primero valida
    v = validate_cfdi(xml_bytes)
    if not v.get("ok"):
        audit(user.correo, "ALTA_RECHAZADA_CFDI", "Alta CFDI rechazada por validación", build_log(request))
        return JSONResponse({"ok": False, "message": "CFDI no válido.", "validation": v}, status_code=400)
    
    # Si no viene fecha_captura desde el frontend, asignar hoy
    if not fecha_captura:
        fecha_captura = date.today().isoformat()

    res = create_factura_and_os(
        actor_email=user.correo,
        log=build_log(request),
        #contrato
        partida_id=partida_id,
        mes_servicio=mes_servicio,
        estatus_os=estatus_os, #estatus Administrativo

        #CFDI
        xml_bytes=xml_bytes,
        proveedor_id=proveedor_id,
        monto_partida=monto_partida,    
        ieps= ieps,
        descuento=descuento,
        otras_contribuciones=otras_contribuciones,
        retenciones=retenciones,
        penalizacion=penalizacion,
        deductiva=deductiva,
        importe_pago=importe_pago,
        fecha_recepcion=fecha_recepcion,
        observaciones_cfdi=observaciones_cfdi,
        
        #os
        orden_suministro=orden_suministro,
        fecha_solicitud=fecha_solicitud,
        folio_oficio=folio_oficio,
        folio_interno=folio_interno,
        cuenta_bancaria=cuenta_bancaria,
        banco=banco,   
        importe_p_compromiso=importe_p_compromiso,
        no_compromiso=no_compromiso,
        fecha_pago=fecha_pago,
        validacion=validacion,
        cincomillar=cincomillar,
        riva=riva,
        risr=risr,
        solicitud=solicitud,
        observaciones_os=observaciones_os,
        archivo=archivo,

        #facturacion
        fecha_fiscalizacion=fecha_fiscalizacion,
        fiscalizador=fiscalizador,
        responsable_fis=responsable_fis,
        fecha_carga_sicop=fecha_carga_sicop,
        responsable_carga_sicop=responsable_carga_sicop,
        numero_solicitud=numero_solicitud,
        clc=clc,
        estatus_siaf=estatus_siaf,

        #devolucion
        oficio_dev=oficio_dev,
        fecha_dev=fecha_dev,
        motivo_dev=motivo_dev,
    )
    #return JSONResponse({"ok": False, "message": res, "validation": v}, status_code=200)
    
    return res

@router.put("/{cfdi_id}")
async def api_update(
    request: Request,
    cfdi_id: int,
    cfdi_estatus: str = Form("ACTIVO"),

    # OS editables
    partida_id: int = Form(...),
    estatus_os: int = Form(...),
    fecha_pago: str = Form(""),
    # Nuevos campos CFDI
    fecha_emision: str = Form(""),
    fecha_recepcion: str = Form(""),
    tipo_de_contrato: str = Form(""),
    observaciones_os: str = Form(""),
):
    user = _require_user(request)
    res = update_factura_and_os(
        cfdi_id=cfdi_id,
        cfdi_estatus=cfdi_estatus,
        partida_id=partida_id if partida_id else None,
        estatus_os=estatus_os if estatus_os else None,
        fecha_pago=fecha_pago,
        fecha_emision=fecha_emision or None,
        fecha_recepcion=fecha_recepcion or None,
        tipo_de_contrato=tipo_de_contrato or None,
        observaciones_os=observaciones_os,
    )
    audit(user.correo, "EDICION_CFDI", f"Edición CFDI id={cfdi_id}", build_log(request))
    return res



@router.put("/{cfdi_id}/estatus")
def api_set_status(request: Request, cfdi_id: int, estatus: str = Form(...)):
    user = _require_user(request)
    res = set_cfdi_estatus(cfdi_id, estatus)
    audit(user.correo, "CFDI_ESTATUS", f"Cambio estatus CFDI id={cfdi_id} -> {estatus}", build_log(request))
    return res

@router.get("/catalogos/proveedor-by-rfc")
def api_proveedor_by_rfc(request: Request, rfc: str):
    user = _require_user(request)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, rfc, razon_social
                FROM cat_facturas.proveedor
                WHERE rfc=%s
                LIMIT 1
            """, (rfc,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Proveedor no encontrado")
            if isinstance(row, dict):
                return {"item": row}
            cols = [d[0] for d in cur.description]
            return {"item": dict(zip(cols, row))}

@router.get("/catalogos/estado-orden")
def api_estado_orden(request: Request):
    _require_user(request)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, estatus_general, estatus_reporte
                FROM cat_facturas.estado_orden
                ORDER BY id
            """)
            #print(cur.description)
            cols = [d[0] for d in cur.description]
            items = [dict(r) for r in cur.fetchall()]
            #print(items)
            return {"items": items}
