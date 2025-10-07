"""Pequenas utilidades para compatibilidade Qt usadas no lançamento da GUI."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog

__all__ = ["exec_modal"]


def exec_modal(dialog: QDialog) -> int:
    """Execute um diálogo de forma modal compatível com PySide6."""

    dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
    return dialog.exec()
