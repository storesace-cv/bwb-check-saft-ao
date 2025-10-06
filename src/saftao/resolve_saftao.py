"""Compatibilidade para o ponto de entrada gráfico legado.

Este módulo serve apenas como encaminhamento para :mod:`saftao.gui`,
permitindo que imports existentes continuem a funcionar após a
reorganização do código da interface gráfica."""

from __future__ import annotations

from .gui import main

__all__ = ["main"]
