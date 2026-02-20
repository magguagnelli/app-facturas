# services/area_service.py
from __future__ import annotations

from psycopg.rows import dict_row
from core.db import get_conn


def list_areas() -> list[dict]:
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
              SELECT id, nombre_area, desc_area
              FROM cat_facturas.area
              ORDER BY lower(nombre_area), id
            """)
            return cur.fetchall()


def insert_area(nombre_area: str, desc_area: str | None) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
              INSERT INTO cat_facturas.area (nombre_area, desc_area)
              VALUES (%s, %s)
              RETURNING id
            """, (nombre_area, desc_area))
            new_id = cur.fetchone()[0]
        conn.commit()
    return int(new_id)


def update_area(area_id: int, nombre_area: str, desc_area: str | None) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
              UPDATE cat_facturas.area
              SET nombre_area=%s, desc_area=%s
              WHERE id=%s
            """, (nombre_area, desc_area, area_id))
        conn.commit()


def delete_area(area_id: int) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM cat_facturas.area WHERE id=%s", (area_id,))
        conn.commit()


def area_name_exists(nombre: str, exclude_id: int | None = None) -> bool:
    """
    Duplicados por nombre_area (trim + lower). exclude_id para edición.
    """
    nombre_norm = " ".join((nombre or "").strip().split())
    if not nombre_norm:
        return False

    with get_conn() as conn:
        with conn.cursor() as cur:
            if exclude_id is not None:
                cur.execute("""
                  SELECT 1
                  FROM cat_facturas.area
                  WHERE lower(trim(nombre_area)) = lower(trim(%s))
                    AND id <> %s
                  LIMIT 1
                """, (nombre_norm, exclude_id))
            else:
                cur.execute("""
                  SELECT 1
                  FROM cat_facturas.area
                  WHERE lower(trim(nombre_area)) = lower(trim(%s))
                  LIMIT 1
                """, (nombre_norm,))
            return cur.fetchone() is not None
