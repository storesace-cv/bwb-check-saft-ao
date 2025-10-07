# Especificação da API (REST)

> **Base URL (exemplo)**: `https://api.bwb-saftao.local/v1`  
> **Formato**: JSON para requests/responses; `multipart/form-data` no upload.  
> **Autenticação**: Bearer JWT (`Authorization: Bearer <token>`).

---

## 1) Autenticação

### POST /auth/login
**Body**
```json
{ "username": "operador@empresa", "password": "••••••••" }
```
**200**
```json
{ "access_token": "<jwt>", "token_type": "bearer", "expires_in": 3600 }
```
**401** `INVALID_CREDENTIALS`

---

## 2) Upload

### POST /saft/upload
**Headers**: `Authorization`, `Content-Type: multipart/form-data`  
**Form fields**
- `file`: XML SAF‑T (AO)
- `empresa_nif`: string (9 dígitos)
- `periodo`: string `YYYY-MM`

**202**
```json
{
  "job_id": "f25a9f1a-...",
  "status": "received",
  "filename": "SAFT_AO_2025-09.xml",
  "empresa_nif": "500000000",
  "periodo": "2025-09",
  "received_at": "2025-10-07T19:10:00Z"
}
```

**4xx/5xx** conforme `ERROR_CATALOG.md`.

---

## 3) Validação

### POST /saft/validate/{job_id}
Aciona validação XSD + regras de negócio.
**200**
```json
{
  "job_id": "…",
  "report_id": "…",
  "status": "validated",
  "valid": true,
  "errors": [],
  "warnings": ["MISSING_CUSTOMER_TAX_ID: linha 245"],
  "summary": {
    "total_invoices": 58,
    "total_sales": 1452300.50,
    "hash_sequence_ok": true
  }
}
```

### GET /saft/status/{job_id}
**200**
```json
{ "job_id": "…", "status": "received|validating|validated|fixing|fixed|submitting|submitted|failed" }
```

---

## 4) Correções (“auto-fix”)

### POST /saft/auto-fix/{job_id}
Aplica correcções **determinísticas e seguras** (ver `VALIDATION_RULES.md`).  
**200**
```json
{
  "job_id": "…",
  "version_id": "…",
  "status": "fixed",
  "fixes_applied": [
    { "code": "NORMALIZE_DECIMALS", "count": 124 },
    { "code": "PAD_NIF_WITH_ZERO", "count": 2 }
  ]
}
```

### GET /saft/download/{version_id}
Devolve XML (original ou corrigido).

---

## 5) Relatórios

### GET /saft/report/{report_id}?format=json|pdf
**200** → JSON ou PDF.  
Para PDF, `Content-Type: application/pdf` e download.

---

## 6) Submissão (futuro)

### POST /saft/submit/{version_id}
Encaminha versão final para a AGT (quando existir endpoint oficial).  
**202**
```json
{ "submission_id": "…", "status": "submitted", "submitted_at": "…" }
```

### GET /saft/submission/{submission_id}
Estado da submissão externa.

---

## Versionamento da API
- `v1` via prefixo de URL.
- Quebras incompatíveis → `v2` / paralelismo por 6–12 meses.

## Rate Limits
Cabeçalhos `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `Retry-After`.

## Paginação
Padrão `?page=1&page_size=50` e cabeçalhos `X-Total-Count`.
