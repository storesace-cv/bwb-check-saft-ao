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
        self._tree = ttk.Treeview(self, columns=data.columns, show="headings", height=10)
        self._configure_columns(data.columns)

        yscroll = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=yscroll.set)

        self._tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.populate(data.rows)

    def _configure_columns(self, columns: Sequence[str]) -> None:
        for index, column in enumerate(columns):
            self._tree.heading(column, text=column)
            anchor = tk.W if index < 2 else tk.E
            if index == 0:
                width = 110
            elif index == 1:
                width = 130
            else:
                width = 120
            self._tree.column(column, anchor=anchor, stretch=True, width=width)

    def populate(self, rows: Iterable[Sequence[str]]) -> None:
        self._tree.delete(*self._tree.get_children())
        for values in rows:
            self._tree.insert("", tk.END, values=values)

    def update_from_data(self, data: IvaMapSectionData) -> None:
        if tuple(self._tree["columns"]) != tuple(data.columns):
            self._tree.configure(columns=data.columns)
            self._configure_columns(data.columns)
        self.configure(text=data.title)
        self.populate(data.rows)


class IvaMapTab(ttk.Frame):
    """Tab do *notebook* principal responsável pelo mapa de IVA."""

    def __init__(
        self,
        master: tk.Misc,
        data_loader: Callable[[], Sequence[IvaMapSectionData]] | None = None,
    ) -> None:
        super().__init__(master)
        self._data_loader = data_loader or load_default_iva_map_data

        container = ttk.Panedwindow(self, orient=tk.VERTICAL)
        container.pack(fill="both", expand=True)

        sections = self._validated_sections()

        self._section_widgets: list[IvaMapSection] = []
        for section in sections:
            widget = IvaMapSection(container, section)
            container.add(widget, weight=1)
            self._section_widgets.append(widget)

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
        for widget, data in zip(self._section_widgets, sections):
            widget.update_from_data(data)


def load_default_iva_map_data() -> Sequence[IvaMapSectionData]:
    """Dados de demonstração para o mapa de IVA."""

    common_columns = ("TipoDoc", "TaxCode", "Tax%", "Q.Linhas", "Base", "IVA")

    return (
        IvaMapSectionData(
            title="Visão SAFT Fiel",
            columns=common_columns,
            rows=(
                ("FT", "NOR", "17%", "12", "45 230,15", "7 689,13"),
                ("NC", "INT", "14%", "6", "3 980,00", "557,20"),
                ("FR", "ISE", "0%", "3", "780,00", "0,00"),
                ("ND", "ISE", "0%", "2", "240,50", "0,00"),
            ),
        ),
        IvaMapSectionData(
            title="Visão Excel",
            columns=common_columns,
            rows=(
                ("FT", "NOR", "17%", "10", "42 780,00", "7 272,60"),
                ("NC", "INT", "14%", "4", "2 840,00", "397,60"),
                ("FR", "ISE", "0%", "5", "1 050,00", "0,00"),
                ("ND", "ISE", "0%", "1", "125,00", "0,00"),
            ),
        ),
        IvaMapSectionData(
            title="Análise Comparativa",
            columns=common_columns,
            rows=(
                ("FT", "NOR", "17%", "+2", "+2 450,15", "+416,53"),
                ("NC", "INT", "14%", "+2", "+1 140,00", "+159,60"),
                ("FR", "ISE", "0%", "-2", "-270,00", "0,00"),
                ("ND", "ISE", "0%", "+1", "+115,50", "0,00"),
            ),
        ),
    )


__all__ = [
    "IvaMapTab",
    "IvaMapSectionData",
    "load_default_iva_map_data",
]
