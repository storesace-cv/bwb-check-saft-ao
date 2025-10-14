from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

import tools.corrige_clientes_agt as corrige

from tools.corrige_clientes_agt import (
    aplicar_regras,
    corrigir_excel,
    fetch_taxpayer,
    normalizar_nif,
    set_fetch_settings,
)


class DummyResponse:
    def __init__(self, status_code: int, payload: Any | None = None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class DummySession:
    def __init__(self, responses: dict[str, DummyResponse]):
        self.responses = responses
        self.calls: list[str] = []

    def get(self, url: str, timeout: float):
        self.calls.append(url)
        nif = url.rsplit("/", 1)[-1]
        return self.responses.get(nif, DummyResponse(404, {"success": False}))

    def close(self):
        pass


def test_normalizar_nif_remove_nao_digitos():
    assert normalizar_nif("001.234.567-8") == "0012345678"


def test_aplicar_regras_preferencia_company_name():
    linha = {"Codigo": "1", "NIF": "500", "Nome": "Original", "Morada": "Rua", "Localidade": "Cidade"}
    api = {"companyName": "Empresa", "gsmc": "Oficial", "nsrdz": "Endereco", "hdzt": "ACTIVE"}
    resultado = aplicar_regras(linha, api, "500", {"500": "1"})
    assert resultado["Nome"] == "Empresa"
    assert resultado["Morada"] == "Endereco"
    assert resultado["Localidade"] == "Cidade"


def test_aplicar_regras_inactivo_altera_localidade():
    linha = {"Codigo": "1", "NIF": "500", "Nome": "Original", "Morada": "Rua", "Localidade": "Cidade"}
    api = {"gsmc": "Oficial", "nsrdz": "Endereco", "hdzt": "SUSPENDED"}
    resultado = aplicar_regras(linha, api, "500", {"500": "1"})
    assert resultado["Localidade"] == "Contribuinte INACTIVO na AGT"


def test_aplicar_regras_nif_invalido():
    linha = {"Codigo": "1", "NIF": "", "Nome": "Original", "Morada": "Rua", "Localidade": "Cidade"}
    resultado = aplicar_regras(linha, None, "", {})
    assert resultado["Localidade"] == "NIF INVALIDO"


def test_aplicar_regras_nif_duplicado():
    linha = {"Codigo": "2", "NIF": "500", "Nome": "Original", "Morada": "Rua", "Localidade": "Cidade"}
    resultado = aplicar_regras(linha, {}, "500", {"500": "1"})
    assert resultado["Localidade"] == "NIF DUPLICADO - 1"


def test_fetch_taxpayer_usa_cache(monkeypatch):
    responses = {"500": DummyResponse(200, {"success": True, "data": {"companyName": "Empresa"}})}
    session = DummySession(responses)
    cache: dict[str, Any] = {}
    set_fetch_settings(rate_limit=0, timeout=10, use_cache=True)

    # primeira chamada deve realizar request
    resultado1 = fetch_taxpayer("500", session, cache)
    assert resultado1["companyName"] == "Empresa"
    assert len(session.calls) == 1

    # segunda chamada usa cache
    resultado2 = fetch_taxpayer("500", session, cache)
    assert resultado2["companyName"] == "Empresa"
    assert len(session.calls) == 1


def test_corrigir_excel_integration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    set_fetch_settings(rate_limit=0, timeout=10, use_cache=False)

    dados = pd.DataFrame(
        [
            {"Codigo": "C1", "NIF": "500000000", "Nome": "Orig1", "Morada": "Rua 1", "Localidade": "Cidade"},
            {"Codigo": "C2", "NIF": "500000000", "Nome": "Orig2", "Morada": "Rua 2", "Localidade": "Cidade"},
            {"Codigo": "C3", "NIF": "", "Nome": "Orig3", "Morada": "Rua 3", "Localidade": "Cidade"},
        ]
    )
    input_path = tmp_path / "clientes.xlsx"
    dados.to_excel(input_path, index=False)

    responses = {
        "500000000": DummyResponse(
            200,
            {
                "success": True,
                "data": {
                    "companyName": "Empresa Nova",
                    "gsmc": "Nome Oficial",
                    "nsrdz": "Endereco Atualizado",
                    "hdzt": "ACTIVE",
                },
            },
        )
    }

    monkeypatch.setattr(
        "tools.corrige_clientes_agt.requests.Session",
        lambda: DummySession(responses),
    )

    output_path = corrigir_excel(str(input_path))
    assert Path(output_path).exists()

    result = pd.read_excel(output_path)
    assert list(result["Nome"]) == ["Empresa Nova", "Empresa Nova", "Orig3"]
    assert list(result["Morada"]) == ["Endereco Atualizado", "Endereco Atualizado", "Rua 3"]
    assert result.loc[0, "Localidade"] == "Cidade"
    assert result.loc[1, "Localidade"] == "NIF DUPLICADO - C1"
    assert result.loc[2, "Localidade"] == "NIF INVALIDO"

    summary = corrige.LAST_SUMMARY
    assert summary is not None
    assert summary["linhas"] == 3
    assert summary["invalidos"] == 1
    assert summary["nifs_duplicados"] == 1
    assert summary["duplicados_marcados"] == 1
