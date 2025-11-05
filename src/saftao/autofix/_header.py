"""Helpers for normalising header information."""

from __future__ import annotations

from lxml import etree


def _find_header(root: etree._Element, namespace: str) -> etree._Element | None:
    ns = {"n": namespace}
    return root.find(".//n:Header", namespaces=ns)


def _find_company_address(
    header: etree._Element, namespace: str
) -> etree._Element | None:
    ns = {"n": namespace}
    return header.find("./n:CompanyAddress", namespaces=ns)


def normalise_tax_registration_number(
    root: etree._Element, namespace: str
) -> tuple[bool, str, str]:
    """Strip non-digit characters from ``TaxRegistrationNumber``."""

    header = _find_header(root, namespace)
    if header is None:
        return False, "", ""

    ns = {"n": namespace}
    trn = header.find("./n:TaxRegistrationNumber", namespaces=ns)
    if trn is None:
        return False, "", ""

    current = (trn.text or "").strip()
    digits_only = "".join(ch for ch in current if ch.isdigit())
    if not digits_only or digits_only == current:
        return False, current, digits_only

    trn.text = digits_only
    return True, current, digits_only


def ensure_company_address_building_number(
    root: etree._Element, namespace: str
) -> tuple[bool, str, str]:
    """Ensure ``BuildingNumber`` is set to an accepted value.

    If the original value is missing or resolves to ``0`` (frequently usado
    como marcador para "sem número"), substitui-se por ``"S/N"`` para cumprir
    com o formato aceite pela autoridade tributária.
    """

    header = _find_header(root, namespace)
    if header is None:
        return False, "", ""

    address = _find_company_address(header, namespace)
    if address is None:
        return False, "", ""

    ns = {"n": namespace}
    element = address.find("./n:BuildingNumber", namespaces=ns)
    if element is None:
        element = etree.SubElement(address, f"{{{namespace}}}BuildingNumber")
        current = ""
    else:
        current = (element.text or "").strip()

    needs_fix = _building_number_needs_normalisation(current)
    if not needs_fix:
        return False, current, current

    element.text = "S/N"
    return True, current, "S/N"


def _building_number_needs_normalisation(value: str) -> bool:
    if not value:
        return True

    normalised = value.strip().upper()
    if normalised in {"S/N", "SN"}:
        return False

    if normalised in {"0", "00", "000", "0000"}:
        return True

    digits = "".join(ch for ch in normalised if ch.isdigit())
    if digits and int(digits or "0") == 0:
        return True

    return False


def normalise_company_postal_code(
    root: etree._Element, namespace: str
) -> tuple[bool, str, str]:
    """Normalise ``PostalCode`` when using the ``0000-000`` placeholder."""

    header = _find_header(root, namespace)
    if header is None:
        return False, "", ""

    address = _find_company_address(header, namespace)
    if address is None:
        return False, "", ""

    ns = {"n": namespace}
    element = address.find("./n:PostalCode", namespaces=ns)
    if element is None:
        return False, "", ""

    current = (element.text or "").strip()
    normalised = current.replace(" ", "")
    if normalised != "0000-000":
        return False, current, current

    element.text = "0000"
    return True, current, "0000"


__all__ = [
    "ensure_company_address_building_number",
    "normalise_company_postal_code",
    "normalise_tax_registration_number",
]
