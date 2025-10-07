# Verificador SAF-T (AO)

Ferramenta em Python para validação e correção de ficheiros **SAF-T (AO)**
conforme o esquema XSD oficial e regras de negócio da AGT.

> ℹ️ **Nota importante**
> Toda a documentação e organização inicial deste repositório foi gerada pelo
> **ChatGPT**. O **Codex GPT** terá a responsabilidade de assumir a evolução do
> projeto, podendo reorganizar o código, as pastas e a documentação como
> entender melhor.

## Funcionalidades
- Validação contra XSD oficial (`schemas/SAFTAO1.01_01.xsd`).
- Validação de regras de negócio estritas (precisão, arredondamento, totais,
  TaxTable).
- Correção automática (scripts `autofix_soft` e `autofix_hard`).
- Geração de logs de erros em Excel (`logs/*.xlsx`).

## Requisitos
Recomendamos isolar as dependências numa *virtualenv* dedicada. A forma mais
simples é utilizar o módulo `venv` da própria instalação de Python (>= 3.11):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

> Caso prefira `virtualenvwrapper`, `pyenv` ou ferramentas similares, assegure-se
> apenas de que o `python` activo corresponde à versão pretendida e que a pasta
> `PySide6/Qt/plugins` é instalada dentro do ambiente virtual (o comando acima
> garante isso automaticamente).

### Ferramentas de desenvolvimento

Para garantir uma base consistente de testes e linting recomendamos instalar as
dependências de desenvolvimento e executar as ferramentas de forma regular.

```bash
pip install -r requirements-dev.txt

# Testes
pytest

# Linting
flake8

# Formatação automática
black .
```

## Utilização

Enquanto a migração para o novo pacote Python decorre, os scripts originais
estão organizados na pasta `scripts/`. Use o `launcher.py` na raiz para os
executar de forma unificada ou invoque-os directamente a partir desse directório.

### Validação
```bash
python3 launcher.py validate FICHEIRO.xml --xsd schemas/SAFTAO1.01_01.xsd
```

### Correção Soft
```bash
python3 launcher.py autofix-soft FICHEIRO.xml
```

### Correção Hard
```bash
python3 launcher.py autofix-hard FICHEIRO.xml
```

### Interface gráfica

Para utilizar todas as ferramentas a partir de uma única aplicação execute o
`launcher.py` sem argumentos ou invoque directamente o módulo da GUI:

```bash
python3 launcher.py
# ou
python3 -m saftao.gui
```

A interface permite selecionar o ficheiro SAF-T, efectuar validações, aplicar as
correcções automáticas *soft* ou *hard* e registar novas actualizações de regras
ou esquemas sem recorrer à linha de comandos.

#### Diagnóstico do Qt no macOS

Se o arranque da interface gráfica falhar com o erro do plugin ``cocoa`` no
macOS, execute o comando de diagnóstico para inspecionar o ambiente actual:

```bash
python3 launcher.py qt-doctor
```

O relatório indica as variáveis de ambiente detectadas, o caminho dos plugins
instalados com o PySide6 e sugere um procedimento de recuperação. Os passos
recomendados incluem limpar variáveis Qt herdadas, reinstalar PySide6 6.7.x e
exportar explicitamente o directório ``platforms`` para testar o arranque.

### Registo de novas regras ou XSD
```bash
PYTHONPATH=src python3 -m saftao.rules_updates --note "Circular 12/2024" \
    --xsd caminho/para/SAFTAO1.02.xsd --rule caminho/para/regras.xlsx \
    --tag CIRCULAR_12_2024
```

O comando acima copia os ficheiros recebidos para `rules_updates/`, actualiza o
índice `rules_updates/index.json` com o metadado e, opcionalmente, aceita vários
`--rule` adicionais. Caso pretenda substituir o XSD activo em `schemas/`, use o
argumento extra `--schema-target SAFTAO1.01_01.xsd`.

---

## Estrutura do projeto
- `src/saftao/`: novo pacote modular com stubs para validação, auto-fix e
  utilitários partilhados. As primeiras implementações práticas incluem:
  - `saftao.logging.ExcelLogger`: escrita simples de relatórios em Excel com
    `openpyxl`, reutilizável pela GUI e futuros comandos.
  - `saftao.utils`: funções de apoio para detecção do *namespace* e parsing de
    decimais partilhadas entre scripts.
- `scripts/validator_saft_ao.py`, `scripts/saft_ao_autofix_soft.py`,
  `scripts/saft_ao_autofix_hard.py`: scripts legacy a migrar para o pacote.
- `schemas/`: esquema oficial.
- `docs/`: documentação funcional e técnica.
- `tests/`: suite de testes (placeholder).

---

## Licença
MIT
