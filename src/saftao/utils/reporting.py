"""Helpers to aggregate SAF-T (AO) documents and build Excel reports."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Iterable

from lxml import etree
from openpyxl import Workbook

from ..rules import iter_sales_invoices
from ..utils import parse_decimal


@dataclass
class Totals:
    """Aggregate of monetary values for a set of documents."""

    net_total: Decimal = field(default_factory=lambda: Decimal("0"))
    tax_total: Decimal = field(default_factory=lambda: Decimal("0"))
    gross_total: Decimal = field(default_factory=lambda: Decimal("0"))

    def add(self, net: Decimal, tax: Decimal, gross: Decimal) -> None:
        """Add *net*, *tax* and *gross* values to the totals."""

        self.net_total += net
        self.tax_total += tax
        self.gross_total += gross


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

    totals_by_type: dict[str, Totals]
    overall_totals: Totals
    non_accounting_documents: list[NonAccountingDocument]


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


def _iter_work_documents(root: etree._Element, namespace: str) -> Iterable[etree._Element]:
    if namespace:
        return root.findall(
            ".//n:SourceDocuments/n:WorkingDocuments/n:WorkDocument",
            namespaces={"n": namespace},
        )
    return root.findall(".//SourceDocuments/WorkingDocuments/WorkDocument")


def aggregate_documents(root: etree._Element, namespace: str) -> ReportData:
    """Aggregate accounting and non-accounting documents from *root*."""

    totals_by_type: dict[str, Totals] = {}
    overall = Totals()

    for invoice in iter_sales_invoices(root, namespace):
        invoice_type = _find_child_text(invoice, namespace, "InvoiceType") or "DESCONHECIDO"
        document_totals = _extract_document_totals(invoice, namespace)

        if invoice_type not in totals_by_type:
            totals_by_type[invoice_type] = Totals()
        totals_by_type[invoice_type].add(
            document_totals.net_total,
            document_totals.tax_total,
            document_totals.gross_total,
        )
        overall.add(
            document_totals.net_total,
            document_totals.tax_total,
            document_totals.gross_total,
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
        totals_by_type=totals_by_type,
        overall_totals=overall,
        non_accounting_documents=non_accounting,
    )


def write_excel_report(data: ReportData, destination: Path) -> None:
    """Generate an Excel workbook with accounting totals and other documents."""

    destination.parent.mkdir(parents=True, exist_ok=True)

    workbook = Workbook()
    summary_ws = workbook.active
    summary_ws.title = "Resumo"
    summary_ws.append(["Tipo", "Total sem IVA", "IVA", "Total com IVA"])

    for doc_type in sorted(data.totals_by_type):
        totals = data.totals_by_type[doc_type]
        summary_ws.append(
            [
                doc_type,
                totals.net_total,
                totals.tax_total,
                totals.gross_total,
            ]
        )

    summary_ws.append([])
    summary_ws.append(
        [
            "Totais Gerais",
            data.overall_totals.net_total,
            data.overall_totals.tax_total,
            data.overall_totals.gross_total,
        ]
    )

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
