"""Hard auto-fix routines for SAFT AO XML files."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ..logging import ExcelLogger, ExcelLoggerConfig
from ..validator import ValidationIssue


def apply_hard_fixes(path: Path) -> Iterable[ValidationIssue]:
    """Apply destructive corrections to the given file.

    Once the refactor is complete, this function will wrap the logic from
    ``saft_ao_autofix_hard.py`` and yield a list of applied fixes.
    """

    raise NotImplementedError("Hard auto-fixes still need to be implemented")


def log_hard_fixes(issues: Iterable[ValidationIssue], *, destination: Path) -> None:
    """Persist the hard fixes to a spreadsheet log."""

    logger = ExcelLogger(
        ExcelLoggerConfig(columns=("code", "message"), filename=str(destination))
    )
    logger.write_rows(issues)
