# Arquitetura Interna

Esta secção documentará os componentes principais do pacote `saftao`.

## Módulos planeados

- `saftao.cli` – ponto de entrada unificado para comandos de linha de comando.
- `saftao.validator` – serviços de validação e geração de relatórios.
- `saftao.autofix` – correções automáticas (soft e hard).
- `saftao.utils` – funções partilhadas (formatação, parsing e namespaces).
- `saftao.logging` – infraestruturas de logging e geração de relatórios.
- `saftao.tax_table` e `saftao.invoices` – objetos de domínio e carregamento.
- `saftao.schema` – resolução de recursos de esquema.

Cada módulo será coberto por testes dedicados na pasta `tests/`.
