# Workflows e Pipelines

## Pipeline padrão
1. Recepção (upload) → armazenar *as‑is* + calcular SHA‑256.
2. Validação XSD (sincrona) → se falha, erro imediato.
3. Enfileirar validações de negócio (assíncrono).
4. Gerar relatório JSON (+ PDF opcional).
5. Aplicar *auto-fix* opcional → criar nova versão.
6. Revalidar versão corrigida → relatório final.
7. (Futuro) Submeter à AGT; guardar recibo/estado.

## Integração com a App de Correcções
- A app invoca os endpoints da API (mesmo host).
- Abrir relatório no ReportBro/HTML dentro da app.
- Botão “Corrigir e reenviar” chama `/auto-fix` e posterior `/submit` (quando existir).
