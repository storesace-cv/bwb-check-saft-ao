"""Helpers for normalising header information."""

from __future__ import annotations

from lxml import etree

from lib.validators.rules_loader import get_rule

_RULE_TAX_REGISTRATION_DIGITS = "agt.header.tax_registration_number.digits_only"
_RULE_BUILDING_NUMBER = "agt.header.building_number.normalised"
_RULE_POSTAL_CODE_PLACEHOLDER = "agt.header.postal_code.placeholder"


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
    rule = get_rule(_RULE_TAX_REGISTRATION_DIGITS)
    # Rule agt.header.tax_registration_number.digits_only guides the sanitiser
    # to remove non-numeric prefixes that violate AGT requirements.
    digits_only = "".join(ch for ch in current if ch.isdigit())
    if rule is not None:
        if not rule.constraints.get("strip_non_digits", True):
            digits_only = current

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

    rule = get_rule(_RULE_BUILDING_NUMBER)
    # Rule agt.header.building_number.normalised dictates the placeholder used
    # when AGT accepts "sem número" markers.
    needs_fix = _building_number_needs_normalisation(current, rule)
    if not needs_fix:
        return False, current, current

    replacement = "S/N"
    if rule is not None:
        markers = rule.constraints.get("allowed_markers", [replacement])
        if markers:
            replacement = markers[0]

    element.text = replacement
    return True, current, replacement


def _building_number_needs_normalisation(value: str, rule: object | None) -> bool:
    if not value:
        return True

    normalised = value.strip().upper()
    allowed = {"S/N", "SN"}
    forbidden = {"0", "00", "000", "0000"}
    if rule is not None:
        try:
            constraints = rule.constraints  # type: ignore[attr-defined]
        except AttributeError:
            constraints = {}
        allowed = {marker.upper() for marker in constraints.get("allowed_markers", allowed)}
        forbidden = {marker.upper() for marker in constraints.get("forbidden_values", forbidden)}

    if normalised in allowed:
        return False

    if normalised in forbidden:
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
    rule = get_rule(_RULE_POSTAL_CODE_PLACEHOLDER)
    # Rule agt.header.postal_code.placeholder forces the canonical '0000'
    # placeholder recommended by the AGT submission guides.
    placeholder = "0000"
    alias = "0000-000"
    if rule is not None:
        constraints = rule.constraints
        placeholder = constraints.get("placeholder", placeholder)
        alias = constraints.get("alias", alias)

    normalised = current.replace(" ", "")
    if normalised != alias:
        return False, current, current

    element.text = placeholder
    return True, current, placeholder


__all__ = [
    "ensure_company_address_building_number",
    "normalise_company_postal_code",
    "normalise_tax_registration_number",
]
