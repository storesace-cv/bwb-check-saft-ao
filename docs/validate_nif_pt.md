# 📘 Validação Matemática e Estrutural do NIF Português

## 🔎 Objetivo
Este documento descreve o **algoritmo matemático oficial** e as **regras estruturais** que permitem validar um **Número de Identificação Fiscal (NIF)** emitido pela **Autoridade Tributária e Aduaneira de Portugal (AT)**.

O objetivo é verificar se o NIF é **estruturalmente válido**, mesmo sem consultar qualquer base de dados externa, e explicar tecnicamente como consultar a API do NIF.PT para obter dados públicos de empresas.

---

## 🧩 Estrutura do NIF

O NIF possui **9 dígitos numéricos**:

```
NIF = D1 D2 D3 D4 D5 D6 D7 D8 D9
```

- **D1..D8**: Dígitos base
- **D9**: Dígito de controlo (checksum)

---

## 🧮 Algoritmo de Validação Matemática

O dígito de controlo (**D9**) é calculado da seguinte forma:

1. Multiplicar cada um dos 8 primeiros dígitos por um peso decrescente de 9 até 2.

   ```
   Soma = D1×9 + D2×8 + D3×7 + D4×6 + D5×5 + D6×4 + D7×3 + D8×2
   ```

2. Calcular o **resto da divisão por 11**:

   ```
   Resto = Soma mod 11
   ```

3. Calcular o **dígito de controlo**:

   ```
   Se Resto < 2  → D9 = 0
   Caso contrário → D9 = 11 - Resto
   ```

4. O NIF é **válido** se o **último dígito** for igual ao valor calculado.

---

## 🔢 Prefixos Válidos (Identificação de Tipo)

| Prefixo | Tipo de Entidade | Observações |
|----------|------------------|----------------|
| 1, 2, 3  | Pessoas singulares | Residentes |
| 45       | Pessoas coletivas não residentes |  |
| 5        | Pessoas coletivas (empresas) | Inclui sociedades e associações |
| 6        | Administrações públicas |  |
| 8        | Empresários em nome individual |  |
| 9        | Outros / utilizações temporárias |  |

---

## 💻 Exemplo de Implementação em Python

```python
def nif_valido(nif: str) -> bool:
    if not nif.isdigit() or len(nif) != 9:
        return False

    soma = sum(int(d) * (9 - i) for i, d in enumerate(nif[:8]))
    resto = soma % 11
    digito_controle = 0 if resto < 2 else 11 - resto
    return int(nif[-1]) == digito_controle
```

---

## 🌐 API NIF.PT — Como consultar (técnico)

O NIF.PT disponibiliza um **webservice simples** para consultar NIFs e obter informações públicas (nome, morada, atividade) quando disponíveis.

### Obter a chave de acesso
- Submeta o formulário em "API - Pedido de Acesso" no site do NIF.PT; receberá por email uma **key** e um link para ativação. Após ativada, pode usar a API. (ver política de utilização).

### Endpoint básico (GET) — Consulta de NIF
- Exemplo simples de chamada (substitua `KEY` e `NIF`):

```
http://www.nif.pt/?json=1&q=<NIF>&key=<KEY>
```

- Parâmetros:
  - `json=1` — força resposta em JSON.
  - `q=<NIF>` — número a pesquisar.
  - `key=<KEY>` — chave de API obtida por email.

### Exemplo CURL

```bash
curl "http://www.nif.pt/?json=1&q=509442013&key=SEU_KEY"
```

### Exemplo Python (requests)

```python
import requests

def consulta_nif_nifpt(nif: str, key: str, timeout=10):
    url = "http://www.nif.pt/"
    params = {"json": "1", "q": nif, "key": key}
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()
```

### Endpoints adicionais úteis

#### 1) Compra de créditos
Permite comprar créditos para ultrapassar os limites gratuitos.

```
http://www.nif.pt/?json=1&buy=<QUANTIDADE>&invoice_name=<NOME>&invoice_nif=<NIF-FACTURA>&key=<KEY>
```

**Resposta (exemplo):**
```
{"credits": 1000, "mb": {"entity": "10241", "reference": "000 000 000", "amount": "10.00"}}
```

> `invoice_name` e `invoice_nif` são opcionais; sem eles a fatura é emitida a "Consumidor Final". Se enviar `invoice_nif`, tem de ser um NIF válido.

#### 2) Verificação de créditos
Consulta o consumo de créditos gratuitos/pagos do mês/dia/hora/minuto corrente.

```
http://www.nif.pt/?json=1&credits=1&key=<KEY>
```

