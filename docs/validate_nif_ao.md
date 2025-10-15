# 📘 Validação Heurística de NIF (Angola)

## 🔎 Objetivo
Este documento descreve as **regras, padrões e heurísticas conhecidas** que permitem ao sistema validar **Números de Identificação Fiscal (NIF)** emitidos pela **Administração Geral Tributária (AGT)** de Angola.

O objetivo é **classificar** cada NIF segundo o seu grau de plausibilidade, mesmo **sem algoritmo de controlo oficial**, e preparar o terreno para integração com o endpoint público da AGT.

---

## 🧩 1️⃣ Tipos de NIF reconhecidos

| Tipo de contribuinte | Formato típico | Observações |
|----------------------|----------------|--------------|
| Pessoa coletiva (empresa) | **10 dígitos numéricos** | Confirmado em portais da AGT e implementações SAF-T AO |
| Pessoa singular (formato histórico) | **14 caracteres alfanuméricos** (`NNNNNNNNNLLNNN`) | Muito comum em NIF antigos; `L` = letras, `N` = dígitos |
| Consumidor final | **999999999** | Placeholder válido e aceite pela AGT e SAF-T AO |
| Pessoa singular (novo formato) | **Mesmo número do Bilhete de Identidade** | Pode ser numérico ou alfanumérico |
| Exceções / históricos | 8–11 dígitos sem letras | Casos residuais antigos (manter compatibilidade) |

---

## 🧮 2️⃣ Classificação heurística

Cada NIF deve ser classificado em **três níveis**:

| Nível | Descrição | Utilização prática |
|-------|------------|--------------------|
| 🟥 **Manifestamente errado** | Formato impossível, caracteres inválidos, demasiado curto/longo | Pode ser rejeitado imediatamente |
| 🟧 **Possivelmente errado** | Estrutura incompleta, mistura de letras/dígitos fora de posição | Avisar o utilizador e tentar corrigir ou confirmar |
| 🟩 **Possivelmente correto** | Formato coincide com um dos padrões conhecidos | Pode ser aceite, devendo depois ser confirmado via AGT |

---

## ⚙️ 3️⃣ Regras de validação

Abaixo estão as regras **em ordem de prioridade**.

### 3.1 Normalização
Antes de validar:
- Remover espaços e hífens.
- Converter para maiúsculas.
- Remover todos os caracteres não alfanuméricos.

```python
def normalizar_nif(nif: str) -> str:
    return ''.join(ch for ch in nif.strip().upper() if ch.isalnum())
```

---

### 3.2 Padrões reconhecidos
| Categoria | Expressão regular | Interpretação |
|------------|------------------|----------------|
| Empresa (Pessoa Coletiva) | `^\d{10}$` | 10 dígitos |
| Pessoa Singular (histórica) | `^\d{9}[A-Z]{2}\d{3}$` | 9 dígitos + 2 letras + 3 dígitos |
| Consumidor Final | `^999999999$` | Valor especial |
| BI / Cartão Residente (novo formato) | `^[A-Z0-9]{9,14}$` | 9 a 14 caracteres alfanuméricos, plausível |
| Antigo / Exceção | `^\d{8,11}$` | Versões numéricas antigas |

---

### 3.3 Lógica de classificação heurística

```python
import re

def classificar_nif_ao(nif: str) -> str:
    if not nif:
        return "manifestamente_errado"
    nif = ''.join(ch for ch in nif.strip().upper() if ch.isalnum())
    if not re.fullmatch(r"[0-9A-Z]+", nif):
        return "manifestamente_errado"
    if nif == "999999999":
        return "possivelmente_correto"
    if re.fullmatch(r"\d{10}", nif):
        return "possivelmente_correto"
    if re.fullmatch(r"\d{9}[A-Z]{2}\d{3}", nif):
        return "possivelmente_correto"
    if re.fullmatch(r"[A-Z0-9]{9,14}", nif):
        return "possivelmente_correto"
    if len(nif) < 6 or len(nif) > 15:
        return "manifestamente_errado"
    return "possivelmente_errado"
```

