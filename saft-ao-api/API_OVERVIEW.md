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
- **Não existe validação prévia contra os sistemas da AGT.** Os relatórios de validação/correção são internos e não garantem aceitação pela AGT;
  apenas simulam as regras conhecidas.

## O que é possível fazer hoje

1. Automatizar o **upload seguro** do ficheiro SAF‑T (AO) e manter o original imutável para auditoria.
2. Executar **validações XSD e regras de negócio** com geração de relatórios detalhados (JSON/PDF) para equipas internas e clientes.
3. Aplicar **correcções automáticas** onde existam “fixes” seguros, produzindo novas versões versionadas do ficheiro.
4. Distribuir o ficheiro **corrigido** e respectivos relatórios para que o contribuinte faça a submissão manual.
5. Acompanhar o **estado interno** de cada job (received/validated/fixed/failed) através de `/saft/status/{job_id}`.

> ⚠️ Até existir um serviço oficial da AGT, não é possível consultar online se o ficheiro será aceite nem acompanhar estados externos
> (aceite/rejeitado). O pipeline prepara o ficheiro da melhor forma possível e guarda o histórico, mas a submissão e confirmação final
> continuam dependentes do portal da AGT.

## Domínios/Entidades
- **Company** (NIF, nome, etc.)
- **Upload** (`job_id`, período fiscal, ficheiro original)
- **Validation** (`report_id`, resultado XSD + regras)
- **Fix** (`version_id`, diffs aplicados)
- **Submission** (`submission_id`, recibo/estado externo)
