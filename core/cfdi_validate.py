# core/cfdi_validate.py
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
from lxml import etree
from urllib.parse import urlparse
import base64
import os
import re

# -----------------------------
# Timbre validators (TimbreFiscalDigital 1.1)
# -----------------------------
def _is_base64(s: str) -> bool:
    try:
        b = s.encode("utf-8")
        return base64.b64encode(base64.b64decode(b)) == b
    except Exception:
        return False

_TFD_VALIDATORS = {
    "Version": lambda v: v == "1.1",
    "UUID": lambda v: bool(re.fullmatch(r"[A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12}", v)),
    "FechaTimbrado": lambda v: bool(re.fullmatch(r"(20[1-9][0-9])-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]([+-][0-2][0-9]:[0-5][0-9]|Z)?", v)),
    "RfcProvCertif": lambda v: bool(re.fullmatch(r"[A-Z&Ñ]{3}[0-9]{2}(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])[A-Z0-9]{2}[0-9A]", v)),
    "SelloCFD": _is_base64,
    "NoCertificadoSAT": lambda v: bool(re.fullmatch(r"[0-9]{20}", v)),
    "SelloSAT": _is_base64,
}

def validar_timbre(timbre_elem: etree._Element) -> Dict[str, str]:
    res: Dict[str, str] = {}
    for attr, validator in _TFD_VALIDATORS.items():
        val = (timbre_elem.get(attr) or "").strip()
        if not val:
            res[attr] = "faltante"
        elif not validator(val):
            res[attr] = "inválido"
        else:
            res[attr] = "ok"
    return res


# -----------------------------
# XSD local resolver
# -----------------------------
class LocalResolver(etree.Resolver):
    """Resuelve imports/includes de XSD usando archivos locales."""
    def __init__(self, xsd_path: str):
        super().__init__()
        self.xsd_path = xsd_path

    def resolve(self, system_url, public_id, context):
        filename = os.path.basename(urlparse(system_url).path)
        full_path = os.path.join(self.xsd_path, filename)
        if os.path.exists(full_path):
            return self.resolve_filename(full_path, context)
        return None


def _parse_xml(xml_bytes: bytes) -> Tuple[bool, Optional[etree._Element], str]:
    try:
        doc = etree.fromstring(xml_bytes)
        return True, doc, ""
    except etree.XMLSyntaxError as e:
        return False, None, f"XML inválido: {str(e)}"


def _strip_for_xsd(doc: etree._Element) -> Tuple[etree._Element, Dict[str, bool]]:
    """Copia profunda y remueve timbre/addenda SOLO para validar XSD."""
    info = {"addenda_removed": False, "timbre_removed": False}
    xsd_doc = etree.fromstring(etree.tostring(doc))  # deep copy

    ns = {
        "cfdi": "http://www.sat.gob.mx/cfd/4",
        "tfd": "http://www.sat.gob.mx/TimbreFiscalDigital",
    }

    # remover timbre antes de validar XSD CFDI
    for tfd in xsd_doc.xpath("//cfdi:Complemento//tfd:TimbreFiscalDigital", namespaces=ns):
        parent = tfd.getparent()
        if parent is not None:
            parent.remove(tfd)
            info["timbre_removed"] = True

    # remover addenda antes de validar XSD CFDI
    for addenda in xsd_doc.xpath("//cfdi:Addenda", namespaces={"cfdi": ns["cfdi"]}):
        parent = addenda.getparent()
        if parent is not None:
            parent.remove(addenda)
            info["addenda_removed"] = True

    return xsd_doc, info


def _validate_xsd_cfdi(xsd_doc: etree._Element, xsd_base_path: str) -> Tuple[bool, str]:
    """Valida contra cfdv40.xsd usando resolver local."""
    try:
        parser = etree.XMLParser(no_network=True)
        parser.resolvers.add(LocalResolver(xsd_base_path))

        xsd_file = os.path.join(xsd_base_path, "cfdv40.xsd")
        if not os.path.exists(xsd_file):
            return False, f"No se encontró cfdv40.xsd en: {xsd_base_path}"

        with open(xsd_file, "rb") as f:
            schema_root = etree.XML(f.read(), parser)

        schema = etree.XMLSchema(schema_root)
        schema.assertValid(xsd_doc)
        return True, ""
    except etree.DocumentInvalid as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)


def validate_cfdi_40(xml_bytes: bytes, xsd_base_path: str) -> Dict[str, Any]:
    """
    Checklist para UI:
      - xml_ok
      - xsd_ok (CFDI 4.0)
      - timbre_ok
    Además:
      - addenda_present
      - messages (human friendly)
      - errors (técnicos)
      - timbre (dict por atributo)
    """
    report: Dict[str, Any] = {
        "xml_ok": False,
        "xsd_ok": False,
        "timbre_ok": False,
        "messages": [],
        "errors": [],
        "addenda_present": False,
        "timbre": None,
    }

    ok_xml, doc, xml_err = _parse_xml(xml_bytes)
    if not ok_xml or doc is None:
        report["errors"].append(xml_err)
        report["messages"].append("❌ XML inválido")
        return report

    report["xml_ok"] = True
    report["messages"].append("✅ XML bien formado")

    ns = {
        "cfdi": "http://www.sat.gob.mx/cfd/4",
        "tfd": "http://www.sat.gob.mx/TimbreFiscalDigital",
    }

    addenda = doc.find(".//cfdi:Addenda", namespaces=ns)
    report["addenda_present"] = addenda is not None
    if report["addenda_present"]:
        report["messages"].append("ℹ️ Addenda detectada: se excluye de la validación XSD pero se guarda completa")

    # XSD CFDI 4.0 (sin timbre y sin addenda)
    xsd_doc, _info = _strip_for_xsd(doc)
    ok_xsd, xsd_err = _validate_xsd_cfdi(xsd_doc, xsd_base_path)
    if not ok_xsd:
        report["errors"].append(xsd_err)
        report["messages"].append("❌ XSD CFDI 4.0 inválido")
        return report

    report["xsd_ok"] = True
    report["messages"].append("✅ XSD CFDI 4.0 válido")

    # TimbreFiscalDigital presente y atributos válidos
    timbre_elem = doc.find(".//cfdi:Complemento/tfd:TimbreFiscalDigital", namespaces=ns)
    if timbre_elem is None:
        report["errors"].append("No se encontró tfd:TimbreFiscalDigital en cfdi:Complemento")
        report["messages"].append("❌ TimbreFiscalDigital no encontrado")
        return report

    timbre_res = validar_timbre(timbre_elem)
    report["timbre"] = timbre_res

    if not all(v == "ok" for v in timbre_res.values()):
        bad = [f"{k}: {v}" for k, v in timbre_res.items() if v != "ok"]
        report["errors"].append("Timbre inválido -> " + ", ".join(bad))
        report["messages"].append("❌ TimbreFiscalDigital inválido")
        return report

    report["timbre_ok"] = True
    report["messages"].append("✅ TimbreFiscalDigital válido")
    return report