---

## 🌐 4️⃣ Verificação via AGT

Endpoint oficial:  
`https://invoice.minfin.gov.ao/commonServer/common/taxpayer/get/{NIF}`

Exemplo de resposta:
```json
{
  "success": true,
  "data": {
    "nif": "5000000000",
    "companyName": "Exemplo Lda",
    "nsrdz": "Rua 123",
    "hdzt": "ACTIVE"
  }
}
```

---

## 🧱 5️⃣ Exemplo de validação completa

```python
def validar_nif_completo(nif: str, session=None) -> dict:
    import requests
    estado = classificar_nif_ao(nif)
    result = {"nif": nif, "estado": estado, "confirmado_agt": None, "ativo": None}
    if estado != "possivelmente_correto":
        return result
    try:
        url = f"https://invoice.minfin.gov.ao/commonServer/common/taxpayer/get/{nif}"
        r = (session or requests).get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get("success") and data.get("data"):
            result["confirmado_agt"] = True
            result["ativo"] = (data["data"].get("hdzt") == "ACTIVE")
        else:
            result["confirmado_agt"] = False
    except Exception:
        result["confirmado_agt"] = False
    return result
```

---

## ✅ 6️⃣ Exemplos de classificação esperada

| NIF | Classificação | Motivo |
|------|----------------|--------|
| `999999999` | 🟩 possivelmente_correto | consumidor final |
| `5000000000` | 🟩 possivelmente_correto | empresa (10 dígitos) |
| `003489072LA037` | 🟩 possivelmente_correto | pessoa singular (14 caracteres) |
| `1234567` | 🟧 possivelmente_errado | demasiado curto |
| `A00000000` | 🟥 manifestamente_errado | começa por letra, inválido |
| `ABCDE12345` | 🟥 manifestamente_errado | mistura não coerente |
| `50000000001XYZ` | 🟧 possivelmente_errado | muito longo |
| `1234567890123456` | 🟥 manifestamente_errado | > 15 caracteres |

---

## 📚 Fontes consultadas
- Decreto Presidencial – Regime Jurídico do NIF (angolex.com)
- Portal do Contribuinte da AGT (portaldocontribuinte.minfin.gov.ao)
- Endpoint público AGT – invoice.minfin.gov.ao
- Exemplos reais de NIF: `003489072LA037`, `999999999`, `5000000000`
- validarnif.pt – Angola validator

**Fim do documento**


### 📤 Export para Excel (Fallback PT)

Quando o fallback PT for acionado (e houver resposta válida do `nif.pt`), mapear os campos devolvidos para as colunas do Excel:

| Campo `nif.pt` | Coluna Excel | Regra |
|---|---|---|
| `nif` | **Contribuinte** | Valor devolvido (string/numérico) |
| `title` | **Nome** | Texto |
| `address` | **Morada** | Texto |
| `pc4` + `pc3` | **Cod. Postal** | Concatenar `"pc4-pc3"` (ex.: `4465-671`). Se um faltar, deixar vazio ou apenas o disponível |
| `city` | **Localidade** | Texto |

> Observação: antes de escrever, garanta `País = Portugal`. Para **pessoa singular** sem consulta `nif.pt`, manter `Localidade = "NIF INVÁLIDO | Possivelmente Português"`.

#### Pseudocódigo
```python
resp = consulta_nif_nifpt(nif_pt, key)
if resp.get("result") == "success" and resp.get("records"):
    rec = next(iter(resp["records"].values()))
    cod_postal = "-".join(filter(None, [rec.get("pc4"), rec.get("pc3")])) if rec.get("pc4") or rec.get("pc3") else ""
    linha_excel = {
        "Contribuinte": str(rec.get("nif", "")).strip(),
        "Nome": (rec.get("title") or "").strip(),
        "Morada": (rec.get("address") or "").strip(),
        "Cod. Postal": cod_postal,
        "Localidade": (rec.get("city") or "").strip(),
        "País": "Portugal",
    }
```
