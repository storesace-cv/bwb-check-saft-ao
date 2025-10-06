"""Validator entry point for SAFT AO files.

This module will eventually house the refactored logic currently present in
``validator_saft_ao.py``.  For now, it provides stub classes and functions
that define the intended public surface.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .logging import ExcelLogger, ExcelLoggerConfig


class ValidationIssue:
    """Placeholder representation of a problem detected during validation."""

    def __init__(self, message: str, *, code: str | None = None) -> None:
        self.message = message
        self.code = code or "GENERIC"

    def as_cells(self) -> list[str]:
        """Serialise the issue for tabular export."""

        return [self.code, self.message]


def validate_file(path: Path) -> Iterable[ValidationIssue]:
    """Validate the provided file.

    The implementation is pending the migration of the existing validator
    script into the package structure.
    """

    raise NotImplementedError("Validator logic not yet ported to the package")


def export_report(issues: Iterable[ValidationIssue], *, destination: Path) -> None:
    """Export validation issues to an Excel report.

    This helper demonstrates how the shared logger will be used once the
    underlying logic is refactored.
    """

    logger = ExcelLogger(
        ExcelLoggerConfig(columns=("code", "message"), filename=str(destination))
    )
    logger.write_rows(issues)
