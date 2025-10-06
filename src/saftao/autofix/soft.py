"""Soft auto-fix routines for SAFT AO XML files."""

from __future__ import annotations

import os
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from lxml import etree

from ..logging import ExcelLogger, ExcelLoggerConfig
from ..validator import ValidationIssue

_EXCEL_ENV_VARIABLE = "BWB_SAFTAO_CUSTOMER_FILE"
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_ADDONS_DIR = _REPO_ROOT / "work" / "origem" / "addons"


@dataclass
class _CustomerRecord:
    """Representa os dados mínimos necessários para criar um cliente."""

    customer_id: str
    company_name: str
    tax_id: str
    city: str
    country: str
    telephone: str
    source_path: Path


def apply_soft_fixes(path: Path) -> Iterable[ValidationIssue]:
    """Apply non-destructive corrections to the given file.

    The intent is to migrate the behaviours from ``saft_ao_autofix_soft.py``
    into this module, exposing a clean function that yields issues which were
    auto-resolved.  The stub raises :class:`NotImplementedError` until that
    work happens.
    """

    raise NotImplementedError("Soft auto-fixes still need to be implemented")


def normalize_invoice_type_vd(path: Path) -> Iterable[ValidationIssue]:
    """Placeholder for converting ``InvoiceType="VD"`` into ``"FR"`` entries."""

    raise NotImplementedError(
        "Normalização de InvoiceType 'VD' ainda não foi implementada"
    )


def ensure_invoice_customers_exported(path: Path) -> Iterable[ValidationIssue]:
    """Ensure every customer referenced by an invoice is present in MasterFiles.

    Esta rotina detecta clientes utilizados nas facturas que ainda não estejam
    presentes no bloco ``MasterFiles/Customer`` do ficheiro SAF-T. Caso sejam
    identificadas ausências, o utilizador é solicitado a indicar o ficheiro
    Excel com a tabela de clientes (padrão ``work/origem/addons``). Os registos
    em falta são adicionados automaticamente ao XML.
    """

    tree = etree.parse(str(path))
    root = tree.getroot()
    ns_uri = _detect_namespace(root)
    namespaces = {"n": ns_uri} if ns_uri else None

    invoice_ids = _collect_invoice_customer_ids(root, namespaces)
    existing_ids = _collect_masterfile_customer_ids(root, namespaces)

    missing_ids = [cid for cid in invoice_ids if cid not in existing_ids]
    if not missing_ids:
        return []

    records = _gather_customer_records(missing_ids)

    masterfiles = _ensure_masterfiles_node(root, ns_uri)

    issues: list[ValidationIssue] = []
    for customer_id in missing_ids:
        record = records[customer_id]
        _append_customer(masterfiles, ns_uri, record)
        issues.append(
            ValidationIssue(
                f"Cliente '{customer_id}' adicionado ao MasterFiles com dados de "
                f"'{record.source_path.name}'.",
                code="AUTOADD_CUSTOMER",
            )
        )

    tree.write(str(path), encoding="utf-8", xml_declaration=True, pretty_print=True)
    return issues


def log_soft_fixes(issues: Iterable[ValidationIssue], *, destination: Path) -> None:
    """Persist the soft fixes to a spreadsheet log."""

    logger = ExcelLogger(
        ExcelLoggerConfig(columns=("code", "message"), filename=str(destination))
    )
    logger.write_rows(issues)


def _detect_namespace(root: etree._Element) -> str:
    tag = root.tag
    if tag.startswith("{") and "}" in tag:
        return tag.split("}", 1)[0][1:]
    return ""


def _collect_invoice_customer_ids(
    root: etree._Element, namespaces: dict[str, str] | None
) -> list[str]:
    if namespaces:
        xpath = ".//n:SourceDocuments/n:SalesInvoices/n:Invoice//n:CustomerID"
        nodes = root.xpath(xpath, namespaces=namespaces)
    else:
        nodes = root.findall(
            ".//SourceDocuments/SalesInvoices/Invoice//CustomerID"
        )

    ordered: list[str] = []
    seen: set[str] = set()
    for node in nodes:
        text = (node.text or "").strip()
        if not text or text in seen:
            continue
        ordered.append(text)
        seen.add(text)
    return ordered


