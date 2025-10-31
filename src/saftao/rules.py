"""Shared structural helpers for SAF-T (AO) validation and auto-fixes."""

from __future__ import annotations

from typing import Iterable, Iterator, List

from lxml import etree


def _namespace_map(namespace: str) -> dict[str, str] | None:
    """Return the namespace mapping for XPath lookups."""

    if namespace:
        return {"n": namespace}
    return None


def _findall(root: etree._Element, path: str, namespace: str) -> List[etree._Element]:
    ns_map = _namespace_map(namespace)
    if ns_map:
        return root.findall(path, namespaces=ns_map)  # type: ignore[arg-type]
    # When no namespace is present we fall back to a plain lookup without the
    # ``n:`` prefixes used in our XPath expressions.
    plain = path.replace("n:", "")
    return root.findall(plain)


def iter_masterfile_customers(
    root: etree._Element, namespace: str
) -> Iterator[etree._Element]:
    """Yield the ``Customer`` elements defined under ``MasterFiles``."""

    ns_map = _namespace_map(namespace)
    masterfiles = root.find(".//n:MasterFiles", namespaces=ns_map)
    if masterfiles is None:
        return iter(())
    return iter(
        masterfiles.findall(f"./{{{namespace}}}Customer")
        if namespace
        else masterfiles.findall("./Customer")
    )


def collect_masterfile_customer_ids(root: etree._Element, namespace: str) -> set[str]:
    """Return the set of ``CustomerID`` values present in ``MasterFiles``."""

    ids: set[str] = set()
    for customer in iter_masterfile_customers(root, namespace):
        node = customer.find(f"./{{{namespace}}}CustomerID") if namespace else None
        if node is None:
            node = _find_child_by_localname(customer, "CustomerID")
        text = (node.text or "").strip() if node is not None else ""
        if text:
            ids.add(text)
    return ids


def _collect_unique_customer_ids(
    root: etree._Element, namespace: str, xpath: str
) -> list[str]:
    """Collect distinct ``CustomerID`` values in document order for ``xpath``."""

    nodes = _findall(root, xpath, namespace)

    ordered: list[str] = []
    seen: set[str] = set()
    for node in nodes:
        text = (node.text or "").strip()
        if not text or text in seen:
            continue
        ordered.append(text)
        seen.add(text)
    return ordered


def collect_invoice_customer_ids(root: etree._Element, namespace: str) -> list[str]:
    """Return the ordered list of ``CustomerID`` values used in invoices."""

    return _collect_unique_customer_ids(
        root,
        namespace,
        ".//n:SourceDocuments/n:SalesInvoices/n:Invoice//n:CustomerID",
    )


def collect_workdocument_customer_ids(root: etree._Element, namespace: str) -> list[str]:
    """Return the ordered ``CustomerID`` values used in work documents."""

    return _collect_unique_customer_ids(
        root,
        namespace,
        ".//n:SourceDocuments/n:WorkingDocuments/n:WorkDocument//n:CustomerID",
    )


def collect_payment_customer_ids(root: etree._Element, namespace: str) -> list[str]:
    """Return the ordered ``CustomerID`` values used in payments."""

    return _collect_unique_customer_ids(
        root,
        namespace,
        ".//n:SourceDocuments/n:Payments/n:Payment//n:CustomerID",
    )


def iter_sales_invoices(root: etree._Element, namespace: str) -> Iterator[etree._Element]:
    """Yield every ``Invoice`` node under ``SourceDocuments``."""

    return iter(
        _findall(root, ".//n:SourceDocuments/n:SalesInvoices/n:Invoice", namespace)
    )


def iter_tax_elements(root: etree._Element, namespace: str) -> Iterable[etree._Element]:
    """Yield the ``Tax`` blocks under ``SourceDocuments``."""

    ns_map = _namespace_map(namespace)
    if ns_map:
        return root.xpath(
            ".//n:SourceDocuments//*[local-name()='Tax']",
            namespaces=ns_map,
        )
    return root.findall(".//SourceDocuments//*[local-name()='Tax']")


def resolve_tax_context(
    tax: etree._Element, namespace: str
) -> tuple[str, str, str]:
    """Determine the document context for a ``Tax`` node."""

    line = tax.getparent()
    line_no = ""
    if line is not None:
        node = line.find(f"./{{{namespace}}}LineNumber") if namespace else None
        if node is None:
            node = _find_child_by_localname(line, "LineNumber")
        if node is not None:
            line_no = (node.text or "").strip()

    parent = line.getparent() if line is not None else None
    while parent is not None:
        local = etree.QName(parent).localname
        if local == "Invoice":
            ident = _find_child_text(parent, namespace, "InvoiceNo")
            return local, ident or "", line_no
        if local == "Payment":
            ident = _find_child_text(parent, namespace, "PaymentRefNo")
            return local, ident or "", line_no
        if local == "WorkDocument":
            ident = _find_child_text(parent, namespace, "DocumentNumber")
            return local, ident or "", line_no
        parent = parent.getparent()

    return "", "", line_no


def _find_child_text(
    element: etree._Element, namespace: str, tag: str
) -> str | None:
    node = element.find(f"./{{{namespace}}}{tag}") if namespace else None
    if node is None:
        node = _find_child_by_localname(element, tag)
    if node is None:
        return None
    return (node.text or "").strip()


def _find_child_by_localname(
    element: etree._Element, tag: str
) -> etree._Element | None:
    for child in element:
        if etree.QName(child).localname == tag:
            return child
    return None


__all__ = [
    "collect_invoice_customer_ids",
    "collect_masterfile_customer_ids",
    "collect_payment_customer_ids",
    "collect_workdocument_customer_ids",
    "iter_masterfile_customers",
    "iter_sales_invoices",
    "iter_tax_elements",
    "resolve_tax_context",
]