**Resposta (exemplo):**
```
{"credits": {"month": 1000, "day": 100, "hour": 10, "minute": 1, "paid": 0}}
```

### Exemplo oficial de Pesquisa (pedido e resposta)

**Pedido**
```
http://www.nif.pt/?json=1&q=509442013&key=KEY
```

**Resposta** (exemplo real da documentação)
```json
{
  "result": "success",
  "records": {
    "509442013": {
      "nif": 509442013,
      "seo_url": "nexperience-lda",
      "title": "Nexperience Lda",
      "address": "Rua da Lionesa Nº 446, Edifício G20",
      "pc4": "4465",
      "pc3": "671",
      "city": "Leça do Balio",
      "activity": "Desenvolvimento de software. Consultoria em informática. Comércio de equipamentos e sistemas informáticos. Exploração de portais web.",
      "status": "active",
      "cae": "62010",
      "contacts": {
        "email": "info@nex.pt",
        "phone": "220198228",
        "website": "www.nex.pt",
        "fax": "224 905 459"
      },
      "structure": {
        "nature": "LDA",
        "capital": "5000.00",
        "capital_currency": "EUR"
      },
      "geo": {
        "region": "Porto",
        "county": "Matosinhos",
        "parish": "Leça do Balio"
      },
      "place": {
        "address": "Rua da Lionesa Nº 446, Edifício G20",
        "pc4": "4465",
        "pc3": "671",
        "city": "Leça do Balio"
      },
      "racius": "http://www.racius.com/nexperience-lda/",
      "alias": "Nex - Nexperience, Lda",
      "portugalio": "http://www.portugalio.com/nex/"
    }
  },
  "nif_validation": true,
  "is_nif": true,
  "credits": { "used": "free", "left": [] }
}
```

---

### Mapeamento para Excel (Codex)

Extrair do bloco `records` (nota: chave do dicionário = NIF consultado) e mapear para as colunas do Excel conforme segue:

| Campo `nif.pt` | Coluna Excel | Regra |
|---|---|---|
| `nif` | **Contribuinte** | Valor numérico/string conforme devolvido |
| `title` | **Nome** | Texto |
| `address` | **Morada** | Texto |
| `pc4` + `pc3` | **Cod. Postal** | Concatenar como `"pc4-pc3"` (ex.: `4465-671`) |
| `city` | **Localidade** | Texto |

> Dicas: se `pc4`/`pc3` vierem vazios, deixar `Cod. Postal` por preencher. Conservar acentuação e `utf-8`.

#### Pseudocódigo de parsing e mapeamento
```python
payload = consulta_nif_nifpt(nif, key)

if payload.get("result") == "success" and payload.get("records"):
    rec = next(iter(payload["records"].values()))  # primeiro (único) registo
    cod_postal = "-".join(filter(None, [rec.get("pc4"), rec.get("pc3")])) if rec.get("pc4") or rec.get("pc3") else ""
    linha_excel = {
        "Contribuinte": str(rec.get("nif", "")).strip(),
        "Nome": (rec.get("title") or "").strip(),
        "Morada": (rec.get("address") or "").strip(),
        "Cod. Postal": cod_postal,
        "Localidade": (rec.get("city") or "").strip(),
    }
```

---


## 📈 Limites e compras de créditos

A utilização gratuita está sujeita a limites que devem ser respeitados pelo Codex/cliente:

| Intervalo | Máx. pedidos |
|-----------|--------------|
| Por minuto | 1 |
| Por hora   | 10 |
| Por dia    | 100 |
| Por mês    | 1000 |

Para exceder estes limites, é possível adquirir créditos pagos (ex.: €0,01 por pedido adicional) segundo a documentação/portal do NIF.PT.

---

## ♻️ Boas práticas técnicas para integração

1. **Cache** — armazene localmente (ex.: TTL 24–168h) resultados de NIFs para reduzir pedidos repetidos.
2. **Backoff e retry** — implemente retries exponenciais e respeite `Retry-After` quando aplicável.
3. **Rate-limiter local** — garanta que não excede 1 pedido/minuto por chave; se usar múltiplas chaves, discipline-as igualmente.
4. **Batching e queue** — para processamento massivo, enfileire pedidos e respeite limites; considere comprar créditos se necessário.
5. **Logging e auditoria** — registre datas/IPs/resultado para fins de auditoria e conformidade RGPD.

---

## ⚖️ Privacidade e legal

- Use os dados apenas para finalidades legítimas; evite expor nomes de pessoas singulares sem consentimento. Observe RGPD e termos do NIF.PT.

---

**Fim do documento**
