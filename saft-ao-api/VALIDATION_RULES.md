# Regras de Validação — SAF‑T (AO)

## 1) Validação XSD (estrutural)
- Usar XSD oficial SAF‑T (AO) (ver `SCHEMAS_AND_REFERENCES.md`).
- Rejeitar ficheiros não conformes com mensagem clara (linha/coluna).

## 2) Regras de Negócio (não exaustivo)
- **Sequência de Hash**: cada documento referenciar `hash` anterior; SHA‑1 conforme norma.
- **Integridade de Totais**: `NetTotal + TaxPayable == GrossTotal`. Tolerância: 0,01 AKZ.
- **Datas**: `InvoiceDate ≤ SystemEntryDate`; período fiscal coerente com `periodo` do upload.
- **NIF**: 9 dígitos; normalizar zeros à esquerda quando aplicável.
- **Duplicados**: `InvoiceNo` único por série/período.
- **Moeda/Taxas**: IVA alinhado com tabela interna; conferir arredondamentos.
- **Referências cruzadas**: linhas somam ao cabeçalho; clientes/fornecedores existem.
- **Numeração/Séries**: gaps justificados (documentos anulados) devem constar.

## 3) Severidade
- **ERROR**: bloqueia submissão; exige correcção.
- **WARNING**: não bloqueia, mas fica em relatório.
- **INFO**: nota informativa.

## 4) Fixes automáticos (determinísticos)
- Normalização de vírgula/decimal (`,` → `.`) onde inequívoco.
- Padding do NIF até 9 dígitos quando for claramente um *leading zero* ausente.
- Remoção de espaços não imprimíveis em campos de código.
- Recalcular total de linhas quando diferenças ≤ 0,01 e cabeçalho é consistente.

> Fixes que alterem **conteúdo fiscal** sensível (ex.: taxa de IVA) **não** são automáticos — apenas sugeridos no relatório.
