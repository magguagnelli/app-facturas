# services/cfdi_os_service.py
from __future__ import annotations

from typing import Optional
from psycopg.rows import dict_row
from core.db import get_conn

def os_exists(os_id: int) -> bool:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM cat_facturas.orden_suministro WHERE id=%s;", (os_id,))
            return cur.fetchone() is not None

def list_cfdi_by_os(os_id: int) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
              SELECT id, orden_suministro, uuid, rfc_emisor, fecha_recepcion, fecha_emision,
                     onservaciones
              FROM cat_facturas.cfdi
              WHERE orden_suministro = %s
              ORDER BY id DESC;
            """, (os_id,))
            return cur.fetchall()

def get_cfdi(cfdi_id: int) -> Optional[dict]:
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
              SELECT id, orden_suministro, uuid, rfc_emisor, fecha_recepcion, fecha_emision,
                     onservaciones, xml_factura
              FROM cat_facturas.cfdi
              WHERE id = %s;
            """, (cfdi_id,))
            return cur.fetchone() 

def insert_cfdi(os_id: int, uuid: str, rfc_emisor: str, fecha_recepcion, fecha_emision, observaciones: str | None, xml_factura: str) -> int:
    sql = """
      INSERT INTO cat_facturas.cfdi
        (orden_suministro, uuid, rfc_emisor, fecha_recepcion, fecha_emision, onservaciones, xml_factura)
      VALUES
        (%s, %s, %s, %s, %s, %s, %s)
      RETURNING id;
    """ 
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (os_id, uuid, rfc_emisor, fecha_recepcion, fecha_emision, observaciones, xml_factura))
            row = cur.fetchone()
            conn.commit() 
            return int(row["id"])

def update_cfdi_meta(cfdi_id: int, fecha_recepcion, fecha_emision, observaciones: str | None) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
              UPDATE cat_facturas.cfdi
              SET fecha_recepcion=%s, fecha_emision=%s, onservaciones=%s
              WHERE id=%s;
            """, (fecha_recepcion, fecha_emision, observaciones, cfdi_id))
            conn.commit()

def update_cfdi_xml(cfdi_id: int, uuid: str, rfc_emisor: str, fecha_recepcion, fecha_emision, xml_factura: str) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
              UPDATE cat_facturas.cfdi
              SET uuid=%s, rfc_emisor=%s, fecha_recepcion=%s, fecha_emision=%s, xml_factura=%s
              WHERE id=%s;
            """, (uuid, rfc_emisor, fecha_recepcion, fecha_emision, xml_factura, cfdi_id))
            conn.commit()
 
def delete_cfdi(cfdi_id: int) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM cat_facturas.cfdi WHERE id=%s;", (cfdi_id,))
            conn.commit()
