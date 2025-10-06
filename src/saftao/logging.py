"""Shared logging helpers for SAFT AO utilities.

The goal of this module is to consolidate the different ``ExcelLogger``
implementations that exist today in the root-level scripts.  The future
implementation should expose reusable helpers for generating spreadsheet
summaries as well as plain-text logs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol


class RowLike(Protocol):
    """Protocol describing a row serialisable to tabular outputs."""

    def as_cells(self) -> Iterable[str]:
        """Return the ordered cell values for the row."""


@dataclass
class ExcelLoggerConfig:
    """Configuration placeholder for the shared Excel logging utility."""

    columns: Iterable[str]
    filename: str = "saft-ao-report.xlsx"


class ExcelLogger:
    """Stubbed logger that will replace the ad-hoc Excel writers.

    The real implementation should accept rows conforming to :class:`RowLike`
    and serialise them to the configured output format.
    """

    def __init__(self, config: ExcelLoggerConfig) -> None:
        self.config = config

    def write_rows(self, rows: Iterable[RowLike]) -> None:
        """Persist the provided rows to the configured destination.

        The method is currently a stub and will be implemented once the
        refactor migrates the legacy scripts into this package.
        """

        raise NotImplementedError("Excel logging still needs to be implemented")
