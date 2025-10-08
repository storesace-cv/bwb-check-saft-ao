# Arquitetura Interna

O repositório passou a tratar o pacote `src/saftao` como fonte de verdade. Os
scripts na pasta `scripts/` existem apenas como *wrappers* finos que delegam para
os módulos reais do pacote.

## Camadas actuais

1. **Interface de linha de comandos (`saftao.cli`)** – responsável por registar
   os comandos disponíveis e encaminhar argumentos para os módulos
   especializados.
2. **Comandos (`saftao.commands.*`)** – implementação concreta da validação e
   das rotinas de auto-correcção. Estes módulos foram migrados directamente dos
   scripts legados e continuam a expor a mesma experiência de utilização.
3. **Wrappers legados (`scripts/*.py`)** – mantêm compatibilidade com
   distribuições anteriores e projectos que importavam directamente os scripts.
   Cada ficheiro apenas faz `raise SystemExit(main())` para o comando
   correspondente no pacote.

```
saftao.cli  ->  saftao.commands.<command>  ->  scripts/<legacy>.py (compat)
```

## Mapa de comandos

| Comando        | Módulo                                     | Wrapper legado                         | Saídas principais                          |
| -------------- | ------------------------------------------ | -------------------------------------- | ------------------------------------------ |
| `validate`     | `saftao.commands.validator_strict`         | `scripts/validator_saft_ao.py`         | Excel com erros/sugestões, relatório no STDOUT |
| `autofix-soft` | `saftao.commands.autofix_soft`             | `scripts/saft_ao_autofix_soft.py`      | XML corrigido, log Excel com acções        |
| `autofix-hard` | `saftao.commands.autofix_hard`             | `scripts/saft_ao_autofix_hard.py`      | XML corrigido (versões *_v.xx*), mensagens STDOUT |

Os metadados de cada comando (nome, resumo, módulo de origem e wrapper
legado) estão registados em `saftao.cli.CommandSpec`, o que permite gerar
páginas de documentação ou UIs dinâmicas a partir da mesma fonte.

## Melhorias de coesão propostas

- **Unificação da manipulação de `sys.exit`** – parte do código ainda depende
  de `sys.exit()` directo. O *wrapper* em `CommandSpec.run` normaliza o código
  de saída, mas o ideal será devolver sempre inteiros para simplificar testes.
- **Conversão progressiva para funções puras** – mover a lógica pesada de
  manipulação de XML (actualmente em funções internas dos scripts) para módulos
  reutilizáveis (`saftao.validator`, `saftao.autofix.*`). Isto permitirá que
  novas interfaces (GUI, serviços web) partilhem a mesma API.
- **Centralização do logging** – tanto o validador como os *auto-fixes*
  constroem instâncias próprias de `ExcelLogger`. Extrair uma fábrica comum em
  `saftao.logging` reduzirá divergências e facilitará personalizações.
- **Testes integrados por comando** – agora que os comandos estão registados no
  pacote é possível criar `pytest` parametrizado que invoque `saftao.cli.run`
  para cada fluxo, garantindo que as saídas continuam consistentes.
