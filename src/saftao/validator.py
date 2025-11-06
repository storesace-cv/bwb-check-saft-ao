"""Validator entry point for SAFT AO files."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from lxml import etree

from lib.validators.rules_loader import get_rule

from .rules import (
    iter_masterfile_customers,
    iter_sales_invoices,
    iter_tax_elements,
    resolve_tax_context,
)
from .schema import load_audit_file
from .utils import detect_namespace


class ValidationIssue:
    """Representation of a problem detected during validation."""

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        details: dict[str, str] | None = None,
    ) -> None:
        self.message = message
        self.code = code or "GENERIC"
        self.details = details or {}

    def as_cells(self) -> list[str]:
        """Serialise the issue for tabular export."""

        return [self.code, self.message]


def validate_file(path: Path) -> Iterable[ValidationIssue]:
    """Validate the provided file and return the detected issues."""

    tree, _, _ = load_audit_file(path)
    return validate_tree(tree)


def validate_tree(tree: etree._ElementTree) -> list[ValidationIssue]:
    """Run the validation checks against an in-memory XML tree."""

    root = tree.getroot()
    namespace = detect_namespace(root)

    issues: list[ValidationIssue] = []

    customer_issues, valid_customers, prefixed_customers = _check_masterfile_customers(
        root, namespace
    )
    issues.extend(customer_issues)
    issues.extend(
        _check_invoice_customer_references(
            root, namespace, valid_customers, prefixed_customers
        )
    )
    issues.extend(_check_tax_registration_number(root, namespace))
    issues.extend(_check_header_building_number(root, namespace))
    issues.extend(_check_header_postal_code(root, namespace))
    issues.extend(_check_tax_country_region(root, namespace))

    return issues


def export_report(issues: Iterable[ValidationIssue], *, destination: Path) -> None:
    """Export validation issues to an Excel report."""

    from .logging import ExcelLogger, ExcelLoggerConfig

    logger = ExcelLogger(
        ExcelLoggerConfig(columns=("code", "message"), filename=str(destination))
    )
    logger.write_rows(issues)


def _check_masterfile_customers(
    root: etree._Element, namespace: str
) -> tuple[list[ValidationIssue], set[str], set[str]]:
    ns = {"n": namespace}
    masterfiles = root.find(".//n:MasterFiles", namespaces=ns)
    if masterfiles is None:
        return [], set(), set()

    issues: list[ValidationIssue] = []
    valid_ids: set[str] = set()
    prefixed_ids: set[str] = set()

    for customer in iter_masterfile_customers(root, namespace):
        customer_id = _extract_customer_id(customer, namespace)
        has_prefix = _subtree_has_prefixed_nodes(customer, namespace)
        if has_prefix:
            prefixed_ids.add(customer_id)
            issues.append(
                ValidationIssue(
                    "Customer no MasterFiles exportado com prefixo de namespace (ns:).",
                    code="CUSTOMER_WRONG_NAMESPACE",
                    details={"customer_id": customer_id},
                )
            )
        elif customer_id:
            valid_ids.add(customer_id)

    return issues, valid_ids, prefixed_ids


def _check_invoice_customer_references(
    root: etree._Element,
    namespace: str,
    valid_ids: set[str],
    prefixed_ids: set[str],
) -> list[ValidationIssue]:
    ns = {"n": namespace}
    issues: list[ValidationIssue] = []

    for invoice in iter_sales_invoices(root, namespace):
        customer_el = invoice.find("./n:CustomerID", namespaces=ns)
        if customer_el is None:
            continue
        customer_id = (customer_el.text or "").strip()
        if not customer_id or customer_id in valid_ids:
            continue

        invoice_no = _find_child_text(invoice, namespace, "InvoiceNo") or "(sem número)"
        message = (
            f"Fatura '{invoice_no}' referencia CustomerID '{customer_id}' que não existe no MasterFiles."
        )
        note = (
            "CustomerID presente no MasterFiles mas com prefixo de namespace não padrão"
            if customer_id in prefixed_ids
            else "CustomerID não encontrado"
        )
        issues.append(
            ValidationIssue(
                message,
                code="INVOICE_CUSTOMER_MISSING",
                details={
                    "invoice": invoice_no,
                    "customer_id": customer_id,
                    "note": note,
                },
            )
        )

    return issues


def _check_tax_registration_number(
    root: etree._Element, namespace: str
) -> list[ValidationIssue]:
    ns = {"n": namespace}
    header = root.find(".//n:Header", namespaces=ns)
    if header is None:
        return []

    tax_el = header.find("./n:TaxRegistrationNumber", namespaces=ns)
    if tax_el is None:
        return []

    value = (tax_el.text or "").strip()
    rule = get_rule(_RULE_TAX_REGISTRATION_DIGITS)
    # Rule agt.header.tax_registration_number.digits_only (referenced from the
    # AGT data structure circular) mandates numeric-only identifiers.
    if not value:
        return []

    digits_only = value
    if rule is None or rule.constraints.get("format") == "digits-only":
        digits_only = "".join(ch for ch in value if ch.isdigit())
        if digits_only == value:
            return []
    else:
        pattern = rule.constraints.get("pattern")
        if pattern is not None:
            import re

            if re.fullmatch(pattern, value):
                return []
        if rule.constraints.get("strip_non_digits", False):
            digits_only = "".join(ch for ch in value if ch.isdigit())

    return [
        ValidationIssue(
            "TaxRegistrationNumber deve conter apenas dígitos (sem prefixos como 'AO').",
            code="HEADER_TAX_ID_INVALID",
            details={"current_value": value, "suggested_value": digits_only},
        )
    ]


def _check_header_building_number(
    root: etree._Element, namespace: str
) -> list[ValidationIssue]:
    ns = {"n": namespace}
    header = root.find(".//n:Header", namespaces=ns)
    if header is None:
        return []

    address = header.find("./n:CompanyAddress", namespaces=ns)
    if address is None:
        return []

    element = address.find("./n:BuildingNumber", namespaces=ns)
    current = (element.text or "").strip() if element is not None else ""
    rule = get_rule(_RULE_BUILDING_NUMBER)
    # Rule agt.header.building_number.normalised defines valid placeholders and
    # rejects zero-equivalent values according to AGT technical annexes.
    if not _building_number_needs_normalisation(current, rule):
        return []

    return [
        ValidationIssue(
            "BuildingNumber deve estar preenchido com um valor válido (utilize 'S/N' quando não existe número de porta).",
            code="HEADER_BUILDING_NUMBER_INVALID",
            details={"current_value": current, "suggested_value": "S/N"},
        )
    ]


def _building_number_needs_normalisation(value: str, rule: object | None) -> bool:
    if not value:
        return True

    normalised = value.strip().upper()
    allowed_markers: set[str] = {"S/N", "SN"}
    forbidden: set[str] = {"0", "00", "000", "0000"}
    if rule is not None:
        try:
            constraints = rule.constraints  # type: ignore[attr-defined]
        except AttributeError:
            constraints = {}
        allowed_markers = {
            marker.upper() for marker in constraints.get("allowed_markers", allowed_markers)
        }
        forbidden = {
            marker.upper() for marker in constraints.get("forbidden_values", forbidden)
        }

    if normalised in allowed_markers:
        return False

    if normalised in forbidden:
        return True

    digits = "".join(ch for ch in normalised if ch.isdigit())
    if digits and int(digits or "0") == 0:
        return True

    return False


def _check_header_postal_code(
    root: etree._Element, namespace: str
) -> list[ValidationIssue]:
    ns = {"n": namespace}
    header = root.find(".//n:Header", namespaces=ns)
    if header is None:
        return []

    address = header.find("./n:CompanyAddress", namespaces=ns)
    if address is None:
        return []

    element = address.find("./n:PostalCode", namespaces=ns)
    if element is None:
        return []

    current = (element.text or "").strip()
    rule = get_rule(_RULE_POSTAL_CODE_PLACEHOLDER)
    # Rule agt.header.postal_code.placeholder ensures consistent placeholder
    # normalisation when AGT requires "0000" for missing codes.
    placeholder = "0000"
    alias = "0000-000"
    if rule is not None:
        constraints = rule.constraints
        placeholder = constraints.get("placeholder", placeholder)
        alias = constraints.get("alias", alias)

    if current.replace(" ", "") != alias:
        return []

    return [
        ValidationIssue(
            "PostalCode deve utilizar o marcador '0000' quando não existe código oficial.",
            code="HEADER_POSTAL_CODE_INVALID",
            details={"current_value": current, "suggested_value": placeholder},
        )
    ]


def _check_tax_country_region(root: etree._Element, namespace: str) -> list[ValidationIssue]:
    ns = {"n": namespace}
    issues: list[ValidationIssue] = []
    rule = get_rule(_RULE_TAX_COUNTRY_REGION_REQUIRED)
    # Rule agt.tax.country_region.required consolidates AGT VAT rules requiring
    # AO as the country/region marker for applicable transactions.
    required = True
    allowed_values: set[str] = set()
    if rule is not None:
        constraints = rule.constraints
        required = constraints.get("required", True)
        allowed_values = {value.upper() for value in constraints.get("allowed_values", [])}

    for tax in iter_tax_elements(root, namespace):
        region = tax.find(f"./{{{namespace}}}TaxCountryRegion")
        if region is not None:
            region_text = (region.text or "").strip()
            if region_text:
                if allowed_values and region_text.upper() not in allowed_values:
                    doc_type, doc_id, line_no = resolve_tax_context(tax, namespace)
                    context_parts = [doc_type]
                    if doc_id:
                        context_parts[-1] = f"{doc_type} '{doc_id}'" if doc_type else doc_id
                    if line_no:
                        context_parts.append(f"linha {line_no}")
                    context = ", ".join(part for part in context_parts if part)
                    if not context:
                        context = "Tax"
                    issues.append(
                        ValidationIssue(
                            f"TaxCountryRegion em {context} possui valor '{region_text}' fora do permitido.",
                            code="TAX_COUNTRY_REGION_INVALID",
                            details={
                                "document_type": doc_type,
                                "document_id": doc_id,
                                "line": line_no,
                                "allowed_values": sorted(allowed_values),
                                "current_value": region_text,
                            },
                        )
                    )
                continue
        if not required:
            continue

        doc_type, doc_id, line_no = resolve_tax_context(tax, namespace)
        context_parts = [doc_type]
        if doc_id:
            context_parts[-1] = f"{doc_type} '{doc_id}'" if doc_type else doc_id
        if line_no:
            context_parts.append(f"linha {line_no}")
        context = ", ".join(part for part in context_parts if part)
        if not context:
            context = "Tax"

        issues.append(
            ValidationIssue(
                f"TaxCountryRegion em {context} está em falta ou vazio.",
                code="TAX_COUNTRY_REGION_MISSING",
                details={
                    "document_type": doc_type,
                    "document_id": doc_id,
                    "line": line_no,
                },
            )
        )

    return issues


def _find_child_text(
    element: etree._Element, namespace: str, tag: str
) -> str | None:
    child = element.find(f"./{{{namespace}}}{tag}")
    if child is None:
        child = _find_child_by_localname(element, tag)
    if child is None:
        return None
    return (child.text or "").strip()


def _extract_customer_id(customer: etree._Element, namespace: str) -> str:
    node = customer.find(f"./{{{namespace}}}CustomerID")
    if node is None:
        node = _find_child_by_localname(customer, "CustomerID")
    return (node.text or "").strip() if node is not None else ""


def _subtree_has_prefixed_nodes(node: etree._Element, namespace: str) -> bool:
    for element in node.iter():
        if not element.prefix:
            continue
        if etree.QName(element).namespace != namespace:
            return True
    return False


def _find_child_by_localname(
    element: etree._Element, tag: str
) -> etree._Element | None:
    for child in element:
        if etree.QName(child).localname == tag:
            return child
    return None


__all__ = ["ValidationIssue", "validate_file", "validate_tree", "export_report"]
_RULE_TAX_REGISTRATION_DIGITS = "agt.header.tax_registration_number.digits_only"
_RULE_BUILDING_NUMBER = "agt.header.building_number.normalised"
_RULE_POSTAL_CODE_PLACEHOLDER = "agt.header.postal_code.placeholder"
_RULE_TAX_COUNTRY_REGION_REQUIRED = "agt.tax.country_region.required"

