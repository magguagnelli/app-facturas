# services/catalogos_service.py
from __future__ import annotations

from io import BytesIO
import os
import unicodedata
from datetime import datetime, date

import pandas as pd
from core.db import get_conn
from core.audit import audit


# Hojas canónicas y columnas esperadas
HOJAS_REQUERIDAS = {
    "Área": ["NOMBRE_AREA", "DESC_AREA"],
   "Proveedor": ["RFC", "RAZON_SOCIAL", "TIPO_PERSONA", "TELEFONO", "EMAIL", "ESTATUS", "NOMBRE_COMERCIAL"],
   "Usuario": ["NOMBRE", "PWD", "EMAIL", "ROL", "ESTATUS"],
   "Contrato": ["RFC_PP", "F_INICIO", "F_FIN", "NUM_CONTRATO", "EJERCICIO", "MES",
                "MONTO_TOTAL", "MONTO_MAXIMO", "MONTO_EJERCIDO", "SALDO_DISPONIBLE",
                "ESTATUS", "AREA", "OBSERVACIONES","TIPO DE CONTRATO"],
   "Partida": ["CONTRATO", "CAPITULO", "DES_CAP", "CONCEPTO", "DES_CONCEPTO",
               "USO_PARTIDA", "DES_USO_PARTIDA", "PARTIDA_ESPECIFICA", "DES_PE",
               "TIPO_GASTO", "AUSTERIDAD", "PP", "DES_PP", "ENTIDAD", "MONTO_TOTAL", "OBSERVACIONES"]#,
   #"Orden": ["PARTIDA", "PROVEEDOR", "FECHA_ORDEN", "FOLIO_OFICIO", "FECHA_FACTURA",
    #         "FOLIO_INTERNO", "CUENTA_BANCARIA", "BANCO", "MES_SERVICIO",
     #        "MONTO_SINIVA", "IVA", "MONTO_C_IVA", "ISR", "IEPS", "DESCUENTO",
      #       "OTRAS_CONTRIBUCIONES", "RETENCIONES", "PENALIZACION", "DEDUCTIVA",
       #      "IMPORTE_PAGO", "IMPORTE_P_COMPROMISO", "NO_COMPROMISO", "ESTATUS",
        #     "FECHA_PAGO", "ARCHIVO", "OBSERVACIONES"]
}

# Aliases tolerantes → hoja canónica
SHEET_ALIASES = {
    "area": "Área",
    "areas": "Área",
    "área": "Área",
    "áreas": "Área",

    "proveedor": "Proveedor",
    "proveedores": "Proveedor",

    "usuario": "Usuario",
    "usuarios": "Usuario",

    "contrato": "Contrato",
    "contratos": "Contrato",

    "partida": "Partida",
    "partidas": "Partida",

    "orden": "Orden",
    "ordenes": "Orden",
    "órdenes": "Orden",
    "ordenes de suministro": "Orden",
    "orden de suministro": "Orden",
    "orden_suministro": "Orden",
    "orden suministro": "Orden",
}


