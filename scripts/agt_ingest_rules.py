"""Ingest AGT source documents into the SAF-T (AO) rules index."""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import io
import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Sequence

from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams
from pdfminer.pdfdocument import PDFTextExtractionNotAllowed
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfparser import PDFSyntaxError
from pdfminer.psparser import PSEOF
from docx import Document as DocxDocument

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIR = REPO_ROOT / "rules_updates" / "agt"
DEFAULT_INDEX_PATH = DEFAULT_SOURCE_DIR / "index.json"
SUMMARY_PATH = REPO_ROOT / "docs" / "en" / "agt" / "agt_rules_summary.md"
CHANGELOG_PATH = REPO_ROOT / "docs" / "en" / "agt" / "agt_rules_changelog.md"
SCHEMA_VERSION = "1.0.0"


logger = logging.getLogger("agt_ingest_rules")


@dataclass(slots=True)
class DocumentContent:
    """Normalised textual representation of a document."""

    text: str
    pages: list[str]

    def iter_lower_pages(self) -> Iterator[str]:
        for page in self.pages:
            yield page.lower()


@dataclass(slots=True)
class DocumentMetadata:
    source_path: str
    filename: str
    filesize: int
    hash_sha256: str
    title: str
    doc_date: str | None
    date_confidence: str
    version: str | None
    type: str | None
    entities: list[str]
    abstract: str
    uncertainty_level: str | None


@dataclass(slots=True)
class RulePattern:
    rule_id: str
    scope: str
    semantics: str
    constraints: dict[str, Any]
    keywords: tuple[str, ...] = ()
    precedence: int = 0
    fallback_filenames: tuple[str, ...] = ()
    search_terms: tuple[str, ...] = ()


RULE_PATTERNS: tuple[RulePattern, ...] = (
    RulePattern(
        rule_id="agt.header.tax_registration_number.digits_only",
        scope="header.tax_registration_number",
        semantics="TaxRegistrationNumber deve conter apenas dígitos (sem prefixos ou espaços).",
        constraints={
            "format": "digits-only",
            "pattern": r"^[0-9]+$",
            "strip_non_digits": True,
        },
        keywords=("taxregistrationnumber",),
        search_terms=("taxregistrationnumber",),
        precedence=10,
    ),
    RulePattern(
        rule_id="agt.header.building_number.normalised",
        scope="header.company_address.building_number",
        semantics="BuildingNumber deve utilizar marcadores 'S/N' quando não existe número físico e rejeitar zeros.",
        constraints={
            "allowed_markers": ["S/N", "SN"],
            "forbidden_values": ["0", "00", "000", "0000"],
        },
        keywords=(),
        search_terms=("building number", "buildingnumber"),
        fallback_filenames=(
            "ds-120.especificacao.tecnica.fe.v1.0.pdf",
            "ds-120 especificação técnica consulta de contribuinte - consultar (produtores de software) v5.0.1.pdf",
            "estrutura_de_dados_de_software_modelo_de_facturação_electrónica.pdf",
            "estrutura de dados de software modelo de facturação electrónica especificações técnicas e procedimenta.pdf",
            "minfin055809.pdf",
        ),
        precedence=8,
    ),
    RulePattern(
        rule_id="agt.header.postal_code.placeholder",
        scope="header.company_address.postal_code",
        semantics="PostalCode deve ser reduzido para '0000' quando o valor presente for '0000-000'.",
        constraints={
            "placeholder": "0000",
            "alias": "0000-000",
        },
        keywords=(),
        search_terms=("postalcode", "0000-000"),
        fallback_filenames=(
            "ds-120.especificacao.tecnica.fe.v1.0.pdf",
            "ds-120 especificação técnica consulta de contribuinte - consultar (produtores de software) v5.0.1.pdf",
            "estrutura_de_dados_de_software_modelo_de_facturação_electrónica.pdf",
            "estrutura de dados de software modelo de facturação electrónica especificações técnicas e procedimenta.pdf",
            "minfin055809.pdf",
        ),
        precedence=8,
    ),
    RulePattern(
        rule_id="agt.tax.country_region.required",
        scope="tax.country_region",
        semantics="TaxCountryRegion é obrigatório e deve usar o código 'AO' quando aplicável.",
        constraints={
            "required": True,
            "allowed_values": ["AO"],
        },
        keywords=("taxcountryregion",),
        search_terms=("taxcountryregion", "região", "regiao"),
        precedence=6,
    ),
)


