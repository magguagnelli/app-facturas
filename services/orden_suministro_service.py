# services/orden_suministro_service.py
from __future__ import annotations
from typing import Optional
from psycopg.rows import dict_row
from core.db import get_conn

OS_FIELDS = [
    "partida", "proveedor", "fecha_orden", "folio_oficio", "fecha_factura", "folio_interno",
    "cuenta_bancaria", "banco", "mes_servicio",
    "monto_siniva", "iva", "monto_c_iva", "isr", "ieps", "descuento", "otras_contribuciones",
    "retenciones", "penalizacion", "deductiva",
    "importe_pago", "importe_p_compromiso", "no_compromiso",
    "observaciones", "estatus", "fecha_pago"
]

def get_os(orden_id: int) -> Optional[dict]:
    sql = """
      SELECT o.*,
             pv.rfc AS proveedor_rfc, pv.razon_social AS proveedor_razon_social,
             eo.estado_resumen, eo.estatus_general
      FROM cat_facturas.orden_suministro o
      JOIN cat_facturas.proveedor pv ON pv.id = o.proveedor
      JOIN cat_facturas.estado_orden eo ON eo.id = o.estatus
      WHERE o.id = %s
    """
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (orden_id,))
            return cur.fetchone()

def list_proveedores_activos(search: str | None = None) -> list[dict]:
    if search:
        like = f"%{search.strip().lower()}%"
        sql = """
          SELECT id, rfc, razon_social, nombre_comercial, estatus
          FROM cat_facturas.proveedor
          WHERE estatus = 'ACTIVO'
            AND (lower(rfc) LIKE %s OR lower(razon_social) LIKE %s OR lower(nombre_comercial) LIKE %s)
          ORDER BY razon_social
          LIMIT 100;
        """
        params = (like, like, like)
    else:
        sql = """
          SELECT id, rfc, razon_social, nombre_comercial, estatus
          FROM cat_facturas.proveedor
          WHERE estatus = 'ACTIVO'
          ORDER BY razon_social
          LIMIT 100;
        """
        params = ()
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            return cur.fetchall()

def create_os(data: dict) -> int:
    # defaults para campos not null numéricos (si el front manda vacíos)
    defaults = {
        "isr": 0, "ieps": 0, "descuento": 0, "otras_contribuciones": 0,
        "retenciones": 0, "penalizacion": 0, "deductiva": 0,
        "observaciones": None,
        "estatus": 1,
        "fecha_pago": None,
    }
    payload = {**defaults, **{k: data.get(k) for k in OS_FIELDS}}

    sql = """
      INSERT INTO cat_facturas.orden_suministro (
        partida, proveedor, fecha_orden, folio_oficio, fecha_factura, folio_interno,
        cuenta_bancaria, banco, mes_servicio,
        monto_siniva, iva, monto_c_iva, isr, ieps, descuento, otras_contribuciones,
        retenciones, penalizacion, deductiva,
        importe_pago, importe_p_compromiso, no_compromiso,
        observaciones, estatus, fecha_pago
      ) VALUES (
        %(partida)s, %(proveedor)s, %(fecha_orden)s, %(folio_oficio)s, %(fecha_factura)s, %(folio_interno)s,
        %(cuenta_bancaria)s, %(banco)s, %(mes_servicio)s,
        %(monto_siniva)s, %(iva)s, %(monto_c_iva)s, %(isr)s, %(ieps)s, %(descuento)s, %(otras_contribuciones)s,
        %(retenciones)s, %(penalizacion)s, %(deductiva)s,
        %(importe_pago)s, %(importe_p_compromiso)s, %(no_compromiso)s,
        %(observaciones)s, %(estatus)s, %(fecha_pago)s
      )
      RETURNING id;
    """
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, payload)
            row = cur.fetchone()
            conn.commit()
            return int(row["id"])

def update_os(orden_id: int, data: dict) -> None:
    # actualiza todo excepto 'archivo' (se maneja por endpoint de CFDI upload)
    payload = {k: data.get(k) for k in OS_FIELDS}
    payload["id"] = orden_id

    sql = """
      UPDATE cat_facturas.orden_suministro SET
        partida=%(partida)s,
        proveedor=%(proveedor)s,
        fecha_orden=%(fecha_orden)s,
        folio_oficio=%(folio_oficio)s,
        fecha_factura=%(fecha_factura)s,
        folio_interno=%(folio_interno)s,
        cuenta_bancaria=%(cuenta_bancaria)s,
        banco=%(banco)s,
        mes_servicio=%(mes_servicio)s,
        monto_siniva=%(monto_siniva)s,
        iva=%(iva)s,
        monto_c_iva=%(monto_c_iva)s,
        isr=%(isr)s,
        ieps=%(ieps)s,
        descuento=%(descuento)s,
        otras_contribuciones=%(otras_contribuciones)s,
        retenciones=%(retenciones)s,
        penalizacion=%(penalizacion)s,
        deductiva=%(deductiva)s,
        importe_pago=%(importe_pago)s,
        importe_p_compromiso=%(importe_p_compromiso)s,
        no_compromiso=%(no_compromiso)s,
        observaciones=%(observaciones)s,
        estatus=%(estatus)s,
        fecha_pago=%(fecha_pago)s
      WHERE id=%(id)s;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, payload)
            conn.commit()
