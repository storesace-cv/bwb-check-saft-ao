# bwb-check-saft-ao — API de Integração SAF‑T (AO)

> Pacote de documentação para o desenho e implementação da **nossa própria API REST** que permite a integração com softwares de faturação para **upload, validação, correção** e (quando aplicável) **submissão** de ficheiros **SAF‑T (AO)**.

- Data: 2025-10-07
- Língua: pt-PT (pré-Acordo, termos técnicos mantêm-se)
- Público: equipa interna (devs, QA) + Codex

## Sumário dos documentos

- `API_OVERVIEW.md` — Visão geral, objectivos, princípios e fluxos.
- `API_SPEC.md` — Especificação REST (rotas, payloads, erros, versionamento).
- `VALIDATION_RULES.md` — Regras técnicas (XSD) e de negócio (hashes, totais, datas).
- `SCHEMAS_AND_REFERENCES.md` — Estruturas, XSDs e fontes de referência.
- `SECURITY_AND_AUTH.md` — Autenticação (JWT), permissões, auditing e LGPD.
- `WORKFLOWS_AND_PIPELINES.md` — Pipelines de validação/correção e integração com a app de “correcções de SAF‑T”.
- `DEPLOYMENT_AND_DEVOPS.md` — Stack, ambientes, logs, observabilidade e migrações.
- `ERROR_CATALOG.md` — Catálogo padronizado de códigos/erros/warnings.
- `POSTMAN_COLLECTION.json` — Colecção exemplo para testes (importar no Postman ou Insomnia).
- `CODEX_PROMPT_API_SCAFFOLD.md` — Prompt único e directo para o Codex gerar o esqueleto inicial (FastAPI) **exactamente** como pretendido.
- `ROADMAP.md` — Roadmap de fases, MVP → GA.
- `GLOSSARY.md` — Glossário de termos SAF‑T (AO) e internos.

> Dica: começa por **API_OVERVIEW.md** e **CODEX_PROMPT_API_SCAFFOLD.md**.
