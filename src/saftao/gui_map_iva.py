"""Componentes Tkinter para o mapa de IVA."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

import tkinter as tk
from tkinter import ttk


@dataclass(frozen=True)
class IvaMapSectionData:
    """Informação a apresentar numa secção do mapa de IVA."""

    title: str
    columns: Sequence[str]
    rows: Sequence[Sequence[str]]

    def validate(self) -> None:
        """Garantir coerência básica entre colunas e linhas."""

        expected = len(self.columns)
        for index, row in enumerate(self.rows):
            if len(row) != expected:
                raise ValueError(
                    f"Linha {index} da secção '{self.title}' tem {len(row)} colunas; "
                    f"esperavam-se {expected}."
                )


class IvaMapSection(ttk.LabelFrame):
    """Tabela reutilizável com o formato comum às três visões."""

    def __init__(self, master: tk.Misc, data: IvaMapSectionData) -> None:
        super().__init__(master, text=data.title, padding=(12, 8))
        self._tree = ttk.Treeview(self, columns=data.columns, show="headings", height=12)
        self._configure_columns(data.columns)

        yscroll = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=yscroll.set)

        self._tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.populate(data.rows)

    def _configure_columns(self, columns: Sequence[str]) -> None:
        for column in columns:
            self._tree.heading(column, text=column)
            self._tree.column(column, anchor=tk.W, stretch=True, width=180)

    def populate(self, rows: Iterable[Sequence[str]]) -> None:
        self._tree.delete(*self._tree.get_children())
        for values in rows:
            self._tree.insert("", tk.END, values=values)


class IvaMapTab(ttk.Frame):
    """Tab do *notebook* principal responsável pelo mapa de IVA."""

    def __init__(
        self,
        master: tk.Misc,
        data_loader: Callable[[], Sequence[IvaMapSectionData]] | None = None,
    ) -> None:
        super().__init__(master)
        self._data_loader = data_loader or load_default_iva_map_data

        container = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        container.pack(fill="both", expand=True)

        sections = self._validated_sections()

        left_frame = ttk.Frame(container)
        right_pane = ttk.Panedwindow(container, orient=tk.VERTICAL)

        container.add(left_frame, weight=1)
        container.add(right_pane, weight=1)

        self._left_section = IvaMapSection(left_frame, sections[0])
        self._left_section.pack(fill="both", expand=True)

        self._right_top = IvaMapSection(right_pane, sections[1])
        self._right_bottom = IvaMapSection(right_pane, sections[2])

        right_pane.add(self._right_top, weight=1)
        right_pane.add(self._right_bottom, weight=1)

        self.bind("<Visibility>", lambda _event: self.refresh())

    def _validated_sections(self) -> Sequence[IvaMapSectionData]:
        sections = list(self._data_loader())
        if len(sections) != 3:
            raise ValueError(
                "O mapa de IVA espera exactamente três secções: "
                "Visão SAFT Fiel, Visão Excel e Análise Comparativa."
            )
        for section in sections:
            section.validate()
        return sections

    def refresh(self) -> None:
        """Recarregar dados da fonte configurada e actualizar as tabelas."""

        sections = self._validated_sections()
        self._left_section.populate(sections[0].rows)
        self._right_top.populate(sections[1].rows)
        self._right_bottom.populate(sections[2].rows)


def load_default_iva_map_data() -> Sequence[IvaMapSectionData]:
    """Dados de demonstração para o mapa de IVA."""

    common_columns = ("Indicador", "Valor", "Variação vs. mês anterior")

    return (
        IvaMapSectionData(
            title="Visão SAFT Fiel",
            columns=common_columns,
            rows=(
                ("IVA liquidado", "120 430 €", "+2,5%"),
                ("IVA dedutível", "77 980 €", "-1,1%"),
                ("Saldo do período", "42 450 €", "+4,2%"),
            ),
        ),
        IvaMapSectionData(
            title="Visão Excel",
            columns=common_columns,
            rows=(
                ("Registos conciliados", "95,2%", "+0,6 p.p."),
                ("Erros identificados", "42", "-8 unidades"),
                ("Alertas pendentes", "7", "-2 face ao mês anterior"),
            ),
        ),
        IvaMapSectionData(
            title="Análise Comparativa",
            columns=("Indicador", "SAFT", "Excel", "Diferença"),
            rows=(
                ("Total IVA liquidado", "120 430 €", "118 900 €", "+1 530 €"),
                ("Total IVA dedutível", "77 980 €", "78 250 €", "-270 €"),
                ("Saldo final", "42 450 €", "40 650 €", "+1 800 €"),
            ),
        ),
    )


__all__ = [
    "IvaMapTab",
    "IvaMapSectionData",
    "load_default_iva_map_data",
]
