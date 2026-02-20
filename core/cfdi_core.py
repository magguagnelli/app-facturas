# core/cfdi_core.py
from __future__ import annotations

import os
from datetime import datetime, date
from typing import Any, Dict, Optional, Tuple

from lxml import etree

CFDI_NS = "http://www.sat.gob.mx/cfd/4"
TFD_NS = "http://www.sat.gob.mx/TimbreFiscalDigital"

NS = {
    "cfdi": CFDI_NS,
    "tfd": TFD_NS,
}

def _project_root() -> str:
    # asume ejecución en raíz del repo o dentro del proyecto
    return os.getcwd()

def _xsd_base_path() -> str:
    # XSD/CFD/4 en raíz del proyecto
    return os.path.join(_project_root(), "XSD", "CFD", "4")

def _guess_main_xsd() -> str:
    """
    Intento robusto:
    - primero cfdv40.xsd (común)
    - si no existe, toma el primer .xsd en la carpeta
    """
    base = _xsd_base_path()
    c1 = os.path.join(base, "cfdv40.xsd")
    if os.path.exists(c1):
        return c1

    # fallback: primer xsd
    for fn in os.listdir(base) if os.path.exists(base) else []:
        if fn.lower().endswith(".xsd"):
            return os.path.join(base, fn)

    raise FileNotFoundError(f"No se encontró XSD principal en: {base}")

def strip_for_xsd_validation(xml_bytes: bytes) -> bytes:
    """
    Emula cfdi.py:
    - Quita TimbreFiscalDigital
    - Quita Addenda
    SOLO para validar XSD.
    """
    parser = etree.XMLParser(recover=False, remove_blank_text=True, huge_tree=True)
    doc = etree.fromstring(xml_bytes, parser=parser)

    # 1) quitar timbre(s)
    timbres = doc.xpath(
        "//cfdi:Complemento//tfd:TimbreFiscalDigital",
        namespaces=NS
    )
    for t in timbres:
        p = t.getparent()
        if p is not None:
            p.remove(t)

    # 2) quitar addenda(s)
    addendas = doc.findall(".//cfdi:Addenda", namespaces=NS)
    for a in addendas:
        p = a.getparent()
        if p is not None:
            p.remove(a)

    return etree.tostring(doc, encoding="utf-8", xml_declaration=True)


def validate_xml_well_formed(xml_bytes: bytes) -> Tuple[bool, str]:
    try:
        etree.fromstring(xml_bytes)
        return True, "XML bien formado."
    except Exception as e:
        return False, f"XML inválido: {e}"

def validate_xsd_cfdi40(xml_bytes_no_addenda: bytes):
    """
    Retorna SIEMPRE: (ok: bool, msg: str, errors: list[str])
    Emula validación estable con imports locales (SAT URLs -> archivos).
    """
    base = _xsd_base_path()
    xsd_main = os.path.join(base, "schema_cfdi40_con_timbre.xsd")
    if not os.path.exists(xsd_main):
        # fallback (pero recomendado crear el wrapper)
        xsd_main = os.path.join(base, "cfdv40.xsd")

    errors = []

    class LocalResolver(etree.Resolver):
        def resolve(self, url, pubid, context):
            # 1) si viene URL SAT, tomar basename
            fname = os.path.basename(url)

            # 2) intenta base/fname
            cand = os.path.join(base, fname)
            if os.path.exists(cand):
                return self.resolve_filename(cand, context)

            # 3) intenta base/url (por si es relativa)
            cand2 = os.path.join(base, url)
            if os.path.exists(cand2):
                return self.resolve_filename(cand2, context)

            # 4) búsqueda recursiva por si están en subcarpetas
            for root, _, files in os.walk(base):
                if fname in files:
                    return self.resolve_filename(os.path.join(root, fname), context)

            return None

    try:
        # Parser XSD con resolver
        xsd_parser = etree.XMLParser(load_dtd=False, no_network=True)
        xsd_parser.resolvers.add(LocalResolver())

        schema_doc = etree.parse(xsd_main, parser=xsd_parser)
        schema = etree.XMLSchema(schema_doc)

        # Parse XML (sin addenda) y validar
        xml_parser = etree.XMLParser(recover=False, huge_tree=True)
        doc = etree.fromstring(xml_bytes_no_addenda, parser=xml_parser)

        schema.assertValid(doc)
        return True, f"XSD OK usando {os.path.basename(xsd_main)}", errors

    except etree.DocumentInvalid as e:
        # errores detallados del schema
        try:
            for err in e.error_log:
                errors.append(f"[{err.line}:{err.column}] {err.message}")
        except Exception:
            errors.append(str(e))
        return False, "XSD inválido (estructura CFDI no cumple).", errors

    except Exception as e:
        return False, f"No fue posible validar XSD: {e}", [str(e)]

