"""Utility helpers shared across SAFT AO modules."""

from __future__ import annotations

from decimal import Decimal
from xml.etree.ElementTree import Element

NS_DEFAULT = "urn:saftao:PT"


def detect_namespace(root: Element) -> str:
    """Return the XML namespace detected for the document root.

    The final implementation should replicate the behaviour of the helper
    functions present in the legacy scripts.
    """

    raise NotImplementedError("Namespace detection has not been implemented")


def parse_decimal(value: str) -> Decimal:
    """Convert the provided value to :class:`~decimal.Decimal`.

    This stub exists to highlight the shared need for robust decimal parsing
    across validator and autofix modules.
    """

    raise NotImplementedError("Decimal parsing helper still needs to be implemented")
