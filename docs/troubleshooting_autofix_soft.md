# Resolução de falhas ao aplicar o "Fix Precisão Standard"

## Contexto
O comando `Fix Precisão Standard` invoca o script legado
`scripts/saft_ao_autofix_soft.py`, responsável por normalizar aspetos de
precisão e ordenar elementos em linhas de documentos SAF-T (AO). A execução
reportada gerou um ficheiro `*_corrigido_invalido.xml` e a validação XSD falhou
com o erro:

> Element `{urn:OECD:StandardAuditFile-Tax:AO_1.01_01}OrderReferences`: This element is not expected. Expected is (`{urn:OECD:StandardAuditFile-Tax:AO_1.01_01}CustomsInformation`).

## Motivo do erro
O `autofix_soft` reorganiza os elementos das linhas através da função
`ensure_line_order`. Antes desta correção, a ordem de referência não incluía o
nó opcional `OrderReferences`. Consequentemente, todos os `OrderReferences`
encontrados eram movidos para o final da linha, ficando depois de
`CustomsInformation`. No esquema oficial (`schemas/SAFTAO1.01_01.xsd`), os
`OrderReferences` devem surgir logo após `LineNumber`; qualquer ocorrência após
`CustomsInformation` viola a sequência definida pelo XSD, levando aos múltiplos
erros observados.

## Correção implementada
Atualizámos `ensure_line_order` para refletir a ordem de elementos estabelecida
no XSD. Foram introduzidas as seguintes alterações:

- inclusão explícita de `OrderReferences` logo após `LineNumber`;
- suporte à preservação de `TaxBase`, `ProductSerialNumber` e `TaxExemptionCode`,
  evitando que estes campos opcionais sejam deslocados para o final da linha.

Com esta alteração, os elementos opcionais mantêm-se nas posições permitidas pelo
XSD, eliminando o erro de validação causado pelo rearranjo incorreto. Foram
revistos os restantes blocos reordenados (`DocumentTotals` e `TaxTableEntry`) e
confirmou-se que a sequência resultante coincide com a definida no XSD oficial.

## Passos recomendados
1. Atualize o repositório para incluir esta correção.
2. Reexecute o `Fix Precisão Standard` (ou invoque `python3 launcher.py
   autofix-soft <ficheiro.xml>`).
3. Valide novamente o XML corrigido com o XSD oficial (`schemas/SAFTAO1.01_01.xsd`).

Caso persistam erros, verifique o relatório Excel gerado pelo script para
identificar outros campos que necessitem de intervenção manual ou da execução do
`autofix_hard`.
