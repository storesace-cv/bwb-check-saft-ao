"""Schema helpers for SAF-T (AO) documents."""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

from lxml import etree

from .utils import detect_namespace

_PACKAGE_ROOT = Path(__file__).resolve().parent
_SCHEMA_ROOT = (_PACKAGE_ROOT / ".." / ".." / "schemas").resolve()


def load_schema(name: str) -> Path:
    """Return the path to the requested schema resource."""

    path = _SCHEMA_ROOT / name
    if not path.exists():
        raise FileNotFoundError(f"Schema not found: {name}")
    return path


def load_audit_file(path: Path) -> Tuple[etree._ElementTree, etree._Element, str]:
    """Load *path* and return the parsed tree, root element and namespace."""

    tree = etree.parse(str(path))
    root = tree.getroot()
    namespace = detect_namespace(root)
    return tree, root, namespace
