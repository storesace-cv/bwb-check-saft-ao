"""Namespace normalisation utilities for MasterFiles customers."""

from __future__ import annotations

from typing import Callable

from lxml import etree


def _subtree_has_prefixed_nodes(node: etree._Element, namespace: str) -> bool:
    """Return ``True`` if any element in ``node`` uses a prefixed tag."""

    for element in node.iter():
        qname = etree.QName(element)
        if qname.namespace == namespace and element.prefix:
            return True
    return False


def _normalise_node_namespace(node: etree._Element, namespace: str) -> None:
    """Rewrite ``node`` so that it belongs to the default namespace."""

    qname = etree.QName(node)
    if qname.namespace != namespace or node.prefix:
        node.tag = f"{{{namespace}}}{qname.localname}"

    if node.attrib:
        updated: dict[str, str] = {}
        to_remove: list[str] = []
        for attr_name, value in node.attrib.items():
            attr_qname = etree.QName(attr_name)
            if not attr_qname.prefix:
                continue
            to_remove.append(attr_name)
            if attr_qname.namespace:
                updated[f"{{{attr_qname.namespace}}}{attr_qname.localname}"] = value
            else:
                updated[attr_qname.localname] = value
        for name in to_remove:
            del node.attrib[name]
        node.attrib.update(updated)

    for child in node:
        _normalise_node_namespace(child, namespace)


def normalise_customer_namespace(
    root: etree._Element, namespace: str, *, on_fix: Callable[[str], None] | None = None
) -> bool:
    """Rewrite ``Customer`` blocks so that they use the default namespace."""

    ns = {"n": namespace}
    masterfiles = root.find(".//n:MasterFiles", namespaces=ns)
    if masterfiles is None:
        return False

    changed = False
    customers = masterfiles.findall(f"./{{{namespace}}}Customer")
    for customer in customers:
        if not _subtree_has_prefixed_nodes(customer, namespace):
            continue

        customer_id_el = customer.find(f"./{{{namespace}}}CustomerID")
        if customer_id_el is None:
            customer_id_el = _find_child_by_localname(customer, "CustomerID")
        customer_id = (customer_id_el.text or "").strip() if customer_id_el is not None else ""

        parent = customer.getparent()
        if parent is None:
            continue

        _normalise_node_namespace(customer, namespace)
        changed = True

        if on_fix is not None:
            on_fix(customer_id)

    if changed:
        etree.cleanup_namespaces(root)

    return changed


def _find_child_by_localname(
    element: etree._Element, tag: str
) -> etree._Element | None:
    for child in element:
        if etree.QName(child).localname == tag:
            return child
    return None


__all__ = ["normalise_customer_namespace"]