def _collect_masterfile_customer_ids(
    root: etree._Element, namespaces: dict[str, str] | None
) -> set[str]:
    if namespaces:
        xpath = ".//n:MasterFiles/n:Customer/n:CustomerID"
        nodes = root.xpath(xpath, namespaces=namespaces)
    else:
        nodes = root.findall(".//MasterFiles/Customer/CustomerID")

    ids: set[str] = set()
    for node in nodes:
        text = (node.text or "").strip()
        if text:
            ids.add(text)
    return ids


def _gather_customer_records(missing_ids: list[str]) -> dict[str, _CustomerRecord]:
    env_path = os.environ.get(_EXCEL_ENV_VARIABLE)
    if env_path:
        excel_path = Path(env_path).expanduser()
        if not excel_path.exists():
            raise FileNotFoundError(
                f"O ficheiro Excel definido em {_EXCEL_ENV_VARIABLE} não existe: {excel_path}"
            )
        records = _load_records_from_excel(excel_path)
        result: dict[str, _CustomerRecord] = {}
        missing_from_file: list[str] = []
        for customer_id in missing_ids:
            data = records.get(customer_id)
            if data is None:
                missing_from_file.append(customer_id)
                continue
            result[customer_id] = _CustomerRecord(**data, source_path=excel_path)
        if missing_from_file:
            missing_str = ", ".join(missing_from_file)
            raise ValueError(
                "Os seguintes clientes em falta não foram encontrados no ficheiro "
                f"{excel_path}: {missing_str}"
            )
        return result

    return _gather_records_interactively(missing_ids)


def _gather_records_interactively(
    missing_ids: list[str],
) -> dict[str, _CustomerRecord]:
    from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

    _DEFAULT_ADDONS_DIR.mkdir(parents=True, exist_ok=True)

    app = QApplication.instance()
    created_app = False
    if app is None:
        app = QApplication([])
        created_app = True

    try:
        _show_message(
            QMessageBox.Icon.Warning,
            "Clientes em falta no MasterFiles",
            "Foram detectados clientes nas facturas que não existem no MasterFiles.",
            QMessageBox.StandardButton.Ok,
            (
                "Os seguintes identificadores precisam de ser adicionados:\n- "
                + "\n- ".join(missing_ids)
                + "\n\nSeleccione o ficheiro Excel com a tabela de clientes (por defeito: "
                f"{_DEFAULT_ADDONS_DIR})."
            ),
        )

        pending = list(missing_ids)
        collected: dict[str, _CustomerRecord] = {}

        while pending:
            file_path, _ = QFileDialog.getOpenFileName(
                None,
                "Selecionar ficheiro Excel com clientes",
                str(_DEFAULT_ADDONS_DIR),
                "Ficheiros Excel (*.xlsx *.xlsm *.xltx *.xltm);;Todos os ficheiros (*)",
            )
            if not file_path:
                raise RuntimeError(
                    "Operação cancelada pelo utilizador; clientes em falta continuam por registar."
                )

            excel_path = Path(file_path).expanduser()
            try:
                records = _load_records_from_excel(excel_path)
            except Exception as exc:  # pragma: no cover - interface interativa
                _show_message(
                    QMessageBox.Icon.Critical,
                    "Erro ao ler ficheiro Excel",
                    str(exc),
                    QMessageBox.StandardButton.Ok,
                )
                continue

            found: list[str] = []
            for customer_id in pending:
                data = records.get(customer_id)
                if not data:
                    continue
                collected[customer_id] = _CustomerRecord(
                    **data, source_path=excel_path
                )
                found.append(customer_id)

            if not found:
                _show_message(
                    QMessageBox.Icon.Warning,
                    "Clientes não encontrados",
                    (
                        "O ficheiro seleccionado não contém nenhum dos clientes em falta. "
                        "Confirme que escolheu a tabela correcta."
                    ),
                    QMessageBox.StandardButton.Ok,
                )
                continue

            pending = [cid for cid in pending if cid not in collected]
            if pending:
                _show_message(
                    QMessageBox.Icon.Information,
                    "Clientes adicionais em falta",
                    (
                        "Ainda faltam os seguintes clientes:\n- "
                        + "\n- ".join(pending)
                        + "\nSeleccione outro ficheiro, se necessário."
                    ),
                    QMessageBox.StandardButton.Ok,
                )

        return collected
    finally:
        if created_app:
            app.quit()


