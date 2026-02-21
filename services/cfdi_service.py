# services/cfdi_service.py
from __future__ import annotations

import os
from datetime import datetime, date
from typing import Any, Dict, List, Optional

from core.db import get_conn
from core.cfdi_core import build_validation_checklist, extract_cfdi_fields
from core.audit import audit, build_log

DEBUG = os.getenv("DEBUG", "0") == "1"

def _get_id(row):
    if row is None:
        return None
    if isinstance(row, (tuple, list)):
        return row[0] if len(row) else None
    if isinstance(row, dict): 
        return row.get("id") or row.get("ID")
    try:
        return row["id"]
    except Exception:
        return None

def _to_date(s: str) -> Optional[date]:
    s = (s or "").strip()
    if not s:
        return None
    return datetime.fromisoformat(s).date()

def list_facturas(q: str = "") -> List[Dict[str, Any]]:
    """
    Lista CFDI (facturas) con proveedor y OS/partida/contrato para flags.
    """
    q = (q or "").strip()
    with get_conn() as conn:
        with conn.cursor() as cur:
            sql = """
            SELECT
              c.id as cfdi_id,
              c.uuid,
              c.rfc_emisor,
              c.fecha_emision,
              c.fecha_recepcion,
              c.estatus as cfdi_estatus,
              c.orden_suministro as os_id,

              os.partida as partida_id,
              p.contrato as contrato_id,

              pr.id as proveedor_id,
              pr.rfc as proveedor_rfc,
              pr.razon_social as proveedor_razon,

              p.partida_especifica as partida,
              ct.num_contrato as contrato,
              ct.tipo_de_contrato,
              eo.estatus_reporte,

              CASE WHEN os.partida IS NOT NULL THEN TRUE ELSE FALSE END as os_tiene_partida,
              CASE WHEN p.id IS NOT NULL THEN TRUE ELSE FALSE END as partida_existe,
              CASE WHEN ct.id IS NOT NULL THEN TRUE ELSE FALSE END as contrato_existe
            FROM cat_facturas.cfdi c
            LEFT JOIN cat_facturas.orden_suministro os ON os.id = c.orden_suministro
            LEFT JOIN cat_facturas.estado_orden eo ON eo.id = os.estatus
            LEFT JOIN cat_facturas.partida p ON p.id = os.partida
            LEFT JOIN cat_facturas.contrato ct ON ct.id = p.contrato
            LEFT JOIN cat_facturas.proveedor pr ON pr.id = os.proveedor
            WHERE 1=1
            """
            params = []
            if q:
                sql += " AND (c.uuid ILIKE %s OR c.rfc_emisor ILIKE %s OR pr.rfc ILIKE %s OR pr.razon_social ILIKE %s)"
                like = f"%{q}%"
                params += [like, like, like, like]
            sql += " ORDER BY c.id DESC LIMIT 500"

            cur.execute(sql, params)
            cols = [d[0] for d in cur.description]
            out = []
            for row in cur.fetchall():
                if isinstance(row, dict):
                    out.append(row)
                else:
                    out.append(dict(zip(cols, row)))
            return out

def get_factura_audit(cfdi_id: str) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    a.id,
                    CASE
                        WHEN a.accion LIKE 'ALTA%%' THEN 'ALTA'
                        WHEN a.accion LIKE 'EDICION%%' THEN 'MODIFICACIÓN'
                        ELSE 'SIN CLASIFICAR'
                    END AS "ACCION",
                    UPPER(a.descripcion) AS "DESCRIPCION",
                    TO_CHAR(a.fecha_accion,'DD-MM-YYYY HH24:MI:SS') AS "FECHA DE ACCION",
                    UPPER(u.nombre) AS "RESPONSABLE",
                    UPPER(a.correo) AS "CORREO",
                    r.*
                FROM cat_facturas.auditoria a
                LEFT JOIN LATERAL jsonb_to_record(
                    cat_facturas.get_registro(a.seccion,a.id_sec)
                ) AS r(uuid text) ON true
                LEFT JOIN cat_facturas.usuario u 
                    ON u.correo = a.correo
                WHERE 
                    (a.accion LIKE 'ALTA%%' OR a.accion LIKE 'EDIC%%')
                    AND a.seccion = 'cat_facturas.cfdi' 
                    AND a.id_sec = %s
                ORDER BY a.id ASC;
            """, (cfdi_id,))
            rows = cur.fetchall()

            if not rows:
                return []

            cols = [d[0] for d in cur.description]

            return [dict(row) for row in rows]

def get_factura_detalle(cfdi_id: int) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            SELECT
              c.*,
              os.*,
              p.*,
              ct.*,
              os.estatus status_os,
              pr.rfc as proveedor_rfc,
              pr.razon_social as proveedor_razon,
              u.nombre capturista
            FROM cat_facturas.cfdi c
            LEFT JOIN cat_facturas.orden_suministro os ON os.id = c.orden_suministro
            LEFT JOIN cat_facturas.partida p ON p.id = os.partida
            LEFT JOIN cat_facturas.contrato ct ON ct.id = p.contrato
            LEFT JOIN cat_facturas.proveedor pr ON pr.id = os.proveedor
            left join cat_facturas.usuario u on c.resp_captura = u.correo
            WHERE c.id=%s
            """, (cfdi_id,))
            row = cur.fetchone()
            #print(row)
            if not row: 
                return None
            # Nota: aquí devolvemos “crudo” por ser modal informativo
            if isinstance(row, dict):
                return row
            cols = [d[0] for d in cur.description]
            return dict(zip(cols, row))
  
