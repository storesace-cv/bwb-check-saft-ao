# Regras Técnicas do SAF-T (AO)

Documento de referência rápida para implementação e validação técnica do
ficheiro SAF-T (AO) versão 1.01_01.

## Estrutura e componentes obrigatórios

O ficheiro segue o esquema XML `urn:OECD:StandardAuditFile-Tax:AO_1.01_01`
(publicado em `schemas/SAFTAO1.01_01.xsd`). Os blocos principais são:

1. **Header** – identificação da empresa, contabilidade e
   configuração fiscal. Campos críticos: `TaxRegistrationNumber`,
   `TaxAccountingBasis`, `TaxEntity`, `ProductCompanyTaxID`, `SoftwareCertificateNumber`.
2. **MasterFiles** – catálogos de clientes, fornecedores, produtos,
   contas do plano, impostos e tabelas auxiliares. IDs devem ser únicos e
   consistentes com os documentos emitidos.
3. **GeneralLedgerEntries** – movimentos contabilísticos, com
   `JournalID`, `TransactionID`, `GLPostingDate` e reconciliação por
   conta.
4. **SourceDocuments** – faturas (`SalesInvoices`), documentos de
   fornecedores (`PurchaseInvoices`), recibos (`Payments`), impostos
   retidos (`WithholdingTax`) e documentos de movimento de stock
   (`MovementOfGoods`).

Cada secção possui limites de cardinalidade definidos no XSD; utilizar o
esquema para gerar validações automáticas.

## Regras de formato

- **Codificação**: UTF-8 sem BOM e separador decimal ponto.
- **Datas**: formato ISO 8601 (`YYYY-MM-DD` ou `YYYY-MM-DDThh:mm:ss`).
- **Moeda**: código ISO 4217 (`AOA` por omissão) com casas decimais
  definidas em `CurrencyDecimals`.
- **TimeZone**: utilizar `Africa/Luanda` para datas com hora.
- **Compactação**: a AGT aceita ficheiro XML simples ou arquivo ZIP com
  o XML e assinatura digital (`.xml.sig`).

## Identificadores e integridade

- `TaxRegistrationNumber` deve coincidir com o número de contribuinte
  registado no Portal do Contribuinte.
- `SoftwareCertificateNumber` é obrigatório para soluções certificadas;
  para software interno utilizar `0` e preencher `ProductID`/`ProductVersion`.
- `CustomerID`, `SupplierID`, `ProductCode` e `AccountID` têm de ser
  consistentes ao longo do ficheiro. Referências cruzadas inválidas devem
  ser bloqueadas pelo validador.
- Valores monetários devem reconciliar com totais (`DocumentTotals` e
  `TaxPayable`). Implementar verificações de soma antes da exportação.

## Validações adicionais recomendadas

- Validar NIF (9 dígitos) com algoritmo de controlo da AGT antes de
  exportar clientes e fornecedores.
- Verificar limites do XSD (tamanho máximo de campos, enumerados de
  códigos de imposto, `InvoiceType`, `MovementType`, etc.).
- Incluir testes automáticos que comparem o XML gerado com exemplos
  oficiais fornecidos nos manuais e com o XSD em `schemas/`.
- Gerar hash (`SHA-1` ou `SHA-256`) do ficheiro final para auditoria
  interna e registar no log de submissão.

## Entrega e retenção técnica

1. **Nome do ficheiro**: `SAFT_AO_<NIF>_<AAAA-MM>.xml` (ou `.zip`), sem
   espaços ou caracteres especiais.
2. **Assinatura**: quando aplicável, anexar ficheiro `.sig` emitido pelo
   certificado qualificado da empresa.
3. **Armazenamento**: conservar versão submetida e eventuais versões
   retificativas com respetivos comprovativos de entrega.
4. **Monitorização**: guardar logs da exportação e respostas do portal
   (códigos de estado, mensagens de erro) para rastreabilidade.

Atualizar este documento sempre que a AGT publicar nova versão do XSD ou
orientações técnicas adicionais.
