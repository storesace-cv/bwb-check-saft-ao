"""Runtime loader for AGT SAF-T (AO) validation and auto-fix rules."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


_INDEX_ENV_VAR = "AGT_RULES_INDEX_PATH"
_DEFAULT_INDEX_PATH = Path(__file__).resolve().parents[2] / "rules_updates" / "agt" / "index.json"


class RulesLoaderError(RuntimeError):
    """Raised when the rules index cannot be parsed."""


@dataclass(frozen=True)
class DocumentReference:
    """Pointer to the original AGT source that defines a rule."""

    filename: str
    pages: tuple[int, ...] | None = None


@dataclass(frozen=True)
class Rule:
    """Machine-usable SAF-T (AO) rule loaded from ``index.json``."""

    rule_id: str
    scope: str
    semantics: str
    constraints: dict[str, Any]
    applies_since: str | None
    applies_until: str | None
    precedence: int | None
    source_doc_refs: tuple[DocumentReference, ...]


@dataclass(frozen=True)
class Document:
    """Metadata describing an AGT source document."""

    source_path: str
    filename: str
    filesize: int
    hash_sha256: str
    title: str
    doc_date: str | None
    date_confidence: str
    version: str | None
    type: str | None
    entities: tuple[str, ...]
    abstract: str
    uncertainty_level: str | None


@dataclass(frozen=True)
class RulesIndex:
    """Structured representation of ``rules_updates/agt/index.json``."""

    generated_at: str
    schema_version: str
    documents: tuple[Document, ...]
    rules: tuple[Rule, ...]

    def find_rule(self, rule_id: str) -> Rule | None:
        """Return the rule with ``rule_id`` if present."""

        return next((rule for rule in self.rules if rule.rule_id == rule_id), None)

    def iter_scope(self, scope: str) -> Iterable[Rule]:
        """Yield every rule whose ``scope`` matches the provided value."""

        return (rule for rule in self.rules if rule.scope == scope)


_CACHED_INDEX: tuple[Path, float, RulesIndex] | None = None


def _resolve_index_path() -> Path:
    candidate = os.getenv(_INDEX_ENV_VAR)
    if candidate:
        return Path(candidate)
    return _DEFAULT_INDEX_PATH


def _load_index_from_disk(path: Path) -> RulesIndex:
    if not path.exists():
        msg = f"Rules index '{path}' not found"
        raise RulesLoaderError(msg)

    with path.open("r", encoding="utf-8") as handle:
        try:
            payload = json.load(handle)
        except json.JSONDecodeError as exc:
            msg = f"Rules index '{path}' is not valid JSON"
            raise RulesLoaderError(msg) from exc

    try:
        generated_at = payload["generated_at"]
        schema_version = payload["schema_version"]
        raw_documents = payload["documents"]
        raw_rules = payload["rules"]
    except KeyError as exc:
        msg = "Rules index is missing required keys"
        raise RulesLoaderError(msg) from exc

    documents = []
    for item in raw_documents:
        documents.append(
            Document(
                source_path=item["source_path"],
                filename=item["filename"],
                filesize=int(item["filesize"]),
                hash_sha256=item["hash_sha256"],
                title=item["title"],
                doc_date=item.get("doc_date"),
                date_confidence=item.get("date_confidence", "unknown"),
                version=item.get("version"),
                type=item.get("type"),
                entities=tuple(item.get("entities", [])),
                abstract=item.get("abstract", ""),
                uncertainty_level=item.get("uncertainty_level"),
            )
        )

    rules = []
    for item in raw_rules:
        references = []
        for ref in item.get("source_doc_refs", []):
            pages = tuple(ref.get("pages", [])) or None
            references.append(
                DocumentReference(
                    filename=ref["filename"],
                    pages=pages,
                )
            )
        rules.append(
            Rule(
                rule_id=item["rule_id"],
                scope=item["scope"],
                semantics=item["semantics"],
                constraints=dict(item.get("constraints", {})),
                applies_since=item.get("applies_since"),
                applies_until=item.get("applies_until"),
                precedence=item.get("precedence"),
                source_doc_refs=tuple(references),
            )
        )

    return RulesIndex(
        generated_at=generated_at,
        schema_version=schema_version,
        documents=tuple(documents),
        rules=tuple(rules),
    )


def load_rules_index(force_reload: bool = False) -> RulesIndex:
    """Load ``rules_updates/agt/index.json`` with caching."""

    global _CACHED_INDEX

    index_path = _resolve_index_path()
    mtime = index_path.stat().st_mtime if index_path.exists() else 0.0

    if not force_reload and _CACHED_INDEX:
        cached_path, cached_mtime, cached_index = _CACHED_INDEX
        if cached_path == index_path and cached_mtime == mtime:
            return cached_index

    index = _load_index_from_disk(index_path)
    _CACHED_INDEX = (index_path, mtime, index)
    return index


def get_rule(rule_id: str) -> Rule | None:
    """Return the rule with ``rule_id`` from the cached index."""

    index = load_rules_index()
    return index.find_rule(rule_id)


def iter_rules(scope: str | None = None) -> Iterable[Rule]:
    """Iterate over rules optionally filtered by ``scope``."""

    index = load_rules_index()
    if scope is None:
        return index.rules
    return index.iter_scope(scope)


__all__ = [
    "Document",
    "DocumentReference",
    "Rule",
    "RulesIndex",
    "RulesLoaderError",
    "get_rule",
    "iter_rules",
    "load_rules_index",
]
