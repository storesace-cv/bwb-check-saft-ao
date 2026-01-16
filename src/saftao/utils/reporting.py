"""Helpers to aggregate SAF-T (AO) documents and build Excel reports."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Iterable

from lxml import etree
from openpyxl import Workbook

from ..rules import iter_sales_invoices
from ..utils import parse_decimal

REPORT_OUTPUT_ENV = "SAFTAO_REPORT_DIR"
DEFAULT_REPORT_DIR = Path(__file__).resolve().parents[3] / "work" / "destino" / "relatorios"


@dataclass
class Totals:
    """Aggregate of monetary values for a set of documents."""

    net_total: Decimal = field(default_factory=lambda: Decimal("0"))
    tax_total: Decimal = field(default_factory=lambda: Decimal("0"))
    gross_total: Decimal = field(default_factory=lambda: Decimal("0"))
    tax_by_rate: dict[str, Decimal] = field(default_factory=dict)

    def add(
        self,
        net: Decimal,
        tax: Decimal,
        gross: Decimal,
        tax_by_rate: dict[str, Decimal] | None = None,
    ) -> None:
        """Add *net*, *tax* and *gross* values to the totals."""

        self.net_total += net
        self.tax_total += tax
        self.gross_total += gross
        if tax_by_rate:
            for rate, amount in tax_by_rate.items():
                self.tax_by_rate[rate] = self.tax_by_rate.get(rate, Decimal("0")) + amount


@dataclass
class NonAccountingDocument:
    """Representation of a document that does not count towards totals."""

    document_type: str
    document_number: str
    document_date: str
    customer_id: str
    totals: Totals


@dataclass
class ReportData:
    """Container for the aggregated data extracted from a SAF-T file."""

    totals_by_month: dict[str, dict[str, Totals]]
    totals_by_type: dict[str, Totals]
    month_overall_totals: dict[str, Totals]
    overall_totals: Totals
    non_accounting_documents: list[NonAccountingDocument]
    tax_rates: list[str]


def resolve_report_directory() -> Path:
    """Return the base directory for generated totals reports."""

    override = os.environ.get(REPORT_OUTPUT_ENV)
    if override:
        return Path(override).expanduser()
    return DEFAULT_REPORT_DIR


def default_report_destination(
    saft_path: Path | None, *, base_dir: Path | None = None
) -> Path:
    """Return the default Excel path for a totals report."""

    directory = base_dir or resolve_report_directory()
    if saft_path is None:
        stem = "relatorio_totais"
    else:
        stem = saft_path.stem or "relatorio_totais"
    destination = directory / f"{stem}_totais.xlsx"
    return destination


def _find_child(element: etree._Element, namespace: str, localname: str) -> etree._Element | None:
    if namespace:
        node = element.find(f"./{{{namespace}}}{localname}")
        if node is not None:
            return node
    for child in element:
        if etree.QName(child).localname == localname:
            return child
    return None


def _find_child_text(element: etree._Element, namespace: str, localname: str) -> str:
    node = _find_child(element, namespace, localname)
    if node is None or node.text is None:
        return ""
    return node.text.strip()


def _extract_document_totals(element: etree._Element, namespace: str) -> Totals:
    totals_node = _find_child(element, namespace, "DocumentTotals")
    if totals_node is None:
        return Totals()

    net = parse_decimal(_find_child_text(totals_node, namespace, "NetTotal"))
    tax = parse_decimal(_find_child_text(totals_node, namespace, "TaxPayable"))
    gross = parse_decimal(_find_child_text(totals_node, namespace, "GrossTotal"))

    totals = Totals()
    totals.add(net, tax, gross)
    return totals


def _format_tax_rate_label(rate: str) -> str:
    if rate == "ND":
        return "IVA-ND"
    return f"IVA-{rate}%"


def _extract_tax_by_rate(element: etree._Element, namespace: str) -> dict[str, Decimal]:
    if namespace:
        tax_nodes = element.xpath(".//n:Tax", namespaces={"n": namespace})
    else:
        tax_nodes = element.findall(".//Tax")
    totals: dict[str, Decimal] = {}
    for tax_node in tax_nodes:
        percentage_text = _find_child_text(tax_node, namespace, "TaxPercentage")
        tax_amount = parse_decimal(_find_child_text(tax_node, namespace, "TaxAmount"))
        if percentage_text:
            rate_key = percentage_text
        else:
            rate_key = "ND" if tax_amount != 0 else "0"
        label = _format_tax_rate_label(rate_key)
        totals[label] = totals.get(label, Decimal("0")) + tax_amount
    return totals


def _resolve_invoice_month(element: etree._Element, namespace: str) -> str:
    date_text = _find_child_text(element, namespace, "InvoiceDate") or ""
    if len(date_text) >= 7 and date_text[4] == "-":
        return date_text[:7]
    return date_text or "Desconhecido"


def _tax_rate_sort_key(label: str) -> tuple[int, Decimal | str]:
    if label == "IVA-ND":
        return (1, "ND")
    value = label.removeprefix("IVA-").removesuffix("%")
    try:
        return (0, Decimal(value))
    except Exception:
        return (1, value)


def _iter_work_documents(root: etree._Element, namespace: str) -> Iterable[etree._Element]:
    if namespace:
        return root.findall(
            ".//n:SourceDocuments/n:WorkingDocuments/n:WorkDocument",
            namespaces={"n": namespace},
        )
    return root.findall(".//SourceDocuments/WorkingDocuments/WorkDocument")


def aggregate_documents(root: etree._Element, namespace: str) -> ReportData:
    """Aggregate accounting and non-accounting documents from *root*."""

    totals_by_month: dict[str, dict[str, Totals]] = {}
    totals_by_type: dict[str, Totals] = {}
    month_overall_totals: dict[str, Totals] = {}
    overall = Totals()
    tax_rates: set[str] = set()

    for invoice in iter_sales_invoices(root, namespace):
        invoice_type = _find_child_text(invoice, namespace, "InvoiceType") or "DESCONHECIDO"
        document_totals = _extract_document_totals(invoice, namespace)
        tax_by_rate = _extract_tax_by_rate(invoice, namespace)
        month = _resolve_invoice_month(invoice, namespace)
        tax_rates.update(tax_by_rate.keys())

        if invoice_type not in totals_by_type:
            totals_by_type[invoice_type] = Totals()
        totals_by_type[invoice_type].add(
            document_totals.net_total,
            document_totals.tax_total,
            document_totals.gross_total,
            tax_by_rate,
        )
        overall.add(
            document_totals.net_total,
            document_totals.tax_total,
            document_totals.gross_total,
            tax_by_rate,
        )

        month_totals = totals_by_month.setdefault(month, {})
        if invoice_type not in month_totals:
            month_totals[invoice_type] = Totals()
        month_totals[invoice_type].add(
            document_totals.net_total,
            document_totals.tax_total,
            document_totals.gross_total,
            tax_by_rate,
        )
        month_overall = month_overall_totals.setdefault(month, Totals())
        month_overall.add(
            document_totals.net_total,
            document_totals.tax_total,
            document_totals.gross_total,
            tax_by_rate,
        )

    non_accounting: list[NonAccountingDocument] = []
    for work_document in _iter_work_documents(root, namespace):
        doc_type = _find_child_text(work_document, namespace, "DocumentType") or "DESCONHECIDO"
        doc_number = _find_child_text(work_document, namespace, "DocumentNumber")
        doc_date = _find_child_text(work_document, namespace, "WorkDate")
        customer = _find_child_text(work_document, namespace, "CustomerID")
        totals = _extract_document_totals(work_document, namespace)
        non_accounting.append(
            NonAccountingDocument(
                document_type=doc_type,
                document_number=doc_number,
                document_date=doc_date,
                customer_id=customer,
                totals=totals,
            )
        )

    return ReportData(
        totals_by_month=totals_by_month,
        totals_by_type=totals_by_type,
        month_overall_totals=month_overall_totals,
        overall_totals=overall,
        non_accounting_documents=non_accounting,
        tax_rates=sorted(tax_rates, key=_tax_rate_sort_key),
    )


def write_excel_report(data: ReportData, destination: Path) -> None:
    """Generate an Excel workbook with accounting totals and other documents."""

    destination.parent.mkdir(parents=True, exist_ok=True)

    workbook = Workbook()
    summary_ws = workbook.active
    summary_ws.title = "Resumo"
    tax_columns = data.tax_rates
    header = ["Tipo", "Total sem IVA", *tax_columns, "Total com IVA"]

    def append_totals_row(label: str, totals: Totals) -> None:
        summary_ws.append(
            [
                label,
                totals.net_total,
                *[totals.tax_by_rate.get(rate, Decimal("0")) for rate in tax_columns],
                totals.gross_total,
            ]
        )

    months = sorted(data.totals_by_month)
    if len(months) > 1:
        for month in months:
            summary_ws.append([f"Mês: {month}"])
            summary_ws.append(header)
            for doc_type in sorted(data.totals_by_month[month]):
                append_totals_row(doc_type, data.totals_by_month[month][doc_type])
            append_totals_row(f"Subtotal {month}", data.month_overall_totals[month])
            summary_ws.append([])
        append_totals_row("Totais Gerais", data.overall_totals)
    else:
        summary_ws.append(header)
        for doc_type in sorted(data.totals_by_type):
            append_totals_row(doc_type, data.totals_by_type[doc_type])
        summary_ws.append([])
        append_totals_row("Totais Gerais", data.overall_totals)

    other_ws = workbook.create_sheet(title="Documentos não contabilísticos")
    other_ws.append(
        [
            "Tipo",
            "Número",
            "Data",
            "Cliente",
            "Total sem IVA",
            "IVA",
            "Total com IVA",
        ]
    )

    for document in data.non_accounting_documents:
        other_ws.append(
            [
                document.document_type,
                document.document_number,
                document.document_date,
                document.customer_id,
                document.totals.net_total,
                document.totals.tax_total,
                document.totals.gross_total,
            ]
        )

    workbook.save(destination)
