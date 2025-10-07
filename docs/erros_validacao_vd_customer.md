# Erros de validação detectados

Este documento regista os problemas encontrados na validação do ficheiro `AO5002185695_1_20250801_000000_20250831_235959_20251006233531_v.02_invalido.xml` e as acções propostas para os resolver.

## 1. Código de fatura `InvoiceType="VD"`

* **Erro reportado:** o XSD rejeita o código `VD` porque não pertence à enumeração válida (`FT`, `FR`, `GF`, `FG`, `AC`, `AR`, `ND`, `NC`, `AF`, `TV`, `RP`, `RE`, `CS`, `LD`, `RA`).
* **Impacto:** impede o envio do ficheiro para a AGT.
* **Resolução proposta:** normalizar `VD` para `FR`, por ser o único tipo que representa venda com recebimento imediato. Esta substituição será automatizada numa rotina de *soft auto-fix*.

## 2. Cliente `CustomerID = 100250`

* **Erro reportado:** a validação acusa a ausência do cliente `100250` na secção `MasterFiles/Customer`.
* **Observação:** o registo existe na base de dados da aplicação; será necessário confirmar porque não foi exportado para o SAF-T.
* **Plano de confirmação:**
  1. Abrir o ficheiro XML entregue e confirmar manualmente (ou com uma consulta XPath) se existe uma entrada em `MasterFiles/Customer` com `<CustomerID>100250</CustomerID>`.
  2. Caso a entrada não exista, executar a rotina de exportação em ambiente de teste com *logging* detalhado para garantir que o cliente é carregado a partir da base de dados.
  3. Comparar o resultado da exportação com o estado actual da base de dados, verificando se existem filtros que excluem clientes sem actividade recente.
* **Resolução proposta:** alinhar a rotina de extracção com o comportamento desejado:
  * garantir que todos os `CustomerID` referenciados em `SourceDocuments/SalesInvoices` são incluídos no bloco `MasterFiles/Customer`;
  * acrescentar uma verificação automática (ver Secção 3) que acusa a ausência do cliente durante a geração do ficheiro.

## Próximos passos

* ✅ *Auto-fix* actualizado para converter `InvoiceType="VD"` em `FR` automaticamente durante o processo de correcções.
* ✅ Rotina interactiva que garante a presença de todos os clientes referenciados no bloco `MasterFiles`, recorrendo ao ficheiro Excel indicado pelo utilizador.

## 3. Actualizações planeadas

| Item | Objectivo | Como será feito |
| ---- | --------- | --------------- |
| Normalização `VD` | Substituir automaticamente `InvoiceType="VD"` por `FR` durante a geração do ficheiro. | Implementado pela função `normalize_invoice_type_vd`, integrada no script de auto-fix e registada no log Excel. |
| Verificação de clientes | Garantir que todos os `CustomerID` referenciados existem em `MasterFiles/Customer`. | Implementado pela função `ensure_invoice_customers_exported`, que compara os identificadores usados nas facturas com os clientes exportados, procura automaticamente o ficheiro fixo `work/origem/addons/Listagem_de_Clientes.xlsx` e cria os registos em falta. |
