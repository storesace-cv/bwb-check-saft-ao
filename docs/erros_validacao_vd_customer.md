# Erros de validação detectados

Este documento regista os problemas encontrados na validação do ficheiro `AO5002185695_1_20250801_000000_20250831_235959_20251006233531_v.02_invalido.xml` e as acções propostas para os resolver.

## 1. Código de fatura `InvoiceType="VD"`

* **Erro reportado:** o XSD rejeita o código `VD` porque não pertence à enumeração válida (`FT`, `FR`, `GF`, `FG`, `AC`, `AR`, `ND`, `NC`, `AF`, `TV`, `RP`, `RE`, `CS`, `LD`, `RA`).
* **Impacto:** impede o envio do ficheiro para a AGT.
* **Resolução proposta:** normalizar `VD` para `FR`, por ser o único tipo que representa venda com recebimento imediato. Esta substituição será automatizada numa rotina de *soft auto-fix*.

## 2. Cliente `CustomerID = 100250`

* **Erro reportado:** a validação acusa a ausência do cliente `100250` na secção `MasterFiles/Customer`.
* **Observação:** o registo existe na base de dados da aplicação; será necessário confirmar porque não foi exportado para o SAF-T.
* **Resolução proposta:** investigar a rotina de exportação para garantir que o cliente é sempre incluído, ou ajustar a lógica de construção do ficheiro para replicar os dados presentes na aplicação.

## Próximos passos

* Implementar o *auto-fix* que converte `InvoiceType="VD"` em `FR`.
* Rever a extracção de clientes para garantir que o identificador `100250` (e quaisquer outros utilizados) está presente no bloco `MasterFiles`.
