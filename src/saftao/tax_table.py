"""Tax table data structures and helpers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable


@dataclass
class TaxEntry:
    """Representation of a tax table entry."""

    code: str
    description: str
    rate: Decimal


def load_tax_table() -> Iterable[TaxEntry]:
    """Load tax entries from a SAFT AO source.

    The concrete implementation will parse XML nodes and reuse utilities from
    :mod:`saftao.utils` once the refactor takes place.
    """

    raise NotImplementedError("Tax table loader not yet implemented")