def _strip_accents(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s


def normalize_sheet_name(name: str) -> str:
    """Normaliza nombres de hoja (acentos/mayúsculas/espacios)."""
    n = (name or "").strip()
    n = _strip_accents(n)
    n = n.lower()
    n = " ".join(n.split())
    return n


def resolve_sheet_map(sheet_names: list[str]) -> dict[str, str]:
    """Regresa mapeo: hoja_canónica -> hoja_real_en_excel."""
    found: dict[str, str] = {}
    for real in sheet_names:
        key = normalize_sheet_name(real)
        canonical = SHEET_ALIASES.get(key)
        if canonical and canonical not in found:
            found[canonical] = real
    return found


def normalizar_texto(valor, max_len: int | None = None):
    """Normaliza texto y evita NaN->'NAN'; recorta a max_len si se indica."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)) or pd.isna(valor):
        return None

    v = str(valor).strip()
    if v == "":
        return None

    v = unicodedata.normalize("NFKD", v)
    v = "".join(c for c in v if not unicodedata.combining(c))
    v = v.upper()

    if max_len is not None and len(v) > max_len:
        v = v[:max_len]

    return v


def safe_int(valor, default=0):
    if valor is None or (isinstance(valor, float) and pd.isna(valor)) or pd.isna(valor):
        return default
    try:
        return int(valor)
    except Exception:
        return default


def safe_float(valor, default=0.0):
    if valor is None or (isinstance(valor, float) and pd.isna(valor)) or pd.isna(valor):
        return default
    try:
        return float(valor)
    except Exception:
        return default


def safe_date(valor):
    if valor is None or pd.isna(valor):
        return None
    if hasattr(valor, "to_pydatetime"):
        return valor.to_pydatetime().date()
    if hasattr(valor, "date"):
        return valor.date()
    if isinstance(valor, date):
        return valor
    try:
        return datetime.fromisoformat(str(valor)).date()
    except Exception:
        return None


def validate_excel_structure(xls: pd.ExcelFile, sheet_map: dict[str, str]) -> list[str]:
    errores = []
    for canonical, columnas_esperadas in HOJAS_REQUERIDAS.items():
        if canonical not in sheet_map:
            errores.append(
                f"Falta la hoja obligatoria: '{canonical}'. "
                f"(Se aceptan variantes: {', '.join(sorted([k for k,v in SHEET_ALIASES.items() if v == canonical]))})"
            )
            continue

        real_sheet = sheet_map[canonical]
        df0 = pd.read_excel(xls, sheet_name=real_sheet, nrows=0)
        columnas_reales = list(df0.columns)

        faltantes = [c for c in columnas_esperadas if c not in columnas_reales]
        extras = [c for c in columnas_reales if c not in columnas_esperadas]

        if faltantes:
            errores.append(
                f"Hoja '{real_sheet}' (mapeada a '{canonical}') tiene diferencias:\n"
                f"  Columnas esperadas: {', '.join(columnas_esperadas)}\n"
                f"  Columnas reales: {', '.join(columnas_reales)}\n"
                f"  Faltantes: {', '.join(faltantes)}\n"
                f"  Extras: {', '.join(extras) if extras else 'ninguna'}"
            )
    return errores

def _get_id(row):
    """Soporta fetchone() como tuple/list (id,), dict {'id':..} o None."""
    if row is None:
        return None
    if isinstance(row, (tuple, list)):
        return row[0] if len(row) else None
    if isinstance(row, dict):
        # RealDictCursor
        return row.get("id") or row.get("ID")
    # fallback por si es Row/Mapping
    try:
        return row["id"]
    except Exception:
        return None


def process_catalogos_excel(*, excel_bytes: bytes, filename: str, actor_email: str, request_log: str) -> dict:
    xls = pd.ExcelFile(BytesIO(excel_bytes))

    sheet_map = resolve_sheet_map(xls.sheet_names)
    errores = validate_excel_structure(xls, sheet_map)
    if errores:
        return {
            "ok": False,
            "message": "El Excel no cumple la estructura requerida (hojas/columnas).",
            "file": filename,
            "errors": errores,
            "detected_sheets": xls.sheet_names,
            "sheet_map": sheet_map,
        }

    # Lee usando nombres REALES (tolerancia aplicada)
    df_area = pd.read_excel(xls, sheet_name=sheet_map["Área"])
    df_prov = pd.read_excel(xls, sheet_name=sheet_map["Proveedor"])
    df_user = pd.read_excel(xls, sheet_name=sheet_map["Usuario"])
    df_contrato = pd.read_excel(xls, sheet_name=sheet_map["Contrato"])
    df_partida = pd.read_excel(xls, sheet_name=sheet_map["Partida"])
    df_orden = pd.read_excel(xls, sheet_name=sheet_map["Orden"])

    summary = {
        "Área": {"inserted": 0, "updated": 0, "errors": 0},
        "Proveedor": {"inserted": 0, "updated": 0, "errors": 0},
        "Usuario": {"inserted": 0, "updated": 0, "errors": 0},
        "Contrato": {"inserted": 0, "updated": 0, "errors": 0},
        "Partida": {"inserted": 0, "updated": 0, "errors": 0},
        "Orden": {"inserted": 0, "updated": 0, "errors": 0},
    }

    row_errors: list[dict] = []

    debug = os.getenv("DEBUG", "0") == "1"
    debug_attempts: list[dict] = []

    with get_conn() as conn:
        try:
            with conn.cursor() as cur:
                def _log_attempt(sheet: str, rowno: int, action: str, sql: str, params):
                    # Guarda intentos sólo en modo debug para no inflar la respuesta
                    if debug:
                        debug_attempts.append({
                            "sheet": sheet,
                            "row": rowno,
                            "action": action,
                            "sql": sql,
                            "params": repr(params),
                        })

                def _exec_iou(sheet: str, rowno: int, action: str, sql: str, params):
                    """Execute INSERT/UPDATE y registra error por fila; en debug incluye query+params."""
                    _log_attempt(sheet, rowno, action, sql, params)
                    try:
                        cur.execute(sql, params)
                        return True
                    except Exception as e:
                        err = {"sheet": sheet, "row": rowno, "action": action, "error": str(e)}
                        if debug:
                            err["sql"] = sql
                            err["params"] = repr(params)
                        row_errors.append(err)
                        return False

                # 1) ÁREA (upsert por nombre) - con recorte varchar(300/500)
                for idx, r in df_area.iterrows():
                    try:
                        nombre = normalizar_texto(r.get("NOMBRE_AREA"), max_len=300)  # varchar(300)
                        desc = normalizar_texto(r.get("DESC_AREA"), max_len=500)      # varchar(500)

                        if not nombre:
                            summary["Área"]["errors"] += 1
                            row_errors.append({"sheet": "Área", "row": int(idx) + 2, "error": "NOMBRE_AREA vacío"})
                            continue

                        cur.execute(
                            "SELECT id FROM cat_facturas.area WHERE upper(trim(nombre_area))=upper(trim(%s)) LIMIT 1",
                            (nombre,),
                        )
                        hit = cur.fetchone()

                        uid = _get_id(hit)

                        if not hit:
                            if _exec_iou("Área", int(idx)+2, "INSERT", "INSERT INTO cat_facturas.area (nombre_area, desc_area) VALUES (%s, %s)", (nombre, desc)):
                                summary["Área"]["inserted"] += 1
                        else:
                            if _exec_iou("Área", int(idx)+2, "UPDATE", "UPDATE cat_facturas.area SET desc_area=%s WHERE id=%s", (desc, int(uid))):
                                summary["Área"]["updated"] += 1
                    except Exception as e:
                        summary["Área"]["errors"] += 1
                        row_errors.append({"sheet": "Área", "row": int(idx) + 2, "error": str(e)})

                # 2) PROVEEDOR (upsert RFC)
                for idx, r in df_prov.iterrows():
                    rfc = normalizar_texto(r.get("RFC"), max_len=13)
                    razon = normalizar_texto(r.get("RAZON_SOCIAL"), max_len=300)
                    tipo = normalizar_texto(r.get("TIPO_PERSONA"), max_len=10)
                    tel = normalizar_texto(r.get("TELEFONO"), max_len=15)
                    email = (str(r.get("EMAIL")).strip()[:100] if r.get("EMAIL") is not None and not pd.isna(r.get("EMAIL")) else None)
                    estatus = normalizar_texto(r.get("ESTATUS"), max_len=10) or "ACTIVO"
                    nom_com = normalizar_texto(r.get("NOMBRE_COMERCIAL"), max_len=300)

                    if not rfc or not razon or not tipo:
                        summary["Proveedor"]["errors"] += 1
                        row_errors.append({"sheet": "Proveedor", "row": int(idx) + 2, "error": "RFC/RAZON_SOCIAL/TIPO_PERSONA requerido"})
                        continue
                    
                    
                    cur.execute("SELECT id FROM cat_facturas.proveedor WHERE rfc=%s LIMIT 1", (rfc,))
                    hit = cur.fetchone()
                    prov_id = _get_id(hit)
                    if not prov_id:
                        if _exec_iou("Proveedor", int(idx)+2, "INSERT", """
                            INSERT INTO cat_facturas.proveedor
                            (rfc, razon_social, tipo_persona, telefono, email, estatus, nombre_comercial)
                            VALUES (%s,%s,%s,%s,%s,%s,%s)
                        """, (rfc, razon, tipo, tel, email, estatus, nom_com)):
                            summary["Proveedor"]["inserted"] += 1
                    else:
                        #print(int(hit[0]))
                        if _exec_iou("Proveedor", int(idx)+2, "UPDATE", """
                            UPDATE cat_facturas.proveedor
                            SET razon_social=%s, tipo_persona=%s, telefono=%s, email=%s, estatus=%s, nombre_comercial=%s
                            WHERE id=%s
                        """, (razon, tipo, tel, email, estatus, nom_com, int(prov_id))):
                            summary["Proveedor"]["updated"] += 1

                # 3) USUARIO (upsert correo)
                for idx, r in df_user.iterrows():
                    nombre = (str(r.get("NOMBRE")).strip()[:200] if r.get("NOMBRE") is not None and not pd.isna(r.get("NOMBRE")) else None)
                    correo = (str(r.get("EMAIL")).strip().lower()[:100] if r.get("EMAIL") is not None and not pd.isna(r.get("EMAIL")) else None)
                    rol = normalizar_texto(r.get("ROL"), max_len=20)
                    estatus = normalizar_texto(r.get("ESTATUS"), max_len=10) or "ACTIVO"
                    pwd = (str(r.get("PWD")).strip()[:255] if r.get("PWD") is not None and not pd.isna(r.get("PWD")) else None)

                    if not correo or not nombre or not rol or not pwd:
                        summary["Usuario"]["errors"] += 1
                        row_errors.append({"sheet": "Usuario", "row": int(idx) + 2, "error": "NOMBRE/EMAIL/ROL/PWD requerido"})
                        continue

                    cur.execute("SELECT id FROM cat_facturas.usuario WHERE lower(correo)=lower(%s) LIMIT 1", (correo,))
                    hit = cur.fetchone()
                    uid = _get_id(hit)

                    if not hit:
                        if _exec_iou("Usuario", int(idx)+2, "INSERT", """
                            INSERT INTO cat_facturas.usuario (nombre, pwd, correo, rol, estatus)
                            VALUES (%s,%s,%s,%s,%s)
                        """, (nombre, pwd, correo, rol, estatus)):
                            summary["Usuario"]["inserted"] += 1
                    else:
                        if _exec_iou("Usuario", int(idx)+2, "UPDATE", """
                            UPDATE cat_facturas.usuario
                            SET nombre=%s, pwd=%s, rol=%s, estatus=%s
                            WHERE id=%s
                        """, (nombre, pwd, rol, estatus, int(uid))):
                            summary["Usuario"]["updated"] += 1

                # 4) CONTRATO (upsert num_contrato) + FK area por nombre_area
                for idx, r in df_contrato.iterrows():
                    rfc_pp = normalizar_texto(r.get("RFC_PP"), max_len=13)
                    f_inicio = safe_date(r.get("F_INICIO"))
                    f_fin = safe_date(r.get("F_FIN"))
                    num_contrato = normalizar_texto(r.get("NUM_CONTRATO"), max_len=50)
                    ejercicio = safe_int(r.get("EJERCICIO"))
                    mes = safe_int(r.get("MES"))
                    monto_total = safe_float(r.get("MONTO_TOTAL"))
                    monto_maximo = safe_float(r.get("MONTO_MAXIMO"))
                    monto_ejercido = safe_float(r.get("MONTO_EJERCIDO"))
                    estatus = normalizar_texto(r.get("ESTATUS"), max_len=10) or "ACTIVO"
                    area_txt = normalizar_texto(r.get("AREA"), max_len=300)
                    obs = normalizar_texto(r.get("OBSERVACIONES"), max_len=255)
                    tc = normalizar_texto(r.get("TIPO DE CONTRATO"),max_len = 100)


                    if not num_contrato or not area_txt or not f_inicio or not f_fin:
                        summary["Contrato"]["errors"] += 1
                        row_errors.append({"sheet": "Contrato", "row": int(idx) + 2, "error": "NUM_CONTRATO/AREA/F_INICIO/F_FIN requerido"})
                        continue

                    cur.execute("SELECT id FROM cat_facturas.area WHERE upper(trim(nombre_area))=upper(trim(%s)) LIMIT 1", (area_txt,))
                    area_row = cur.fetchone()
                    prov_id = _get_id(area_row)
                    if not area_row:
                        summary["Contrato"]["errors"] += 1
                        row_errors.append({"sheet": "Contrato", "row": int(idx) + 2, "error": f"Área no encontrada: {area_txt}"})
                        continue
                    area_id = int(prov_id)

                    cur.execute("SELECT id FROM cat_facturas.contrato WHERE num_contrato=%s LIMIT 1", (num_contrato,))
                    hit = cur.fetchone()
                    cont_id = _get_id(hit);
                    if not cont_id:
                        if _exec_iou("Contrato", int(idx)+2, "INSERT", """
                            INSERT INTO cat_facturas.contrato
                            (rfc_pp, f_inicio, f_fin, num_contrato, ejercicio, mes,
                             monto_total, monto_maximo, monto_ejercido, estatus, area, observaciones, tipo_de_contrato)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, %s)
                        """, (rfc_pp, f_inicio, f_fin, num_contrato, ejercicio, mes,
                              monto_total, monto_maximo, monto_ejercido, estatus, area_id, obs, tc)):
                            summary["Contrato"]["inserted"] += 1
                        
                         # Obtener el id recién insertado
                        cur.execute("SELECT id FROM cat_facturas.contrato WHERE num_contrato=%s LIMIT 1", (num_contrato,))
                        row2 = cur.fetchone()
                        part_idt2 = _get_id(row2)
                       
                        audit(
                            correo=actor_email,
                            accion="ALTA CONTRATO",
                            descripcion=f"Alta Contrato id={part_idt2}",
                            log_accion="",
                            seccion="cat_facturas.contrato",
                            id_sec= str(part_idt2)
                        )

                    else:
                        if _exec_iou("Contrato", int(idx)+2, "UPDATE", """
                            UPDATE cat_facturas.contrato
                            SET rfc_pp=%s, f_inicio=%s, f_fin=%s, ejercicio=%s, mes=%s,
                                monto_total=%s, monto_maximo=%s, monto_ejercido=%s,
                                estatus=%s, area=%s, observaciones=%s, tipo_de_contrato=%s
                            WHERE id=%s
                        """, (rfc_pp, f_inicio, f_fin, ejercicio, mes,
                              monto_total, monto_maximo, monto_ejercido,
                              estatus, area_id, obs, tc, int(cont_id ))):
                            summary["Contrato"]["updated"] += 1
                        
                        audit(
                            correo=actor_email,
                            accion="EDICION CONTRATO",
                            descripcion=f"Edicion Contrato id={cont_id}",
                            log_accion="",
                            seccion="cat_facturas.contrato",
                            id_sec= str(cont_id)
                        )

                # 5) PARTIDA (upsert contrato_id + partida_especifica) + FK entidad por nombre
                for idx, r in df_partida.iterrows():
                    contrato_txt = normalizar_texto(r.get("CONTRATO"), max_len=50)
                    partida_especifica = normalizar_texto(r.get("PARTIDA_ESPECIFICA"), max_len=10)
                    entidad_txt = (str(r.get("ENTIDAD")).strip()[:50] if r.get("ENTIDAD") is not None and not pd.isna(r.get("ENTIDAD")) else None)

                    capitulo = normalizar_texto(r.get("CAPITULO"), max_len=50)
                    des_cap = normalizar_texto(r.get("DES_CAP"), max_len=50)
                    concepto = normalizar_texto(r.get("CONCEPTO"), max_len=10)
                    des_concepto = normalizar_texto(r.get("DES_CONCEPTO"), max_len=50)
                    uso_partida = normalizar_texto(r.get("USO_PARTIDA"), max_len=10)
                    des_uso_partida = normalizar_texto(r.get("DES_USO_PARTIDA"), max_len=50)
                    des_pe = normalizar_texto(r.get("DES_PE"), max_len=50)
                    tipo_gasto = normalizar_texto(r.get("TIPO_GASTO"), max_len=30)
                    austeridad = normalizar_texto(r.get("AUSTERIDAD"), max_len=50)
                    pp = normalizar_texto(r.get("PP"), max_len=10)
                    des_pp = normalizar_texto(r.get("DES_PP"), max_len=50)
                    monto_total = safe_float(r.get("MONTO_TOTAL"))
                    obs = normalizar_texto(r.get("OBSERVACIONES"), max_len=255)

                    if not contrato_txt or not partida_especifica or not entidad_txt:
                        summary["Partida"]["errors"] += 1
                        row_errors.append({"sheet": "Partida", "row": int(idx) + 2, "error": "CONTRATO/PARTIDA_ESPECIFICA/ENTIDAD requerido"})
                        continue

                    cur.execute("SELECT id FROM cat_facturas.contrato WHERE num_contrato=%s LIMIT 1", (contrato_txt,))
                    contrato_row = cur.fetchone()
                    cont_id = _get_id(contrato_row)
                    if not cont_id:
                        summary["Partida"]["errors"] += 1
                        row_errors.append({"sheet": "Partida", "row": int(idx) + 2, "error": f"Contrato no encontrado: {contrato_txt}"})
                        continue
                    contrato_id = int(cont_id)

                    cur.execute("SELECT id FROM cat_facturas.entidad WHERE nombre=%s LIMIT 1", (entidad_txt,))
                    entidad_row = cur.fetchone()
                    entidad_id = _get_id(entidad_row)
                    if not entidad_id:
                        summary["Partida"]["errors"] += 1
                        row_errors.append({"sheet": "Partida", "row": int(idx) + 2, "error": f"Entidad no encontrada: {entidad_txt}"})
                        continue
                    
                    cur.execute("""
                        SELECT id FROM cat_facturas.partida
                        WHERE contrato=%s AND partida_especifica=%s
                        LIMIT 1
                    """, (contrato_id, partida_especifica))
                    hit = cur.fetchone()
                    part_id = _get_id(hit)
#
                    if not part_id:
                        if _exec_iou("Partida", int(idx)+2, "INSERT", """
                            INSERT INTO cat_facturas.partida
                            (contrato, capitulo, des_cap, concepto, des_concepto,
                             uso_partida, des_uso_partida, partida_especifica, des_pe,
                             tipo_gasto, austeridad, pp, des_pp, entidad, monto_total, observaciones)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """, (contrato_id, capitulo, des_cap, concepto, des_concepto,
                              uso_partida, des_uso_partida, partida_especifica, des_pe,
                              tipo_gasto, austeridad, pp, des_pp, entidad_id, monto_total, obs)):
                            summary["Partida"]["inserted"] += 1

                        # Obtener el id recién insertado
                        cur.execute("""
                            SELECT id FROM cat_facturas.partida
                            WHERE contrato=%s AND partida_especifica=%s
                            LIMIT 1
                        """, (contrato_id, partida_especifica))
                        row1 = cur.fetchone()
                        part_idt = _get_id(row1)
                       
                        audit(
                            correo=actor_email,
                            accion="ALTA PARTIDA",
                            descripcion=f"Alta Partida id={part_idt}",
                            log_accion="",
                            seccion="cat_facturas.partida",
                            id_sec= str(part_idt)
                        )

                    else:
                        if _exec_iou("Partida", int(idx)+2, "UPDATE", """
                            UPDATE cat_facturas.partida
                            SET capitulo=%s, des_cap=%s, concepto=%s, des_concepto=%s,
                                uso_partida=%s, des_uso_partida=%s, des_pe=%s,
                                tipo_gasto=%s, austeridad=%s, pp=%s, des_pp=%s,
                                entidad=%s, monto_total=%s, observaciones=%s
                            WHERE id=%s
                        """, (capitulo, des_cap, concepto, des_concepto,
                              uso_partida, des_uso_partida, des_pe,
                              tipo_gasto, austeridad, pp, des_pp,
                              entidad_id, monto_total, obs, int(part_id))):
                            summary["Partida"]["updated"] += 1

                        audit(
                            correo=actor_email,
                            accion="EDICION PARTIDA",
                            descripcion=f"Edicion Partida id={part_id}",
                            log_accion="",
                            seccion="cat_facturas.partida",
                            id_sec= str(part_id)
                        )
#
                # 6) ORDEN SUMINISTRO: PROVEEDOR en Excel = RFC
                #for idx, r in df_orden.iterrows():
                 #   rowno = int(idx) + 2
                  #  partida_txt = normalizar_texto(r.get("PARTIDA"), max_len=10)
                #    proveedor = normalizar_texto(r.get("PROVEEDOR"))

##
#                    fecha_orden = safe_date(r.get("FECHA_ORDEN"))
#                    folio_oficio = normalizar_texto(r.get("FOLIO_OFICIO"), max_len=20)
#                    fecha_factura = safe_date(r.get("FECHA_FACTURA"))
#                    folio_interno = normalizar_texto(r.get("FOLIO_INTERNO"), max_len=20)
#                    cuenta_bancaria = normalizar_texto(r.get("CUENTA_BANCARIA"), max_len=30)
#                    banco = normalizar_texto(r.get("BANCO"), max_len=20)
#                    mes_servicio = normalizar_texto(r.get("MES_SERVICIO"), max_len=10)
##
#                    monto_siniva = safe_float(r.get("MONTO_SINIVA"))
#                    iva = safe_float(r.get("IVA"))
#                    monto_c_iva = safe_float(r.get("MONTO_C_IVA"))
#                    isr = safe_float(r.get("ISR"))
#                    ieps = safe_float(r.get("IEPS"))
#                    descuento = safe_float(r.get("DESCUENTO"))
#                    otras_contrib = safe_float(r.get("OTRAS_CONTRIBUCIONES"))
#                    retenciones = safe_float(r.get("RETENCIONES"))
#                    penalizacion = safe_float(r.get("PENALIZACION"))
#                    deductiva = safe_float(r.get("DEDUCTIVA"))
#                    importe_pago = safe_float(r.get("IMPORTE_PAGO"))
#                    importe_p_comp = safe_float(r.get("IMPORTE_P_COMPROMISO"))
#                    no_comp = safe_int(r.get("NO_COMPROMISO"))
#                    estatus = safe_int(r.get("ESTATUS"), 1)
#                    fecha_pago = safe_date(r.get("FECHA_PAGO"))
#                    archivo = normalizar_texto(r.get("ARCHIVO"), max_len=100)
#                    obs = normalizar_texto(r.get("OBSERVACIONES"), max_len=255)
##
#                    # Validaciones básicas
#                    if not partida_txt or not proveedor:
#                        summary["Orden"]["errors"] += 1
#                        row_errors.append({"sheet": "Orden", "row": rowno, "error": "PARTIDA/PROVEEDOR(RFC) requerido"})
#                        continue
#                    
#                    
#                    # Obtener ID de partida
#                    cur.execute("SELECT id FROM cat_facturas.partida WHERE partida_especifica=%s LIMIT 1", (partida_txt,))
#                    partida_row = cur.fetchone()
#                    if not partida_row:
#                        summary["Orden"]["errors"] += 1
#                        row_errors.append({"sheet": "Orden", "row": rowno, "error": f"Partida no encontrada: {partida_txt}"})
#                        continue
#                    partida_id = _get_id(partida_row)
#
#                    # Obtener ID de proveedor
#                    cur.execute("SELECT id FROM cat_facturas.proveedor WHERE razon_social=%s LIMIT 1", (proveedor,))
#                    prov_row = cur.fetchone()
#                    if not prov_row:
#                        summary["Orden"]["errors"] += 1
#                        row_errors.append({"sheet": "Orden", "row": rowno, "error": f"Proveedor no encontrado por RFC: {proveedor}"})
#                        continue
#                    prov_id = _get_id(prov_row)
#
#                    # Buscar orden existente
#                    cur.execute("""
#                        SELECT id FROM cat_facturas.orden_suministro
#                        WHERE partida=%s AND proveedor=%s
#                        LIMIT 1
#                    """, (partida_id, prov_id))
#                    hit = cur.fetchone()
#                    uid = _get_id(hit)
#
#                    if not hit:
#                        if _exec_iou("Orden", int(idx)+2, "INSERT", """
#                            INSERT INTO cat_facturas.orden_suministro
#                            (partida, proveedor, fecha_orden, folio_oficio, fecha_factura, folio_interno,
#                             cuenta_bancaria, banco, mes_servicio, monto_siniva, iva, monto_c_iva, isr, ieps,
#                             descuento, otras_contribuciones, retenciones, penalizacion, deductiva,
#                             importe_pago, importe_p_compromiso, no_compromiso, observaciones,
#                             estatus, fecha_pago, archivo)
#                            VALUES
#                            (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
#                        """, (partida_id, prov_id, fecha_orden, folio_oficio, fecha_factura, folio_interno,
#                              cuenta_bancaria, banco, mes_servicio, monto_siniva, iva, monto_c_iva, isr, ieps,
#                              descuento, otras_contrib, retenciones, penalizacion, deductiva,
#                              importe_pago, importe_p_comp, no_comp, obs,
#                              estatus, fecha_pago, archivo)):
#                            summary["Orden"]["inserted"] += 1
#
#                         # Obtener el id recién insertado
#                        cur.execute("""
#                        SELECT id FROM cat_facturas.orden_suministro
#                        WHERE partida=%s AND proveedor=%s
#                        LIMIT 1
#                    """, (partida_id, prov_id))
#                        row3 = cur.fetchone()
#                        part_idt3 = _get_id(row3)
#                       
#                        audit(
#                            correo=actor_email,
#                            accion="ALTA ORDEN",
#                            descripcion=f"Alta Orden id={part_idt3}",
#                            log_accion="",
#                            seccion="cat_facturas.orden_suministro",
#                            id_sec= str(part_idt3)
#                        )   
#
#                    else:
#                        if _exec_iou("Orden", int(idx)+2, "UPDATE", """
#                            UPDATE cat_facturas.orden_suministro
#                            SET fecha_orden=%s, folio_oficio=%s, fecha_factura=%s, folio_interno=%s,
#                                cuenta_bancaria=%s, banco=%s, mes_servicio=%s,
#                                monto_siniva=%s, iva=%s, monto_c_iva=%s, isr=%s, ieps=%s, descuento=%s,
#                                otras_contribuciones=%s, retenciones=%s, penalizacion=%s, deductiva=%s,
#                                importe_pago=%s, importe_p_compromiso=%s, no_compromiso=%s,
#                                observaciones=%s, estatus=%s, fecha_pago=%s, archivo=%s
#                            WHERE id=%s
#                        """, (fecha_orden, folio_oficio, fecha_factura, folio_interno,
#                              cuenta_bancaria, banco, mes_servicio,
#                              monto_siniva, iva, monto_c_iva, isr, ieps, descuento,
#                              otras_contrib, retenciones, penalizacion, deductiva,
#                              importe_pago, importe_p_comp, no_comp,
#                              obs, estatus, fecha_pago, archivo, int(uid))):
#                            summary["Orden"]["updated"] += 1
#
#                        audit(
#                            correo=actor_email,
#                            accion="EDICION ORDEN",
#                            descripcion=f"Edicion Orden id={uid}",
#                            log_accion="",
#                            seccion="cat_facturas.orden_suministro",
#                            id_sec= str(uid)
#                        )

            conn.commit()

        except Exception:
            conn.rollback()
            raise

    result = {
        "ok": True,
        "message": "Archivo procesado correctamente.",
        "file": filename,
        "total_sheets": len(HOJAS_REQUERIDAS),
        "sheet_map": sheet_map,
        "summary": summary,
        "row_errors": row_errors[:2000],
        "notes": [
            "Se aceptan variantes de nombres de hoja (acentos/mayúsculas/espacios).",
            "Orden.PROVEEDOR debe ser RFC (12/13) y debe existir previamente en cat_facturas.proveedor.",
            "Usuario.PWD debe venir como hash compatible con tu login (ej. $argon2id$...).",
            "Partida.ENTIDAD se busca por nombre en cat_facturas.entidad; debe existir previamente.",
            "Se recortan textos a longitudes de columnas para evitar errores varchar."
        ],
    }

    if debug:
        # Limita para no inflar demasiado el JSON
        result["debug_attempts"] = debug_attempts[:5000]

    return result
