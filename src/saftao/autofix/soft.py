"""Soft auto-fix routines for SAFT AO XML files."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ..logging import ExcelLogger, ExcelLoggerConfig
from ..validator import ValidationIssue


def apply_soft_fixes(path: Path) -> Iterable[ValidationIssue]:
    """Apply non-destructive corrections to the given file.

    The intent is to migrate the behaviours from ``saft_ao_autofix_soft.py``
    into this module, exposing a clean function that yields issues which were
    auto-resolved.  The stub raises :class:`NotImplementedError` until that
    work happens.
    """

    raise NotImplementedError("Soft auto-fixes still need to be implemented")


def normalize_invoice_type_vd(path: Path) -> Iterable[ValidationIssue]:
    """Placeholder for converting ``InvoiceType="VD"`` into ``"FR"`` entries."""

    raise NotImplementedError(
        "Normalização de InvoiceType 'VD' ainda não foi implementada"
    )


def ensure_invoice_customers_exported(path: Path) -> Iterable[ValidationIssue]:
    """Ensure every customer referenced by an invoice is present in MasterFiles."""

    raise NotImplementedError(
        "Verificação de clientes exportados ainda não foi implementada"
    )


def log_soft_fixes(issues: Iterable[ValidationIssue], *, destination: Path) -> None:
    """Persist the soft fixes to a spreadsheet log."""

    logger = ExcelLogger(
        ExcelLoggerConfig(columns=("code", "message"), filename=str(destination))
    )
    logger.write_rows(issues)
