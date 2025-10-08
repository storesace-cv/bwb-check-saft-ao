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


def _clone_with_namespace(node: etree._Element, namespace: str) -> etree._Element:
    """Clone ``node`` ensuring every tag belongs to the default namespace."""

    qname = etree.QName(node)
    cloned = etree.Element(f"{{{namespace}}}{qname.localname}")
    cloned.text = node.text
    cloned.tail = node.tail

    for attr_name, value in node.attrib.items():
        attr_qname = etree.QName(attr_name)
        if attr_qname.namespace:
            cloned.attrib[f"{{{attr_qname.namespace}}}{attr_qname.localname}"] = value
        else:
            cloned.attrib[attr_qname.localname] = value

    for child in node:
        cloned.append(_clone_with_namespace(child, namespace))

    return cloned


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
            customer_id_el = customer.find("./*[local-name()='CustomerID']")
        customer_id = (customer_id_el.text or "").strip() if customer_id_el is not None else ""

        parent = customer.getparent()
        if parent is None:
            continue

        replacement = _clone_with_namespace(customer, namespace)
        index = parent.index(customer)
        parent.remove(customer)
        parent.insert(index, replacement)
        changed = True

        if on_fix is not None:
            on_fix(customer_id)

    if changed:
        etree.cleanup_namespaces(root)

    return changed


__all__ = ["normalise_customer_namespace"]