MONTHS_PT = {
    "janeiro": 1,
    "fevereiro": 2,
    "março": 3,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}


def sha256sum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover_documents(source_dir: Path) -> list[Path]:
    docs: list[Path] = []
    for entry in sorted(source_dir.iterdir()):
        if entry.name.startswith("."):
            continue
        if entry.is_dir():
            continue
        if entry.name.lower() == "index.json":
            continue
        if entry.suffix.lower() not in {".pdf", ".docx", ".md", ".txt"}:
            continue
        docs.append(entry)
    return docs


def extract_pdf(path: Path) -> DocumentContent:
    output_stream = io.StringIO()
    laparams = LAParams()
    resource_manager = PDFResourceManager()
    try:
        with path.open("rb") as handle:
            extract_text_to_fp(
                handle,
                output_stream,
                codec="utf-8",
                laparams=laparams,
                output_type="text",
                rsrcmgr=resource_manager,
            )
    except (PDFSyntaxError, PDFTextExtractionNotAllowed, PSEOF) as exc:
        raise RuntimeError(f"Unable to read PDF '{path}': {exc}") from exc

    raw_text = output_stream.getvalue()
    pages = [page.strip() for page in raw_text.split("\f") if page.strip()]
    text = "\n".join(pages)
    return DocumentContent(text=text, pages=pages)


def extract_docx(path: Path) -> DocumentContent:
    document = DocxDocument(path)
    paragraphs = [para.text for para in document.paragraphs if para.text.strip()]
    text = "\n".join(paragraphs)
    return DocumentContent(text=text, pages=[text])


def extract_text_document(path: Path) -> DocumentContent:
    text = path.read_text(encoding="utf-8", errors="ignore")
    cleaned = text.replace("\r\n", "\n")
    pages = [chunk.strip() for chunk in cleaned.split("\f") if chunk.strip()]
    if not pages:
        pages = [cleaned.strip()]
    return DocumentContent(text="\n".join(pages), pages=pages)


def extract_content(path: Path) -> DocumentContent:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf(path)
    if suffix == ".docx":
        return extract_docx(path)
    return extract_text_document(path)


def derive_title(content: DocumentContent, filename: str) -> str:
    for line in content.text.splitlines():
        cleaned = line.strip()
        if cleaned:
            return cleaned[:160]
    return Path(filename).stem.replace("_", " ")


def parse_date_fragment(fragment: str) -> datetime | None:
    fragment = fragment.strip()
    # Formats like YYYY-MM-DD
    match = re.search(r"(20\d{2})[-_/](\d{1,2})[-_/](\d{1,2})", fragment)
    if match:
        year, month, day = map(int, match.groups())
        return datetime(year, month, day)

    # Formats like DD/MM/YYYY
    match = re.search(r"(\d{1,2})[\-/](\d{1,2})[\-/](20\d{2})", fragment)
    if match:
        day, month, year = map(int, match.groups())
        return datetime(year, month, day)

    # Formats like 10 de Março de 2024
    match = re.search(
        r"(\d{1,2})\s+de\s+([A-Za-zçÇéÉ]+)\s+de\s+(20\d{2})",
        fragment,
        flags=re.IGNORECASE,
    )
    if match:
        day = int(match.group(1))
        month_name = match.group(2).lower()
        year = int(match.group(3))
        month = MONTHS_PT.get(month_name)
        if month:
            return datetime(year, month, day)
    return None


def derive_doc_date(content: DocumentContent, filename: str) -> tuple[str | None, str]:
    candidates: list[datetime] = []
    file_match = re.search(r"(20\d{2})[-_/](\d{1,2})[-_/](\d{1,2})", filename)
    if file_match:
        year, month, day = map(int, file_match.groups())
        candidates.append(datetime(year, month, day))

    for line in content.text.splitlines()[:50]:
        candidate = parse_date_fragment(line)
        if candidate:
            candidates.append(candidate)

    if not candidates:
        return None, "low"

    selected = min(candidates)
    return selected.strftime("%Y-%m-%d"), ("high" if file_match else "medium")


