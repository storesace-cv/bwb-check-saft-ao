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

A partir desta reorganização a forma recomendada de utilizar as ferramentas é
através da CLI unificada do pacote:

```bash
python -m saftao.cli <comando> [opções]
```

### Fluxos de utilização

| Fluxo                        | Comando de exemplo                                                                 | Entradas obrigatórias        | Saídas principais                                        |
| ---------------------------- | ---------------------------------------------------------------------------------- | ---------------------------- | -------------------------------------------------------- |
| Validação estrita            | `python -m saftao.cli validate dados/SAFT.xml --xsd schemas/SAFTAO1.01_01.xsd`     | Ficheiro SAF-T, XSD opcional | Log Excel com erros/sugestões, mensagens no terminal     |
| Auto-fix não destrutivo      | `python -m saftao.cli autofix-soft dados/SAFT.xml --output-dir results/`           | Ficheiro SAF-T               | XML corrigido, log Excel com acções aplicadas            |
| Auto-fix com reordenação     | `python -m saftao.cli autofix-hard dados/SAFT.xml --output-dir results/`           | Ficheiro SAF-T               | XML numerado (`*_v.xx.xml`), mensagens de validação XSD  |
| Relatório de totais          | `python -m saftao.cli report dados/SAFT.xml`                                       | Ficheiro SAF-T             | Excel automático em `work/destino/relatorios/<SAFT>_totais.xlsx` |

#### Exemplo: validação estrita

```bash
python -m saftao.cli validate exemplos/Empresa_AO.xml --xsd schemas/SAFTAO1.01_01.xsd
```

Saídas esperadas:

- Mensagens no terminal com o resumo dos erros encontrados.
- Ficheiro `Empresa_AO_YYYYMMDDTHHMMSSZ.xlsx` na pasta corrente com colunas
  `code`, `message`, `xpath`, `invoice`, `line`, `field`, `suggested_value`, entre outras.

#### Exemplo: auto-fix *soft*

```bash
python -m saftao.cli autofix-soft exemplos/Empresa_AO.xml --output-dir build/
```

Saídas esperadas:

- XML corrigido em `build/Empresa_AO_v.02.xml` (ou versão seguinte disponível).
- Ficheiro `Empresa_AO_YYYYMMDDTHHMMSSZ_autofix.xlsx` com a lista das correcções.

#### Exemplo: relatório de totais

```bash
python -m saftao.cli report exemplos/Empresa_AO.xml
```

Saídas esperadas:

- Excel com a folha "Resumo" contendo totais sem IVA, IVA e com IVA por tipo contabilístico.
- Folha "Documentos não contabilísticos" com a listagem de GT, Requisições, Consultas de Mesa, etc., mesmo que não contribuam para os totais.
- Ficheiro gravado automaticamente em `work/destino/relatorios/Empresa_AO_totais.xlsx` (ou equivalente ao nome do SAF-T).

A pasta `work/destino/relatorios` é criada automaticamente e permanece ignorada pelo Git para evitar sincronizar relatórios gerados. Também é possível definir a pasta através da variável de ambiente `SAFTAO_REPORT_DIR` para cenários automatizados.

### Wrappers legados

Os scripts originais foram preservados para compatibilidade. Continuam a poder
ser executados directamente (`python scripts/validator_saft_ao.py ...`), mas
apenas reencaminham para os módulos do pacote `saftao`. Recomenda-se migrar
gradualmente para a nova CLI para beneficiar das melhorias futuras.

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
ou esquemas sem recorrer à linha de comandos. A nova interface é construída com
Tkinter (biblioteca padrão do Python), pelo que não necessita de PySide6 nem de
configuração adicional do Qt. A janela apresenta um cabeçalho personalizado para
permitir transparência; utilize os botões "—" e "✕" ou a tecla `Esc` para
minimizar ou fechar a aplicação.

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

## Regras AGT e referências úteis

| Categoria                   | Documento                                    | Conteúdo principal                                    |
| --------------------------- | -------------------------------------------- | ----------------------------------------------------- |
| Regras legais               | `docs/regras_legal_agt_saft-ao.md`           | Obrigações legais, eventos fiscais e limites de uso   |
| Regras técnicas             | `docs/regras_tecnico_agt_saft-ao.md`         | Estrutura do ficheiro, validações cruzadas e exemplos |
| Erros comuns                | `docs/erros_validacao_vd_customer.md`        | Casos frequentes de erro na exportação VD             |
| Países (ISO alpha-2)        | `docs/paises_iso_alpha2_pt.md`               | Lista de códigos de país aceites pela AGT             |
| Planeamento e objectivos    | `docs/OBJECTIVES.md`, `docs/FUTURE_PLANS.md` | Backlog estratégico e roadmap de evolução             |

Estas referências são a base para as regras aplicadas pelo validador e pelos
auto-fixes. Utilize-as em conjunto com os logs gerados para interpretar cada
mensagem de erro ou correcção sugerida.

---

## Estrutura do projeto
- `src/saftao/`: pacote modular com todas as funcionalidades.
  - `cli.py`: registo dos comandos e *dispatcher*.
  - `commands/`: implementação dos fluxos de validação e auto-fix.
  - `autofix/`, `validator/`, `logging/`: APIs partilhadas em evolução.
- `scripts/`: wrappers compatíveis que delegam para o pacote `saftao`.
- `schemas/`: esquema oficial.
- `docs/`: documentação funcional e técnica.
- `tests/`: suite de testes (placeholder).

---

## Licença
MIT
