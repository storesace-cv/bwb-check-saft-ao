# Visão Geral — API de Integração SAF‑T (AO)

## Objectivo
Criar uma **API REST** própria que permita que softwares de faturação:
1) **Façam upload** de ficheiros SAF‑T (AO);
2) **Validem** tecnicamente (XSD) e por regras de negócio;
3) **Corrijam** automaticamente problemas típicos (quando possível);
4) (Futuro) **Submetam** o ficheiro aceite aos serviços da AGT, quando existir endpoint oficial.

A mesma API será consumida pela nossa aplicação “correcções de SAF‑T” para fechar o ciclo: **receber → corrigir → reenviar → confirmar aceitação**.

## Princípios
- **Compatibilidade** com XSD oficial SAF‑T (AO) (validação determinística).
- **Imutabilidade** do upload original (para auditoria).
- **Correções traçáveis**: cada correcção produz uma nova versão com delta.
- **Transparência**: relatórios completos (erros, avisos, “fixes” aplicados).
- **Segurança**: JWT, least-privilege, encriptação “at-rest” e “in-transit”.
- **Escalabilidade**: processamento assíncrono com filas (p.ex. Celery/RQ).

## Fluxo Alto Nível
1. **/auth/login** → obter token.
2. **/saft/upload** → receber XML; devolver `job_id`.
3. **/saft/validate/{job_id}** → validar XSD + regras; gerar `report_id`.
4. **/saft/auto-fix/{job_id}** (opcional) → aplicar correcções seguras; criar `version_id`.
5. **/saft/status/{job_id}`** → acompanhar estado (received/validated/fixed/submitted/failed).
6. **/saft/report/{report_id}** → descarregar relatório (JSON/PDF).
7. **/saft/download/{version_id}** → obter XML original/corrigido.
8. **/saft/submit/{version_id}** (futuro) → submissão à AGT (quando houver endpoint oficial).

## Limitações actuais

- A API cobre apenas as etapas internas (upload, validação, correcções e distribuição de relatórios/versões).
- **Não existe integração directa com os serviços da AGT neste momento.** Enquanto a Autoridade Geral Tributária não disponibilizar um endpoint
  oficial, a submissão continua a ter de ser feita manualmente no Portal do Contribuinte com o ficheiro preparado pela API.
- O endpoint `POST /saft/submit` está reservado na especificação, mas permanece desactivado até que a ligação oficial possa ser implementada.

## Domínios/Entidades
- **Company** (NIF, nome, etc.)
- **Upload** (`job_id`, período fiscal, ficheiro original)
- **Validation** (`report_id`, resultado XSD + regras)
- **Fix** (`version_id`, diffs aplicados)
- **Submission** (`submission_id`, recibo/estado externo)
