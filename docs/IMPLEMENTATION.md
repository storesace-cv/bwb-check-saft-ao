# Implementação

Este repositório contém duas gerações de código que convivem enquanto decorre
uma migração faseada para um pacote Python instalável.

## Scripts legados na raiz
- **`validator_saft_ao.py`** — implementa toda a validação estrita, incluindo
  validação XSD, regras de arredondamento (`q2`, `q6`), reconciliação de totais e
  geração de _logs_ em Excel através de uma classe `ExcelLogger` própria.
- **`saft_ao_autofix_soft.py`** — aplica correções não destrutivas: ajusta
  arredondamentos, normaliza percentagens e assegura a coerência mínima entre
  totais de documentos.
- **`saft_ao_autofix_hard.py`** — efetua correções estruturais mais agressivas,
  reordenando blocos e forçando os totais a respeitarem as regras da AGT.

Estes ficheiros continuam a ser o caminho crítico para utilizadores finais,
mas servem também como referência funcional para a nova arquitetura.

## Pacote `src/saftao`
O pacote encapsula a lógica partilhada para validação e correção. Os módulos
principais são:

| Módulo | Responsabilidade |
| --- | --- |
| `cli.py` | Ponto de entrada para uma futura CLI unificada com subcomandos de validação e auto-fix. |
| `validator.py` | Define a API de validação e classes `ValidationIssue` para exportação de resultados. |
| `autofix/soft.py` e `autofix/hard.py` | Local destinado à migração das rotinas de correção suave e forte. |
| `logging.py` | Especifica `ExcelLoggerConfig` e um `ExcelLogger` partilhado para normalizar os relatórios. |
| `utils.py` | Agrega utilitários de parsing (decimais, _namespaces_) reutilizados entre módulos. |
| `invoices.py` | Contém a _dataclass_ `Invoice` e abstrações para leitura de documentos. |
| `tax_table.py` | Modela entradas de tabela de impostos e respetivo carregamento. |

A maioria das funções no pacote ainda está em modo _stub_, em preparação para a
migração da lógica existente nos scripts legados.

## Registo e relatórios
- Tanto o `validator_saft_ao.py` como a futura implementação em `src/saftao`
  produzem relatórios em Excel para facilitar auditorias.
- Os _logs_ incluem códigos de erro, valores calculados e sugestões de correção,
  permitindo integração com processos internos de revisão.

## Testes e automação
- O diretório `tests/` contém casos que exercitam partes fundamentais da
  validação SAF-T (AO). A expansão desta suíte é essencial para garantir a
  confiabilidade durante a refatoração.
- Recomenda-se configurar _CI_ com execução de testes e _linting_ (por exemplo,
  `pytest`, `ruff`, `mypy`) à medida que os _stubs_ forem implementados.