def list_contratos() -> List[Dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, num_contrato, rfc_pp, ejercicio, mes, tipo_de_contrato FROM cat_facturas.contrato WHERE estatus='ACTIVO' ORDER BY id DESC")
            cols = [d[0] for d in cur.description]
            items = [dict(r) for r in cur.fetchall()]
            #print(items)
            return items 

def list_partidas_by_contrato(contrato_id: int) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, partida_especifica, des_pe, monto_total
                FROM cat_facturas.partida
                WHERE contrato=%s
                ORDER BY id DESC
            """, (contrato_id,))  
            #cols = [d[0] for d in cur.description]
            return [dict(r) for r in cur.fetchall()]

def list_est_siaf() -> List[dict[str,Any]]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("select id, nombre as estado_siaf from cat_facturas.estatus_siaf order by 1")
            items = [dict(r) for r in cur.fetchall()]
            return items

def list_fiscalizador() -> List[dict[str,Any]]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("select id, nombre as fiscalizador from cat_facturas.usuario where tipo = 'FISCALIZACION' order by 1")
            items = [dict(r) for r in cur.fetchall()]
            return items

def validate_cfdi(xml_bytes: bytes) -> Dict[str, Any]:
    checklist = build_validation_checklist(xml_bytes)

    extracted = checklist.get("extracted") or {}
    rfc_emisor = extracted.get("rfc_emisor")
    uuid = extracted.get("uuid")

    # 1) RFC existe en proveedor
    rfc_ok = False
    rfc_msg = "RFC emisor no detectado en XML."
    if rfc_emisor:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM cat_facturas.proveedor WHERE rfc=%s LIMIT 1", (rfc_emisor,))
                hit = cur.fetchone()
                rfc_ok = bool(_get_id(hit))
                rfc_msg = "RFC existe en catálogo de proveedores." if rfc_ok else "RFC NO existe en catálogo de proveedores."
    checklist["rfc_ok"] = rfc_ok
    checklist["messages"].append(rfc_msg)

    # 2) UUID no duplicado
    uuid_ok = False
    uuid_msg = "UUID no detectado en XML."
    if uuid:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM cat_facturas.cfdi WHERE uuid=%s LIMIT 1", (uuid,))
                hit = cur.fetchone()
                if hit:
                    uuid_ok = False
                    uuid_msg = f"UUID ya registrado (cfdi.id={_get_id(hit)})."
                else:
                    uuid_ok = True
                    uuid_msg = "UUID no existe en BD (OK)."

    checklist["uuid_ok"] = uuid_ok
    checklist["messages"].append(uuid_msg)

    checklist["ok"] = bool(
        checklist.get("xml_ok") and checklist.get("xsd_ok") and checklist.get("timbre_ok")
        and rfc_ok and uuid_ok
    )
    return checklist


def create_factura_and_os(
    actor_email: str,
    log: str,
     #Contrato
    partida_id: int,
    mes_servicio: str,
    estatus_os: int, #estatus Administrativo
    
    #CFDI
    xml_bytes: bytes,
    proveedor_id: int,
    fecha_recepcion: str,#Fecha recepcion CFDI y fecha de captura
    monto_partida: float,    
    ieps: float,
    descuento: float,
    otras_contribuciones: float,
    retenciones: float,
    penalizacion: float,
    deductiva: float,
    importe_pago: float,
    fecha_captura: Optional[str] = None,
    observaciones_cfdi: Optional[str] = None,

    #Complementaria
    orden_suministro: Optional[str] = None,
    fecha_solicitud: Optional[str] = None,
    folio_oficio: Optional[str] = None,
    folio_interno: Optional[str] = None,
    cuenta_bancaria: Optional[str] = None,
    banco: Optional[str] = None,   
    importe_p_compromiso: Optional[float] = 0,
    no_compromiso: Optional[int] = 0,
    fecha_pago: Optional[str] = None,
    validacion: Optional[str] = None,
    cincomillar: Optional[str] = None,
    riva: Optional[str] = None,
    risr: Optional[str] = None,
    solicitud: Optional[str] = None,
    observaciones_os: Optional[str] =None,
    archivo: Optional[str] = None,
    
    #facturacion
    fecha_fiscalizacion: Optional[str] = None,
    fiscalizador: Optional[str] = None,
    responsable_fis: Optional[str] = None,
    fecha_carga_sicop: Optional[str] = None,
    responsable_carga_sicop: Optional[str] = None,
    numero_solicitud: Optional[str] = None,
    clc: Optional[str] = None,
    estatus_siaf: Optional[str] = None,

    #devolucion
    oficio_dev: Optional[str] = None,
    fecha_dev: Optional[str] = None,
    motivo_dev: Optional[str] = None,

    #final
    ret_imp_nom: Optional[float] = 0,
    fecha_pr: Optional[str] = None,
    inmueble: Optional[str] = None,
    periodo: Optional[str] = None,
    recargos: Optional[str] = None,
    corte_presupuesto: Optional[str] = None,
    fecha_turno: Optional[str] = None,
    obs_pr: Optional[str] = None,
    numero_solicitud25: Optional[str] = None,
    clc25: Optional[str] = None,
    numero_solicitud26: Optional[str] = None,
    clc26: Optional[str] = None,
    numero_solicitud27: Optional[str] = None,
    clc27: Optional[str] = None,
    capturista: Optional[str] = None,
    
) -> Dict[str, Any]:
    # Extrae del XML ORIGINAL (incluye timbre)
    extracted = extract_cfdi_fields(xml_bytes)
    #Datos de factura
    uuid = extracted.get("uuid")
    rfc_emisor = extracted.get("rfc_emisor")
    fecha_emision = extracted.get("fecha_emision")#fecha_factura
    monto_siniva = extracted.get("subtotal")
    iva = extracted.get("iva")
    monto_c_iva = extracted.get("con_iva")
    isr = extracted.get("isr")
    
    if not uuid:
        return {"ok": False, "message": "No se pudo extraer UUID."}
    if not rfc_emisor:
        return {"ok": False, "message": "No se pudo extraer RFC."}
    if not fecha_emision:
        return {"ok": False, "message": "No se pudo extraer Fecha del CFDI."}
    if not proveedor_id:
        return {"ok": False, "message": "El Proveedor no està registrado."}
    if partida_id == 0:
        return {"ok": False, "message": "No ha seleccionado una partida"}
    
    xml_str = xml_bytes.decode("utf-8", errors="replace")  
    with get_conn() as conn:
        with conn.cursor() as cur:
            # crea OS
            cur.execute("""
                INSERT INTO cat_facturas.orden_suministro
                (partida, proveedor, fecha_orden, folio_oficio, fecha_factura, folio_interno, 
                cuenta_bancaria, banco, mes_servicio, monto_siniva, iva, monto_c_iva, isr, ieps, 
                descuento, otras_contribuciones, retenciones, penalizacion, deductiva, 
                importe_pago, importe_p_compromiso, no_compromiso,  
                estatus, fecha_pago, archivo, 
                orden_suministro, validacion, _5millar, riva, risr, solicitud, observaciones, 
                fecha_fiscalizacion, fiscalizador, fecha_carga_sicop, responsable_carga_sicop,
                numero_solicitud_pago, clc, estatus_siaff, responsable_fis, 
                oficio_dev, fecha_dev, motivo_dev,
                clc25,clc26,clc27,numero_solicitud_pago25,numero_solicitud_pago26,numero_solicitud_pago27,
                re_imp_nomina,fecha_pr,inmueble,periodo,recargos,observacion_pr,
                corte_presupuesto,fecha_turno)
                VALUES
                (%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,
                %s,%s,%s,
                %s,%s,%s,
                %s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,
                %s,%s,%s,%s,
                %s,%s,%s,
                %s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s,
                %s,%s)
                RETURNING id
            """, (
                partida_id, proveedor_id, _to_date(fecha_solicitud), folio_oficio, fecha_emision, folio_interno,
                cuenta_bancaria, banco, mes_servicio, monto_siniva, iva, monto_c_iva, isr, (ieps or None),
                (descuento or None), (otras_contribuciones or None), (retenciones or None), (penalizacion or None), (deductiva or None),
                importe_pago, (importe_p_compromiso or None), (no_compromiso or None),
                estatus_os, None if fecha_pago is None else _to_date(fecha_pago), (archivo or None),
                (orden_suministro or None), (validacion or None), (cincomillar or None), (riva or None), (risr or None), (solicitud or None), (observaciones_os or None),
                _to_date(fecha_fiscalizacion), (fiscalizador or None), _to_date(fecha_carga_sicop), (responsable_carga_sicop or None),
                (numero_solicitud or None), (clc or None),(estatus_siaf or None),(responsable_fis or None),
                (oficio_dev or None),_to_date(fecha_dev), (motivo_dev or None),
                (clc25 or None),(clc26 or None),(clc27 or None),(numero_solicitud25 or None),(numero_solicitud26 or None),(numero_solicitud27 or None),
                (ret_imp_nom or None),_to_date(fecha_pr),(inmueble or None),(periodo or None),(recargos or None),(obs_pr or None),
                (corte_presupuesto or None),_to_date(fecha_turno)
            ))
            os_id = cur.fetchone()
            os_id = _get_id(os_id)
            
            audit(
                correo=actor_email,
                accion="ALTA Información Complementaria",
                descripcion=f"Alta Información Complementaria id={os_id}",
                log_accion=log,
                seccion="cat_facturas.orden_suministro",
                id_sec= str(os_id)
            )
            
            # crea CFDI
            cur.execute("""
                INSERT INTO cat_facturas.cfdi(
                orden_suministro, uuid, rfc_emisor, fecha_recepcion, fecha_emision, 
                onservaciones, xml_factura, monto_total,  estatus, fecha_captura, monto_partida,resp_captura)
                VALUES(
                    %s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,
                    %s)
                RETURNING id
            """, (
                os_id, uuid, rfc_emisor, _to_date(fecha_recepcion), fecha_emision, 
                (observaciones_cfdi or None), xml_str, importe_pago,"ACTIVO", _to_date(fecha_captura), monto_partida,actor_email
                )
            )
            cfdi_id = _get_id(cur.fetchone())
            ret = {"ok":True,"message":"UUID: "+uuid+" os_id: "+str(os_id)+" cfdi_id: "+str(cfdi_id)}
            audit(
                correo=actor_email,
                accion="ALTA CFDI",
                descripcion=f"Alta de CFDI id={cfdi_id}",
                log_accion=log,
                seccion="cat_facturas.cfdi",
                id_sec= str(cfdi_id)
            )
        conn.commit()
    return ret
    

def update_factura_and_os(
    *,
    cfdi_id: int,
    estatus_os: int, #estatus Administrativo
    monto_partida: float,    
    ieps: Optional[float] = 0,
    descuento: Optional[float] = 0,
    otras_contribuciones: Optional[float] = 0,
    retenciones: Optional[float] = 0,
    penalizacion: Optional[float] = 0,
    deductiva: Optional[float] = 0,
    importe_pago: Optional[float] = 0,
    observaciones_cfdi: Optional[str] = None,

    #Complementaria
    orden_suministro: Optional[str] = None,
    fecha_solicitud: Optional[str] = None,
    folio_oficio: Optional[str] = None,
    folio_interno: Optional[str] = None,
    cuenta_bancaria: Optional[str] = None,
    banco: Optional[str] = None,   
    importe_p_compromiso: Optional[float] = 0,
    no_compromiso: Optional[int] = 0,
    fecha_pago: Optional[str] = None,
    validacion: Optional[str] = None,
    cincomillar: Optional[str] = None,
    risr: Optional[str] = None,
    riva: Optional[str] = None,
    solicitud: Optional[str] = None,
    observaciones_os: Optional[str] = None,
    archivo: Optional[str] = None,
    
    #facturacion
    fecha_fiscalizacion: Optional[str] = None,
    fiscalizador: Optional[str] = None,
    responsable_fis: Optional[str] = None,
    fecha_carga_sicop: Optional[str] = None,
    responsable_carga_sicop: Optional[str] = None,
    numero_solicitud: Optional[str] = None,
    clc: Optional[str] = None,
    estatus_siaf: Optional[str] = None,

    #devolucion
    oficio_dev: Optional[str] = None,
    fecha_dev: Optional[str] = None,
    motivo_dev: Optional[str] = None,

    #ultimos
    ret_imp_nom: Optional[float] = 0,
    fecha_pr: Optional[str] = None,
    inmueble: Optional[str] = None,
    periodo: Optional[str] = None,
    recargos: Optional[str] = None,
    corte_presupuesto: Optional[str] = None,
    fecha_turno: Optional[str] = None,
    obs_pr: Optional[str] = None,
    numero_solicitud25: Optional[str] = None,
    clc25: Optional[str] = None,
    numero_solicitud26: Optional[str] = None,
    clc26: Optional[str] = None,
    numero_solicitud27: Optional[str] = None,
    clc27: Optional[str] = None,
) -> Dict[str, Any]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            # obtener OS padre
            cur.execute("SELECT orden_suministro FROM cat_facturas.cfdi WHERE id=%s", (cfdi_id,))
            row = cur.fetchone()
            if not row:
                return {"ok": False, "message": "CFDI no encontrado."}
            os_id = row[0] if not isinstance(row, dict) else row.get("orden_suministro")

            # actualiza CFDI (uuid/rfc/fechas/obs/estatus)
            cur.execute("""
                UPDATE cat_facturas.cfdi
                SET onservaciones=%s
                WHERE id=%s
            """, (
                (observaciones_os or None), cfdi_id
            ))
            sql = """
                UPDATE cat_facturas.orden_suministro
                SET
                    estatus = %s,
                    monto_c_iva = %s,
                    ieps = %s,
                    descuento = %s,
                    otras_contribuciones = %s,
                    retenciones = %s,
                    penalizacion = %s,
                    deductiva = %s,
                    importe_pago = %s,
                    observaciones = %s,

                    orden_suministro = %s,
                    fecha_orden = %s,
                    folio_oficio = %s,
                    folio_interno = %s,
                    cuenta_bancaria = %s,
                    banco = %s,
                    importe_p_compromiso = %s,
                    no_compromiso = %s,
                    fecha_pago = %s,
                    validacion = %s,
                    _5millar = %s,
                    risr = %s,
                    riva = %s,
                    solicitud = %s,
                    archivo = %s,

                    fecha_fiscalizacion = %s,
                    fiscalizador = %s,
                    responsable_fis = %s,
                    fecha_carga_sicop = %s,
                    responsable_carga_sicop = %s,
                    numero_solicitud_pago = %s,
                    clc = %s,
                    estatus_siaff = %s,

                    oficio_dev = %s,
                    fecha_dev = %s,
                    motivo_dev = %s,

                    re_imp_nomina = %s,
                    fecha_pr = %s,
                    inmueble = %s,
                    periodo = %s,
                    recargos = %s,
                    corte_presupuesto = %s,
                    fecha_turno = %s,
                    observacion_pr = %s,

                    numero_solicitud_pago25 = %s,
                    clc25 = %s,
                    numero_solicitud_pago26 = %s,
                    clc26 = %s,
                    numero_solicitud_pago27 = %s,
                    clc27 = %s

                WHERE id = %s
                """
            cur.execute(sql, (
                estatus_os,
                monto_partida,
                ieps,
                descuento,
                otras_contribuciones,
                retenciones,
                penalizacion,
                deductiva,
                importe_pago,
                observaciones_cfdi or observaciones_os,

                orden_suministro,
                fecha_solicitud,
                folio_oficio,
                folio_interno,
                cuenta_bancaria,
                banco,
                importe_p_compromiso,
                no_compromiso,
                fecha_pago,
                validacion,
                cincomillar,
                risr,
                riva,
                solicitud,
                archivo,

                fecha_fiscalizacion,
                fiscalizador,
                responsable_fis,
                fecha_carga_sicop,
                responsable_carga_sicop,
                numero_solicitud,
                clc,
                estatus_siaf,

                oficio_dev,
                fecha_dev,
                motivo_dev,

                ret_imp_nom,
                fecha_pr,
                inmueble,
                periodo,
                recargos,
                corte_presupuesto,
                fecha_turno,
                obs_pr,

                numero_solicitud25,
                clc25,
                numero_solicitud26,
                clc26,
                numero_solicitud27,
                clc27,                
                os_id
            )
        )
        conn.commit()
    ret = {"ok":True,"message":"Registro actualizado correctamente"}
    return ret



def set_cfdi_estatus(cfdi_id: int, estatus: str) -> Dict[str, Any]:
    if estatus not in ("ACTIVO", "CANCELADO", "INACTIVO"):
        return {"ok": False, "message": "Estatus inválido."}
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE cat_facturas.cfdi SET estatus=%s WHERE id=%s", (estatus, cfdi_id))
            conn.commit()
    return {"ok": True}
