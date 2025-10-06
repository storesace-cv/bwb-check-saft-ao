# Verificador SAF-T (AO)

Ferramenta em Python para validação e correção de ficheiros **SAF-T (AO)** conforme o esquema XSD oficial e regras de negócio da AGT.

> ℹ️ **Nota importante**  
> Toda a documentação e organização inicial deste repositório foi gerada pelo **ChatGPT**.  
> O **Codex GPT** terá a responsabilidade de assumir a evolução do projeto, podendo reorganizar o código, as pastas e a documentação como entender melhor.

## Funcionalidades
- Validação contra XSD oficial (`schemas/SAFTAO1.01_01.xsd`).
- Validação de regras de negócio estritas (precisão, arredondamento, totais, TaxTable).
- Correção automática (scripts `autofix_soft` e `autofix_hard`).
- Geração de logs de erros em Excel (`logs/*.xlsx`).

## Requisitos
```bash
pip install -r requirements.txt
```

## Utilização

### Validação
```bash
python3 validator_saft_ao.py FICHEIRO.xml --xsd schemas/SAFTAO1.01_01.xsd
```

### Correção Soft
```bash
python3 saft_ao_autofix_soft.py FICHEIRO.xml
```

### Correção Hard
```bash
python3 saft_ao_autofix_hard.py FICHEIRO.xml
```

---

## Estrutura do projeto
- `validator_saft_ao.py`: valida ficheiros SAF-T AO.  
- `saft_ao_autofix_soft.py`: aplica correções leves.  
- `saft_ao_autofix_hard.py`: aplica correções mais profundas.  
- `schemas/SAFTAO1.01_01.xsd`: schema oficial.  
- `logs/`: local dos relatórios gerados.  
- `docs/`: documentação do projeto.

---

## Licença
MIT
