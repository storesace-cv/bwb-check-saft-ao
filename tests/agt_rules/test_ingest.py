from __future__ import annotations

import json
import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import agt_ingest_rules


@pytest.fixture()
def sample_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    source_dir = tmp_path / "agt"
    source_dir.mkdir()

    pdf_path = source_dir / "2025-08-14_ds120.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n...")

    docx_path = source_dir / "2025-10-01_layout.docx"
    docx_path.write_bytes(b"PK\x03\x04")

    txt_path = source_dir / "readme.txt"
    txt_path.write_text("Guia oficial de 2024-12-15", encoding="utf-8")

    def fake_extract_content(path: Path) -> agt_ingest_rules.DocumentContent:
        if path.suffix == ".pdf":
            text = (
                "TaxRegistrationNumber deve ser numérico.\n"
                "TaxCountryRegion: AO\n"
            )
        elif path.suffix == ".docx":
            text = "BuildingNumber usa S/N quando aplicável. PostalCode 0000-000"
        else:
            text = "Resumo SAF-T (AO)\n"
        return agt_ingest_rules.DocumentContent(text=text, pages=[text])

    monkeypatch.setattr(agt_ingest_rules, "extract_content", fake_extract_content)

    return source_dir


def test_build_index_from_mocked_documents(sample_source: Path) -> None:
    index = agt_ingest_rules.build_index(sample_source, sample_source.parent)
    assert len(index["documents"]) == 3
    rule_ids = {rule["rule_id"] for rule in index["rules"]}
    assert {
        "agt.header.tax_registration_number.digits_only",
        "agt.header.building_number.normalised",
        "agt.header.postal_code.placeholder",
        "agt.tax.country_region.required",
    } <= rule_ids


def test_index_is_idempotent(sample_source: Path) -> None:
    first = agt_ingest_rules.build_index(sample_source, sample_source.parent)
    second = agt_ingest_rules.build_index(sample_source, sample_source.parent)
    first_cmp = dict(first)
    second_cmp = dict(second)
    first_cmp.pop("generated_at", None)
    second_cmp.pop("generated_at", None)
    assert first_cmp == second_cmp


def test_repository_index_matches_schema() -> None:
    schema_path = Path("schemas/agt_rules_index.schema.json")
    index_path = Path("rules_updates/agt/index.json")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    payload = json.loads(index_path.read_text(encoding="utf-8"))

    from jsonschema import validate

    validate(instance=payload, schema=schema)
