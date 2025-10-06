# Implementação

## validator_saft_ao.py
- Usa `lxml` para parse de XML e validação contra XSD.
- Implementa funções de arredondamento (q2, q6).
- Gera log em formato Excel via `openpyxl`.

## saft_ao_autofix_soft.py
- Aplica correções de arredondamento e coerência mínima.

## saft_ao_autofix_hard.py
- Reordena blocos, força coerência de totais.

## Organização de logs
- Cada execução gera `.xlsx` com erros ou correções aplicadas.
