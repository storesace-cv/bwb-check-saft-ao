"""Utility helpers shared across SAFT AO modules."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from xml.etree.ElementTree import Element

NS_DEFAULT = "urn:OECD:StandardAuditFile-Tax:AO_1.01_01"


def detect_namespace(root: Element) -> str:
    """Return the XML namespace detected for the document root."""

    tag = getattr(root, "tag", "")
    if isinstance(tag, str) and tag.startswith("{") and "}" in tag:
        return tag.split("}", 1)[0][1:]
    return NS_DEFAULT


def parse_decimal(value: str | Decimal | None, *, default: Decimal = Decimal("0")) -> Decimal:
    """Convert the provided value to :class:`~decimal.Decimal`.

    Strings vazias ou valores inválidos devolvem o ``default`` fornecido, de
    forma idêntica aos scripts *legacy*.
    """

    if value is None:
        return default
    if isinstance(value, Decimal):
        return value

    text = str(value).strip()
    if not text:
        return default

    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return default


__all__ = ["NS_DEFAULT", "detect_namespace", "parse_decimal"]