def extract_cfdi_fields(xml_bytes: bytes) -> Dict[str, Any]:
    """
    Extrae uuid, rfc_emisor, fecha_emision (cfdi:Comprobante@Fecha),
    fecha_timbrado (TimbreFiscalDigital@FechaTimbrado).
    """
    doc = etree.fromstring(xml_bytes)

    ##Campos solicitados
    emisor = doc.find(".//cfdi:Emisor", namespaces=NS)
    rfc_emisor = emisor.get("Rfc") if emisor is not None else None
    subtotal = doc.get("SubTotal")
    total = doc.get("Total")
    descuento = doc.get("Descuento")
    #IVA    
    iva = 0
    for traslado in doc.findall(".//cfdi:Traslado", namespaces=NS):
        if traslado.get("Impuesto") == "002":
            iva += float(traslado.get("Importe", 0))

    #ISR
    isr = 0
    for ret in doc.findall(".//cfdi:Retencion", namespaces=NS):
        if ret.get("Impuesto") == "001":
            isr += float(ret.get("Importe", 0))

    #Retenciones
    retenciones = 0
    for ret in doc.findall(".//cfdi:Retencion", namespaces=NS):
        if ret.get("Impuesto") not in ["001", "002"]:
            retenciones += float(ret.get("Importe", 0))

    importe_pago = float(total) - float(isr) - float(retenciones)

    timbre = doc.find(".//cfdi:Complemento/tfd:TimbreFiscalDigital", namespaces=NS)
    uuid = timbre.get("UUID") if timbre is not None else None
    fecha_timbrado_raw = timbre.get("FechaTimbrado") if timbre is not None else None

    fecha_emision_raw = doc.get("Fecha")  # Comprobante@Fecha

    def _to_date(s: Optional[str]) -> Optional[date]:
        if not s:
            return None
        # puede traer timezone, ej 2025-01-01T12:00:00
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
        except Exception:
            # intenta truncar
            try:
                return datetime.fromisoformat(s[:19]).date()
            except Exception:
                return None
        
    fields = {
        "uuid": uuid,
        "rfc_emisor": rfc_emisor,
        "fecha_emision": _to_date(fecha_emision_raw),
        "fecha_timbrado": _to_date(fecha_timbrado_raw),
        "iva":iva,
        "subtotal":subtotal,
        "con_iva":total,
        "descuento":descuento,
        "isr":isr,
        "importe_pago":importe_pago,
    }
    return fields

def build_validation_checklist(xml_bytes: bytes) -> Dict[str, Any]:
    """
    Checklist:
    - xml_ok (bien formado)
    - xsd_ok (CFDI 4.0, sin Addenda)
    - timbre_ok (UUID presente)
    """
    xml_ok, xml_msg = validate_xml_well_formed(xml_bytes)
    data = {"xml_ok": xml_ok, "xsd_ok": False, "timbre_ok": False, "messages": []}
    data["messages"].append(xml_msg)

    if not xml_ok:
        return data

    # extrae campos del original (con timbre)
    fields = extract_cfdi_fields(xml_bytes)
    data["timbre_ok"] = bool(fields.get("uuid"))
    data["messages"].append("Timbre OK." if data["timbre_ok"] else "Timbre NO encontrado (UUID faltante).")

    # valida XSD con XML sin addenda
    try:
        xml_wo = strip_for_xsd_validation(xml_bytes)
        res = validate_xsd_cfdi40(xml_wo)
        ok = res[0]
        msg = res[1] if len(res) > 1 else ""
        errors = res[2] if len(res) > 2 else []
        data["xsd_ok"] = ok
        data["messages"].append(msg)
        if errors:
            data["xsd_errors"] = errors[:25]  # opcional: limitar
    except Exception as e:
        data["xsd_ok"] = False
        data["messages"].append(f"No fue posible validar XSD: {e}")

    data["extracted"] = {
        "uuid": fields.get("uuid"),
        "rfc_emisor": fields.get("rfc_emisor"),
        "fecha_emision": fields.get("fecha_emision").isoformat() if fields.get("fecha_emision") else None,
        "fecha_timbrado": fields.get("fecha_timbrado").isoformat() if fields.get("fecha_timbrado") else None,
        "iva":fields.get("iva"),
        "subtotal":fields.get("subtotal"),
        "con_iva":fields.get("con_iva"),
        "descuento":fields.get("descuento"),
        "isr":fields.get("isr"),
        "importe_pago":fields.get("importe_pago"),
    }
    #print(data["extracted"])
    return data
