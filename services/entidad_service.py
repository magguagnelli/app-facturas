# services/entidad_service.py
from __future__ import annotations
from psycopg.rows import dict_row
from core.db import get_conn

ESTATUS = {"ACTIVO", "INACTIVO"}

def validate_entidad(data: dict):
    eid = (data.get("id") or "").strip().upper()
    nombre = (data.get("nombre") or "").strip()
    estatus = (data.get("estatus") or "ACTIVO").strip().upper()

    if not eid or len(eid) != 2:
        raise ValueError("El ID debe tener exactamente 2 caracteres.")
    if not nombre:
        raise ValueError("El nombre es obligatorio.")
    if estatus not in ESTATUS:
        raise ValueError("Estatus inválido.")

def list_entidades() -> list[dict]:
    sql = """
      SELECT id, nombre, estatus
      FROM cat_facturas.entidad
      ORDER BY id;
    """
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql)
            return cur.fetchall()

def get_entidad(eid: str) -> dict | None:
    sql = """
      SELECT id, nombre, estatus
      FROM cat_facturas.entidad
      WHERE id = %s;
    """
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (eid,))
            return cur.fetchone()

def create_entidad(data: dict):
    validate_entidad(data)

    sql = """
      INSERT INTO cat_facturas.entidad (id, nombre, estatus)
      VALUES (%(id)s, %(nombre)s, %(estatus)s);
    """
    payload = {
        "id": data["id"].strip().upper(),
        "nombre": data["nombre"].strip(),
        "estatus": (data.get("estatus") or "ACTIVO").upper(),
    }

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, payload)
            conn.commit()

def update_entidad(eid: str, data: dict):
    validate_entidad(data)

    sql = """
      UPDATE cat_facturas.entidad
      SET nombre = %(nombre)s,
          estatus = %(estatus)s
      WHERE id = %(id)s;
    """
    payload = {
        "id": eid,
        "nombre": data["nombre"].strip(),
        "estatus": (data.get("estatus") or "ACTIVO").upper(),
    }

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, payload)
            conn.commit()
