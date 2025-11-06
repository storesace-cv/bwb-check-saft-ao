from __future__ import annotations

import json
from pathlib import Path

import pytest
from lxml import etree

from lib.validators import rules_loader
from saftao import validator


def _write_index(path: Path) -> None:
    payload = {
        "generated_at": "2025-11-06T00:00:00+00:00",
        "schema_version": "1.0.0",
        "documents": [
            {
                "source_path": "tests/doc.pdf",
                "filename": "doc.pdf",
                "filesize": 128,
                "hash_sha256": "0" * 64,
                "title": "Doc",
                "doc_date": "2025-08-14",
                "date_confidence": "medium",
                "version": "v1",
                "type": "circular",
                "entities": ["AGT"],
                "abstract": "",
                "uncertainty_level": None,
            }
        ],
        "rules": [
            {
                "rule_id": "agt.header.tax_registration_number.digits_only",
                "scope": "header.tax_registration_number",
                "semantics": "Digits only",
                "constraints": {
                    "format": "digits-only",
                    "strip_non_digits": True,
                },
                "applies_since": "2025-08-14",
                "applies_until": None,
                "precedence": 10,
                "source_doc_refs": [{"filename": "doc.pdf", "pages": [1]}],
            },
            {
                "rule_id": "agt.header.building_number.normalised",
                "scope": "header.company_address.building_number",
                "semantics": "Normalise building",
                "constraints": {
                    "allowed_markers": ["S/N"],
                    "forbidden_values": ["0"],
                },
                "applies_since": "2025-08-14",
                "applies_until": None,
                "precedence": 8,
                "source_doc_refs": [{"filename": "doc.pdf", "pages": [2]}],
            },
            {
                "rule_id": "agt.header.postal_code.placeholder",
                "scope": "header.company_address.postal_code",
                "semantics": "Normalise postal",
                "constraints": {
                    "placeholder": "0000",
                    "alias": "0000-000",
                },
                "applies_since": "2025-08-14",
                "applies_until": None,
                "precedence": 8,
                "source_doc_refs": [{"filename": "doc.pdf", "pages": [3]}],
            },
            {
                "rule_id": "agt.tax.country_region.required",
                "scope": "tax.country_region",
                "semantics": "Country required",
                "constraints": {
                    "required": True,
                    "allowed_values": ["AO"],
                },
                "applies_since": "2025-08-14",
                "applies_until": None,
                "precedence": 6,
                "source_doc_refs": [{"filename": "doc.pdf", "pages": [4]}],
            },
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _build_tree() -> etree._ElementTree:
    xml = """
    <AuditFile xmlns="urn:OECD:StandardAuditFile-Tax:AO_1.01">
      <Header>
        <CompanyAddress>
          <BuildingNumber>0</BuildingNumber>
          <PostalCode>0000-000</PostalCode>
        </CompanyAddress>
        <TaxRegistrationNumber>AO500123456</TaxRegistrationNumber>
      </Header>
      <MasterFiles/>
      <SourceDocuments>
        <SalesInvoices>
          <Invoice>
            <InvoiceNo>FT 1</InvoiceNo>
            <CustomerID>C1</CustomerID>
            <Line>
              <LineNumber>1</LineNumber>
              <Tax>
                <TaxType>IVA</TaxType>
                <TaxCountryRegion></TaxCountryRegion>
              </Tax>
            </Line>
          </Invoice>
        </SalesInvoices>
      </SourceDocuments>
    </AuditFile>
    """
    return etree.ElementTree(etree.fromstring(xml.encode()))


def test_validator_enforces_rules(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    index_path = tmp_path / "index.json"
    _write_index(index_path)

    monkeypatch.setenv("AGT_RULES_INDEX_PATH", str(index_path))
    monkeypatch.setattr(rules_loader, "_CACHED_INDEX", None)
    rules_loader.load_rules_index(force_reload=True)

    issues = validator.validate_tree(_build_tree())
    codes = {issue.code: issue for issue in issues}

    assert "HEADER_TAX_ID_INVALID" in codes
    assert codes["HEADER_TAX_ID_INVALID"].details["suggested_value"] == "500123456"

    assert "HEADER_BUILDING_NUMBER_INVALID" in codes
    assert codes["HEADER_BUILDING_NUMBER_INVALID"].details["suggested_value"] == "S/N"

    assert "HEADER_POSTAL_CODE_INVALID" in codes
    assert codes["HEADER_POSTAL_CODE_INVALID"].details["suggested_value"] == "0000"

    assert any(issue.code == "TAX_COUNTRY_REGION_MISSING" for issue in issues)
