# Avaliação Inicial do Projeto

## 1. Organização Atual
- Scripts principais (`validator_saft_ao.py`, `saft_ao_autofix_soft.py`, `saft_ao_autofix_hard.py`) estão na raiz sem um pacote Python comum, o que dificulta a partilha de utilitários entre eles.
- Ausência de estrutura clara para dados de entrada/saída (`logs/`, `examples/`, etc.) e falta de diretório dedicado a testes automatizados.
- Documentação existente (`docs/*.md`) é breve e não explica fluxos completos de validação/correção ou responsabilidades de cada script.

## 2. Revisão de Código e Dependências
- `validator_saft_ao.py` e `saft_ao_autofix_soft.py` repetem utilitários numéricos (funções `q2`, `q6`, formatação de percentagens) e lógica de deteção de namespace, sugerindo necessidade de módulo comum reutilizável.
- Não existe encapsulamento em classes ou funções modulares; a lógica encontra-se num único ficheiro com mais de 400 linhas, tornando manutenção e testes complexos.
- Dependências mínimas (`lxml`, `openpyxl`) não estão fixadas por versão, o que pode levar a comportamentos diferentes consoante o ambiente.
- Não há tratamento claro para ficheiros grandes (streaming/iterparse) nem limitação de memória.

## 3. Melhorias Imediatas Sugeridas
- **Modularização**: criar pacote `saft_ao/` contendo submódulos (`xsd.py`, `business_rules.py`, `autofix/`, `logging.py`) e mover scripts CLI para `scripts/` ou expor via `python -m saft_ao.cli`.
- **Partilha de utilitários**: extrair funções numéricas e helpers de XML para módulo comum (`utils.py`) e aplicar em todos os scripts para evitar inconsistências.
- **Camada de configuração**: permitir passagem de caminhos para logs, XSD e estratégias de arredondamento via argumentos ou ficheiro `.ini`/`.yaml`.
- **Gestão de dependências**: fixar versões mínimas (`lxml>=4.9`, `openpyxl>=3.1`) e considerar extras opcionais para validações adicionais.
- **Testes automatizados**: iniciar suite `pytest` com casos de validação para `validator_saft_ao` (sucesso, falha XSD, regras de negócio) e regressões para scripts de correção.
- **CI/CD**: configurar GitHub Actions para executar lint (`ruff`/`flake8`) e testes a cada PR.
- **Documentação**: expandir README e `docs/` com fluxos passo-a-passo, exemplos de logs gerados e explicação das regras da AGT.

## 4. Inconsistências Identificadas
- `validator_saft_ao.py` não termina com nova linha (`main()` colado ao prompt), indício de edição automática e potencial issue em linters.
- Falta de mensagens de erro uniformizadas entre scripts (algumas em português, outras misturam português/inglês; sugestões de internacionalização).
- Diretório `logs/` não está versionado nem referido no `.gitignore`, o que pode resultar em ficheiros temporários acidentalmente commitados.

## 5. Proposta de Nova Estrutura
```
saft_ao/
    __init__.py
    cli/
        __init__.py
        validate.py
        autofix_soft.py
        autofix_hard.py
    core/
        business_rules.py
        models.py
        utils.py
    io/
        excel_logger.py
        xml_loader.py
    schemas/
        SAFTAO1.01_01.xsd
scripts/
    validate.py
    autofix_soft.py
    autofix_hard.py
docs/
    ...
examples/
    sample_valid.xml
    sample_invalid.xml
logs/  (ignored)
tests/
    test_validator.py
```
- Esta estrutura separa a lógica nuclear dos CLIs, promove reutilização e prepara o terreno para distribuição via `pip` futuramente.

## 6. Próximos Passos Recomendados
1. Implementar refatoração modular mínima (extrair logger e utilitários partilhados).
2. Introduzir testes unitários e de integração básicos com `pytest`.
3. Criar roteiro de contribuição (`CONTRIBUTING.md`) e template de issues/PRs.
4. Adicionar exemplos de ficheiros SAF-T (anonimizados) para testes locais.
5. Planejar estratégia de correção "hard" para evitar alterações destrutivas (backup automático, diff detalhado).

---
Elaborado por Codex GPT — primeira revisão de arquitetura e qualidade.
