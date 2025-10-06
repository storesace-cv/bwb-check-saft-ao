"""Invoice related helpers for SAFT AO."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable


@dataclass
class Invoice:
    """Lightweight invoice representation used by validators and fixers."""

    number: str
    customer_tax_id: str
    issue_date: date
    gross_total: Decimal
    net_total: Decimal


def load_invoices() -> Iterable[Invoice]:
    """Load invoices from the underlying SAFT AO document."""

    raise NotImplementedError("Invoice loading not yet implemented")
