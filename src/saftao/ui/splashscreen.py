"""Implementação do *splash screen* transparente para a aplicação GUI."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

__all__ = ["SPLASH_IMAGE_PATH", "SplashScreen"]

SPLASH_IMAGE_PATH = Path(__file__).with_name("bwb-Splash.png")


class SplashScreen(QDialog):
    """Splash screen transparente inspirado na implementação do FTV."""

    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")
        self.setFixedSize(800, 500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._background_label = QLabel()
        self._background_label.setObjectName("splash-background")
        self._background_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._background_label.setStyleSheet("background: transparent;")
        layout.addWidget(self._background_label)

        pixmap = QPixmap(str(SPLASH_IMAGE_PATH))
        if pixmap.isNull():
            self._background_label.setText("Ferramentas SAF-T (AO)")
        else:
            self._background_label.setPixmap(pixmap)

        self._overlay = QWidget(self)
        self._overlay.setObjectName("splash-overlay")
        self._overlay.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._overlay.installEventFilter(self)

        overlay_layout = QVBoxLayout(self._overlay)
        overlay_layout.setContentsMargins(32, 32, 32, 32)
        overlay_layout.addStretch()

        self._message_label = QLabel()
        self._message_label.setWordWrap(True)
        self._message_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        self._message_label.setStyleSheet(
            "color: white;"
            "background-color: rgba(32, 32, 32, 150);"
            "padding: 12px;"
            "border-radius: 6px;"
        )
        self._message_label.hide()
        overlay_layout.addWidget(
            self._message_label, alignment=Qt.AlignmentFlag.AlignLeft
        )

        self._button_container = QWidget()
        button_layout = QHBoxLayout(self._button_container)
        button_layout.setContentsMargins(0, 12, 0, 0)
        button_layout.addStretch()
        self._button_container.hide()
        overlay_layout.addWidget(
            self._button_container, alignment=Qt.AlignmentFlag.AlignLeft
        )

        self._overlay.raise_()
        self._overlay.setGeometry(self.rect())

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._overlay.setGeometry(self.rect())

    def eventFilter(self, obj, event):  # type: ignore[override]
        if obj is self._overlay and event.type() == QEvent.Type.MouseButtonPress:
            self._handle_click(event)
            return True
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self._handle_click(event)
        super().mousePressEvent(event)

    def _handle_click(self, event: Optional[QMouseEvent]) -> None:
        if event and event.button() != Qt.MouseButton.LeftButton:
            return
        self.clicked.emit()
        self.accept()

    def show_message(self, message: str | None) -> None:
        """Mostrar ou ocultar uma mensagem sobreposta no splash."""

        if message:
            self._message_label.setText(message)
            self._message_label.show()
        else:
            self._message_label.hide()

    def add_button_box(self, widget: QWidget) -> None:
        """Adicionar um conjunto de botões ao overlay do splash."""

        widget.setParent(self._button_container)
        widget.show()
        layout = self._button_container.layout()
        assert isinstance(layout, QHBoxLayout)
        layout.addWidget(widget)
        self._button_container.show()

    def overlay(self, widget: QWidget) -> None:
        """Adicionar um widget arbitrário ao overlay inferior."""

        widget.setParent(self._overlay)
        widget.show()
        layout = self._overlay.layout()
        assert isinstance(layout, QVBoxLayout)
        layout.addWidget(widget, alignment=Qt.AlignmentFlag.AlignLeft)