def _show_message(
    icon: "QMessageBox.Icon",
    title: str,
    text: str,
    buttons: "QMessageBox.StandardButton",
    informative_text: str | None = None,
) -> None:
    from PySide6.QtWidgets import QMessageBox

    box = QMessageBox()
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(text)
    if informative_text:
        box.setInformativeText(informative_text)
    box.setStandardButtons(buttons)
    box.exec()


def _load_records_from_excel(path: Path) -> dict[str, dict[str, str]]:
    from openpyxl import load_workbook

    if not path.exists():
        raise FileNotFoundError(f"Ficheiro Excel não encontrado: {path}")

    workbook = load_workbook(path, read_only=True, data_only=True)
    sheet = workbook.active

    rows = list(sheet.iter_rows(values_only=True))
    workbook.close()
    if not rows:
        raise ValueError("O ficheiro Excel não contém dados.")

    header = rows[0]
    column_map = _build_column_map(header)

    records: dict[str, dict[str, str]] = {}
    for row in rows[1:]:
        if row is None:
            continue
        customer_id = _normalise_excel_value(
            _value_at(row, column_map["codigo"])
        )
        if not customer_id:
            continue
        records[customer_id] = {
            "customer_id": customer_id,
            "company_name": _normalise_excel_value(
                _value_at(row, column_map["nome"])
            ),
            "tax_id": _normalise_excel_value(
                _value_at(row, column_map["contribuinte"])
            ),
            "city": _normalise_excel_value(
                _value_at(row, column_map["localidade"])
            ),
            "country": _normalise_excel_value(
                _value_at(row, column_map["pais"])
            )
            or "AO",
            "telephone": _normalise_excel_value(
                _value_at(row, column_map["telemovel"])
            ),
        }

    if not records:
        raise ValueError(
            "Nenhum registo de cliente válido foi encontrado no ficheiro Excel."
        )
    return records


def _build_column_map(header: tuple[object, ...]) -> dict[str, int]:
    required = {
        "codigo": "Código",
        "nome": "Nome",
        "contribuinte": "Contribuinte",
        "localidade": "Localidade",
        "pais": "País",
        "telemovel": "Telemovel",
    }

    mapping: dict[str, int] = {}
    for index, value in enumerate(header):
        key = _normalise_header(value)
        if key in required and key not in mapping:
            mapping[key] = index

    missing = [orig for key, orig in required.items() if key not in mapping]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(
            "O ficheiro Excel não contém todas as colunas obrigatórias: "
            f"{joined}."
        )
    return mapping


def _normalise_header(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    normalised = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalised if not unicodedata.combining(ch))


def _normalise_excel_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:g}"
    return str(value).strip()


def _value_at(row: tuple[object, ...], index: int) -> object:
    if index >= len(row):
        return None
    return row[index]


def _ensure_masterfiles_node(root: etree._Element, ns_uri: str) -> etree._Element:
    tag = _ns_tag("MasterFiles", ns_uri)
    masterfiles = root.find(f".//{tag}")
    if masterfiles is not None:
        return masterfiles

    masterfiles = etree.Element(tag)

    source_tag = _ns_tag("SourceDocuments", ns_uri)
    for index, child in enumerate(root):
        if child.tag == source_tag:
            root.insert(index, masterfiles)
            break
    else:
        root.append(masterfiles)
    return masterfiles


def _append_customer(
    masterfiles: etree._Element, ns_uri: str, record: _CustomerRecord
) -> None:
    customer = etree.SubElement(masterfiles, _ns_tag("Customer", ns_uri))

    def add_element(parent: etree._Element, name: str, text: str) -> etree._Element:
        element = etree.SubElement(parent, _ns_tag(name, ns_uri))
        element.text = text
        return element

    add_element(customer, "CustomerID", record.customer_id)
    add_element(customer, "AccountID", record.customer_id)
    add_element(customer, "CustomerTaxID", record.tax_id or "999999990")
    add_element(customer, "CompanyName", record.company_name or record.customer_id)

    billing = etree.SubElement(customer, _ns_tag("BillingAddress", ns_uri))
    add_element(billing, "AddressDetail", record.company_name or "Morada não fornecida")
    add_element(billing, "City", record.city or "Desconhecida")
    if record.country:
        add_element(billing, "Country", record.country)
    else:
        add_element(billing, "Country", "AO")

    if record.telephone:
        add_element(customer, "Telephone", record.telephone)

    add_element(customer, "SelfBillingIndicator", "0")


def _ns_tag(name: str, ns_uri: str) -> str:
    return f"{{{ns_uri}}}{name}" if ns_uri else name
