# Deployment & DevOps

## Stack sugerida
- **Backend**: FastAPI (Python 3.11+)
- **Workers**: RQ/Celery + Redis
- **DB**: PostgreSQL (prod) / SQLite (dev)
- **Storage**: S3 compatível ou disco
- **PDF**: ReportBro/WeasyPrint
- **Auth**: PyJWT

## Ambientes
- `dev` (local), `staging`, `prod`.
- Variáveis (.env): chaves, DSNs, paths `schemas/`.

## Observabilidade
- Logs estruturados (JSON) com níveis.
- Métricas (Prometheus) e dashboards.
- Alertas (erro taxa > N%, filas lentas).

## Backups
- Base de dados + storage de uploads/relatórios.
