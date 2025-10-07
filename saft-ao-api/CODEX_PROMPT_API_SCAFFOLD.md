# Prompt Único para o Codex — Gerar Esqueleto da API (FastAPI)

**Objectivo:** gerar um projecto FastAPI com os endpoints e contratos descritos em `API_SPEC.md`, integrado com validação XSD e regras de negócio mínimas.

---

## Instruções (copiar e colar no Codex)

Cria um projecto FastAPI chamado `bwb_saftao_api` com:
- Python 3.11+, `poetry` ou `pip` + `uvicorn[standard]`.
- Dependências: `fastapi`, `python-multipart`, `pydantic`, `lxml`, `xmlschema`, `python-jose[cryptography]` ou `pyjwt`, `passlib[bcrypt]`, `psycopg2-binary` (ou `asyncpg`), `redis`, `rq`/`celery`, `loguru`.
- Estrutura de pastas:
```
bwb_saftao_api/
  app/
    main.py
    api/ (routers)
    core/ (config, security, logging)
    models/ (ORM)
    services/ (validation, fixes, reports)
    schemas/ (pydantic)
    workers/ (tasks async)
    storage/
    xsd/ (SAFTAO_*.xsd)
  tests/
  pyproject.toml / requirements.txt
  README.md
```

### Implementa:
1) `/auth/login` (JWT com utilizadores em memória para MVP).
2) `/saft/upload` (multipart) → guardar ficheiro em `storage/uploads/` e registo na DB.
3) `/saft/validate/{job_id}` → validar com XSD (usar `lxml`/`xmlschema`) e uma regra simples (NetTotal + TaxPayable == GrossTotal com tolerância 0,01). Gerar relatório JSON e guardar.
4) `/saft/status/{job_id}` → devolve estado.
5) `/saft/auto-fix/{job_id}` → implementar 2 fixes: `NORMALIZE_DECIMALS`, `PAD_NIF_WITH_ZERO` (apenas se determinístico).
6) `/saft/report/{report_id}` → JSON directo; PDF pode ser “TODO” com função stub.
7) `/saft/download/{version_id}` → devolver XML original/corrigido.
8) Versionamento por prefixo `/v1`.

### Especificações a respeitar:
- Ver contratos em `API_SPEC.md` e erros em `ERROR_CATALOG.md`.
- Logging estruturado; calcular SHA‑256 do upload à entrada.
- Guardar sempre o original; alterações criam nova versão com delta (pode ser guardado como ficheiro separado `fixed/…` para o MVP).
- Preparar *hooks* para no futuro chamar `/saft/submit`.

### Testes:
- Criar testes unitários mínimos para: upload, validação XSD de XML válido vs inválido, e um caso de fix aplicado.

### Entregáveis:
- Código compilável, `README` com como executar `uvicorn`, e comandos para criar venv + rodar.