def derive_version(content: DocumentContent) -> str | None:
    match = re.search(r"(\d{1,3}/AGT/20\d{2})", content.text, flags=re.IGNORECASE)
    if match:
        return match.group(1).upper()
    match = re.search(r"(DS-\d{2,3}(?:\.\d+)?)", content.text, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def derive_type(filename: str, content: DocumentContent) -> str | None:
    tokens = [filename.lower(), content.text.lower()[:500]]
    for token in tokens:
        if "circular" in token:
            return "circular"
        if "despacho" in token or "desp." in token:
            return "despacho"
        if "decreto" in token:
            return "decreto"
        if "guia" in token:
            return "guia"
        if "manual" in token:
            return "manual"
    return None


def derive_entities(content: DocumentContent) -> list[str]:
    entities: set[str] = set()
    text_lower = content.text.lower()
    if "agt" in text_lower:
        entities.add("AGT")
    if "saf-t" in text_lower or "saft" in text_lower:
        entities.add("SAF-T (AO)")
    if "civa" in text_lower:
        entities.add("CIVA")
    if "iva" in text_lower:
        entities.add("IVA")
    if "software" in text_lower:
        entities.add("Software")
    return sorted(entities)


def derive_abstract(content: DocumentContent) -> str:
    paragraphs = [paragraph.strip() for paragraph in content.text.split("\n\n") if paragraph.strip()]
    if not paragraphs:
        paragraphs = [line.strip() for line in content.text.splitlines() if line.strip()]
    abstract = "\n\n".join(paragraphs[:2])
    return abstract[:600]


def make_metadata(path: Path, content: DocumentContent, repo_root: Path) -> DocumentMetadata:
    relative_path = str(path.relative_to(repo_root))
    hash_value = sha256sum(path)
    doc_date, confidence = derive_doc_date(content, path.name)
    metadata = DocumentMetadata(
        source_path=relative_path,
        filename=path.name,
        filesize=path.stat().st_size,
        hash_sha256=hash_value,
        title=derive_title(content, path.name),
        doc_date=doc_date,
        date_confidence=confidence,
        version=derive_version(content),
        type=derive_type(path.name, content),
        entities=derive_entities(content),
        abstract=derive_abstract(content),
        uncertainty_level=None if doc_date else "high",
    )
    return metadata


def find_rule_pages(content: DocumentContent, keywords: Sequence[str]) -> list[int]:
    matches: list[int] = []
    lowered_keywords = [keyword.lower() for keyword in keywords]
    for index, page in enumerate(content.iter_lower_pages(), start=1):
        if all(keyword in page for keyword in lowered_keywords):
            matches.append(index)
    return matches


def serialise_metadata(metadata: DocumentMetadata) -> dict[str, Any]:
    payload = dataclasses.asdict(metadata)
    payload["entities"] = sorted(metadata.entities)
    return payload


def load_existing_index(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def summarise_constraints(constraints: dict[str, Any]) -> str:
    parts = []
    for key, value in constraints.items():
        if isinstance(value, (list, tuple)):
            joined = ", ".join(map(str, value))
            parts.append(f"{key}: [{joined}]")
        else:
            parts.append(f"{key}: {value}")
    return "; ".join(parts)


def update_summary(index_data: dict[str, Any], summary_path: Path) -> None:
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# AGT SAF-T (AO) rules summary", ""]
    lines.append(f"_Last generated: {index_data['generated_at']}_")
    lines.append("")

    lines.append("## Documents")
    lines.append("")
    lines.append("| Title | Type | Date | Version | Entities | Source |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for document in index_data["documents"]:
        entities = ", ".join(document.get("entities", []))
        lines.append(
            "| {title} | {type} | {date} | {version} | {entities} | `{source}` |".format(
                title=document.get("title", ""),
                type=document.get("type") or "-",
                date=document.get("doc_date") or "-",
                version=document.get("version") or "-",
                entities=entities or "-",
                source=document.get("source_path"),
            )
        )
    lines.append("")

    lines.append("## Rules")
    lines.append("")
    lines.append("| Rule ID | Scope | Applies Since | Description | Constraints | Sources |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for rule in index_data["rules"]:
        sources = []
        for ref in rule.get("source_doc_refs", []):
            pages = ref.get("pages")
            if pages:
                page_segment = ", ".join(str(page) for page in pages)
                sources.append(f"{ref['filename']} (p. {page_segment})")
            else:
                sources.append(ref["filename"])
        lines.append(
            "| {rule_id} | {scope} | {since} | {semantics} | {constraints} | {sources} |".format(
                rule_id=rule["rule_id"],
                scope=rule["scope"],
                since=rule.get("applies_since") or "-",
                semantics=rule["semantics"],
                constraints=summarise_constraints(rule.get("constraints", {})) or "-",
                sources="; ".join(sources) or "-",
            )
        )

    lines.append("")
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


RULE_IMPACTS = {
    "agt.header.tax_registration_number.digits_only": [
        "src/saftao/validator.py",
        "src/saftao/autofix/_header.py",
    ],
    "agt.header.building_number.normalised": [
        "src/saftao/validator.py",
        "src/saftao/autofix/_header.py",
    ],
    "agt.header.postal_code.placeholder": [
        "src/saftao/validator.py",
        "src/saftao/autofix/_header.py",
    ],
    "agt.tax.country_region.required": [
        "src/saftao/validator.py",
    ],
}


def update_changelog(
    previous: dict[str, Any] | None,
    current: dict[str, Any],
    changelog_path: Path,
) -> None:
    changelog_path.parent.mkdir(parents=True, exist_ok=True)
    if previous is None:
        header = "# AGT rules changelog\n\n"
        if not changelog_path.exists():
            changelog_path.write_text(header, encoding="utf-8")
        previous = {"documents": [], "rules": []}

    previous_docs = {doc["hash_sha256"]: doc for doc in previous.get("documents", [])}
    current_docs = {doc["hash_sha256"]: doc for doc in current.get("documents", [])}

    previous_rules = {rule["rule_id"]: rule for rule in previous.get("rules", [])}
    current_rules = {rule["rule_id"]: rule for rule in current.get("rules", [])}

    added_docs = [doc for digest, doc in current_docs.items() if digest not in previous_docs]
    added_rules = [
        rule for rule_id, rule in current_rules.items() if rule_id not in previous_rules
    ]
    updated_rules = []
    for rule_id, rule in current_rules.items():
        if rule_id in previous_rules and rule != previous_rules[rule_id]:
            updated_rules.append(rule)

    if not added_docs and not added_rules and not updated_rules:
        return

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entry_lines = [f"## {timestamp} – Automated ingestion", ""]

    if added_docs:
        entry_lines.append("- **Documents added:** " + ", ".join(doc["filename"] for doc in added_docs))
    if added_rules:
        entry_lines.append("- **Rules added:** " + ", ".join(rule["rule_id"] for rule in added_rules))
    if updated_rules:
        entry_lines.append(
            "- **Rules updated:** " + ", ".join(rule["rule_id"] for rule in updated_rules)
        )

    impacted_modules: set[str] = set()
    for rule in [*added_rules, *updated_rules]:
        for module in RULE_IMPACTS.get(rule["rule_id"], []):
            impacted_modules.add(module)

    if impacted_modules:
        entry_lines.append(
            "- **Impacted modules:** " + ", ".join(sorted(impacted_modules))
        )

    entry_lines.append(
        "- **Recommended actions:** Re-run `python scripts/agt_ingest_rules.py --rebuild` and ensure validators consume the refreshed constraints."
    )
    entry_lines.append("")

    digest_source = "|".join(entry_lines)
    digest = hashlib.sha256(digest_source.encode("utf-8")).hexdigest()
    entry_lines.append(f"<!-- digest:{digest} -->")
    entry_lines.append("")

    existing = changelog_path.read_text(encoding="utf-8") if changelog_path.exists() else ""
    if f"digest:{digest}" in existing:
        return

    with changelog_path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(entry_lines))


def build_rules(
    metadata: DocumentMetadata,
    content: DocumentContent,
    existing_rules: dict[str, dict[str, Any]],
) -> None:
    text_lower = content.text.lower()
    filename_lower = metadata.filename.lower()
    for pattern in RULE_PATTERNS:
        has_keywords = bool(pattern.keywords) and all(
            keyword in text_lower for keyword in pattern.keywords
        )
        matches = has_keywords
        if not matches and pattern.search_terms:
            matches = any(term in text_lower for term in pattern.search_terms)
        if not matches and pattern.fallback_filenames:
            matches = any(fragment in filename_lower for fragment in pattern.fallback_filenames)
        if not matches:
            continue

        search_basis = pattern.search_terms or pattern.keywords
        pages = find_rule_pages(content, search_basis) if search_basis else []
        rule_entry = existing_rules.get(pattern.rule_id)
        if rule_entry is None:
            rule_entry = {
                "rule_id": pattern.rule_id,
                "scope": pattern.scope,
                "semantics": pattern.semantics,
                "constraints": pattern.constraints,
                "applies_since": metadata.doc_date,
                "applies_until": None,
                "precedence": pattern.precedence,
                "source_doc_refs": [],
            }
            existing_rules[pattern.rule_id] = rule_entry
        else:
            if metadata.doc_date:
                current_date = rule_entry.get("applies_since")
                if not current_date or metadata.doc_date < current_date:
                    rule_entry["applies_since"] = metadata.doc_date

        references: list[dict[str, Any]] = rule_entry["source_doc_refs"]
        reference = next(
            (ref for ref in references if ref["filename"] == metadata.filename),
            None,
        )
        if reference is None:
            reference = {"filename": metadata.filename, "pages": pages or None}
            references.append(reference)
        else:
            if pages:
                existing_pages = set(reference.get("pages") or [])
                existing_pages.update(pages)
                reference["pages"] = sorted(existing_pages)


def normalise_index(index_data: dict[str, Any]) -> dict[str, Any]:
    documents = sorted(index_data["documents"], key=lambda doc: doc["filename"].lower())
    for document in documents:
        document["entities"] = sorted(document.get("entities", []))

    rules = sorted(index_data["rules"], key=lambda rule: rule["rule_id"])
    for rule in rules:
        refs = rule.get("source_doc_refs", [])
        for ref in refs:
            if ref.get("pages"):
                ref["pages"] = sorted(ref["pages"])
        rule["source_doc_refs"] = sorted(refs, key=lambda ref: ref["filename"])

    index_data["documents"] = documents
    index_data["rules"] = rules
    return index_data


def write_index(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def build_index(source_dir: Path, repo_root: Path) -> dict[str, Any]:
    documents_payload: list[dict[str, Any]] = []
    rules_payload: dict[str, dict[str, Any]] = {}

    for path in discover_documents(source_dir):
        logger.debug("Processing %s", path)
        content = extract_content(path)
        metadata = make_metadata(path, content, repo_root)
        documents_payload.append(serialise_metadata(metadata))
        build_rules(metadata, content, rules_payload)

    now = datetime.now(timezone.utc).isoformat()
    index = {
        "generated_at": now,
        "schema_version": SCHEMA_VERSION,
        "documents": documents_payload,
        "rules": list(rules_payload.values()),
    }
    return normalise_index(index)


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="[%(levelname)s] %(message)s")
    logging.getLogger("pdfminer").setLevel(logging.WARNING)
    logging.getLogger("pdfminer.pdfinterp").setLevel(logging.WARNING)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rebuild", action="store_true", help="Rewrite the canonical index")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--index-path", type=Path, default=DEFAULT_INDEX_PATH)
    parser.add_argument("--summary-path", type=Path, default=SUMMARY_PATH)
    parser.add_argument("--changelog-path", type=Path, default=CHANGELOG_PATH)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    configure_logging(args.verbose)

    logger.info("Building AGT rules index from %s", args.source_dir)
    index_payload = build_index(args.source_dir, args.repo_root)

    previous = load_existing_index(args.index_path)

    if args.rebuild:
        logger.info("Writing index to %s", args.index_path)
        write_index(args.index_path, index_payload)
    else:
        logger.info("Dry-run mode; index not rewritten")

    update_summary(index_payload, args.summary_path)
    update_changelog(previous, index_payload, args.changelog_path)

    logger.info("Index build completed with %d documents and %d rules", len(index_payload["documents"]), len(index_payload["rules"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
