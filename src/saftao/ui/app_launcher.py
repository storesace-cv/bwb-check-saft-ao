"""Utilitários para criação da aplicação Qt partilhada.

O módulo fornece uma função ``ensure_app`` inspirada em ``ensure_ftv_app``
do projecto de referência. A função garante que os atributos globais
desejados são configurados antes da criação do ``QApplication`` e aplica
uma folha de estilos consistente que suporta widgets com fundos
transparentes.
"""

from __future__ import annotations

import sys
from typing import Sequence
from functools import lru_cache
from pathlib import Path

from importlib import util as importlib_util

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

_QT_SVG_SPEC = importlib_util.find_spec("PySide6.QtSvg")
if _QT_SVG_SPEC is not None:
    from PySide6.QtSvg import QSvgRenderer
else:  # pragma: no cover - QtSvg may be unavailable in headless tests
    QSvgRenderer = None

APP_STYLESHEET = """
* {
    font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
    font-size: 13px;
    color: #1f1f1f;
}

QMainWindow, QDialog {
    background: rgba(255, 255, 255, 230);
    border-radius: 12px;
}

QMenuBar {
    background-color: rgba(255, 255, 255, 210);
    border: none;
}

QMenu {
    background-color: rgba(255, 255, 255, 245);
    border: 1px solid rgba(31, 31, 31, 40%);
    border-radius: 6px;
}

QPushButton {
    background-color: rgba(46, 125, 229, 0.85);
    color: white;
    padding: 6px 14px;
    border-radius: 6px;
    border: none;
}

QPushButton:disabled {
    background-color: rgba(46, 125, 229, 0.35);
}

QLineEdit, QPlainTextEdit, QTextEdit, QListWidget, QTreeWidget {
    background-color: rgba(255, 255, 255, 230);
    border: 1px solid rgba(31, 31, 31, 45%);
    border-radius: 6px;
    padding: 4px 6px;
}

QLabel#splash-background {
    background: transparent;
}

QWidget#splash-overlay {
    background: transparent;
}
"""

APP_ICON_PATH = Path(__file__).resolve().parents[1] / "bwb-saft-app.svg"

__all__ = [
    "APP_STYLESHEET",
    "ensure_app",
    "set_application_stylesheet",
    "process_events",
]


def _coerce_argv(argv: Sequence[str] | None) -> list[str]:
    if argv is None:
        return list(sys.argv)
    return list(argv)


def ensure_app(argv: Sequence[str] | None = None) -> QApplication:
    """Return a shared ``QApplication`` instance configured for the GUI."""

    app = QApplication.instance()
    if app is not None:
        return app

    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
    coerced = _coerce_argv(argv)
    app = QApplication(coerced)
    app.setApplicationName("Ferramentas SAF-T (AO)")
    app.setOrganizationName("BWB")
    app.setOrganizationDomain("bwb.pt")
    app.setStyle("Fusion")
    icon = _load_app_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)
    set_application_stylesheet(app)
    return app


def set_application_stylesheet(app: QApplication) -> None:
    """Apply the global application stylesheet if not already set."""

    current = app.styleSheet() or ""
    if APP_STYLESHEET.strip() and APP_STYLESHEET not in current:
        app.setStyleSheet(APP_STYLESHEET)


def process_events(app: QApplication, *, iterations: int = 1) -> None:
    """Process pending Qt events a limited number of times."""

    for _ in range(max(1, iterations)):
        app.processEvents()


@lru_cache()
def _load_app_icon() -> QIcon:
    """Load the bundled application icon, rendering SVGs when necessary."""

    icon = QIcon(str(APP_ICON_PATH))
    if not icon.isNull():
        return icon

    if APP_ICON_PATH.suffix.lower() == ".svg" and QSvgRenderer is not None:
        renderer = QSvgRenderer(str(APP_ICON_PATH))
        if renderer.isValid():
            icon = QIcon()
            for size in (16, 24, 32, 48, 64, 128, 256, 512):
                pixmap = QPixmap(size, size)
                pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(pixmap)
                renderer.render(painter)
                painter.end()
                icon.addPixmap(pixmap)
            if not icon.isNull():
                return icon

    return QIcon()
