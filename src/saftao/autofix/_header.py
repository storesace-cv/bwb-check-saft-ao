"""Helpers for normalising header information."""

from __future__ import annotations

from lxml import etree


def normalise_tax_registration_number(
    root: etree._Element, namespace: str
) -> tuple[bool, str, str]:
    """Strip non-digit characters from ``TaxRegistrationNumber``."""

    ns = {"n": namespace}
    header = root.find(".//n:Header", namespaces=ns)
    if header is None:
        return False, "", ""

    trn = header.find("./n:TaxRegistrationNumber", namespaces=ns)
    if trn is None:
        return False, "", ""

    current = (trn.text or "").strip()
    digits_only = "".join(ch for ch in current if ch.isdigit())
    if not digits_only or digits_only == current:
        return False, current, digits_only

    trn.text = digits_only
    return True, current, digits_only


__all__ = ["normalise_tax_registration_number"]
