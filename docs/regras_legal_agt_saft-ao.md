# Regras Legais do SAF-T (AO)

Este guia resume o enquadramento normativo emitido pela Administração
Geral Tributária (AGT) para a geração e submissão do ficheiro SAF-T (AO).
O objetivo é dar visibilidade rápida às equipas técnicas sobre as
obrigações que condicionam as decisões de arquitetura e de produto.

## Diplomas e referências oficiais

- **Despacho Executivo n.º 472/20, de 23 de Dezembro** – institui o
  SAF-T (AO) como formato obrigatório de reporte eletrónico e define o
  escalonamento de entrada em vigor por tipologia de contribuinte.
- **Manual do Contribuinte SAF-T (AO)** e **Manual do Utilizador do
  Portal do Contribuinte** – detalham procedimentos de submissão,
  autenticação e suporte documental exigido.
- **Manual Técnico e XSD SAFTAO1.01_01** – especificação publicada pela
  AGT com as regras de estruturação e validação do ficheiro XML.
- **Código do IVA (Lei n.º 7/19) e Código Geral Tributário** – fonte das
  obrigações de conservação de dados, sigilo fiscal e penalidades.

> Manter cópias atualizadas destes documentos na pasta `docs/` ou via
> links de referência no `README.md`. Na ausência de nova legislação, o
> projeto deve continuar alinhado com a versão 1.01_01 do ficheiro.

## Calendário de adoção

| Segmento de contribuinte                | Período de referência | Prazo limite de submissão |
| -------------------------------------- | --------------------- | ------------------------- |
| Grandes contribuintes                  | Desde janeiro/2021    | Último dia do mês seguinte |
| Médios contribuintes                   | Desde julho/2021      | Último dia do mês seguinte |
| Restantes sujeitos passivos de IVA     | Desde janeiro/2022    | Último dia do mês seguinte |
| Contribuintes sem operações de faturação | Dispensados, mas devem justificar ausência de SAF-T | Não aplicável |

As datas refletem o escalonamento fixado pelo Despacho Executivo n.º
472/20. Prorrogações pontuais são comunicadas pela AGT através de
instruções internas; monitorizar circulares para ajustar cronogramas.

## Obrigações principais

1. **Emissão do ficheiro mensal** – contempla todas as operações do mês
   anterior, incluindo documentos anulados, corrigidos ou emitidos em
   moeda estrangeira.
2. **Submissão eletrónica** – realizada via Portal do Contribuinte, com
   autenticação do representante legal e assinatura digital válida.
3. **Retificação** – caso seja detetado erro, o contribuinte deve
   submeter um novo ficheiro completo com indicação de substituição.
4. **Arquivo** – manter o SAF-T (AO) e respetivos documentos de suporte
   durante pelo menos dez anos, em formato que garanta integridade e
   leitura futura.
5. **Cooperação em auditorias** – disponibilizar o ficheiro e a chave de
   validação quando solicitado em inspeções presenciais.

## Sanções e riscos

- **Coimas** previstas no Código Geral Tributário e no Regime Geral das
  Infracções Tributárias por omissão ou atraso de entrega.
- **Correções oficiosas** e liquidações adicionais quando os dados
  submetidos não suportam as declarações periódicas de IVA.
- **Suspensão de benefícios fiscais** em caso de incumprimento reiterado.

Documentar no repositório os contactos de suporte AGT e procedimentos de
contingência (por exemplo, submissão presencial em caso de falha
prolongada do portal) ajuda a reduzir risco operacional.

## Atualizações 2025 — Faturação Eletrónica

- **Decreto Presidencial n.º 71/25** (20 de março de 2025) entra em vigor
  em **20 de setembro de 2025**, revogando os Decretos 292/18 e 144/23 e
  instituindo fases obrigatórias para adoção da faturação eletrónica.
- **Âmbito inicial**: grandes contribuintes e fornecedores do Estado são
  os primeiros obrigados a integrar o novo regime. Os restantes segmentos
  seguem o calendário a publicar pela AGT.
- **Revogação do software SAC5**: deixa de ter validade fiscal a partir
  de **1 de setembro de 2025**, exigindo migração dos contribuintes
  dependentes da solução.
- **Fatura Premiada**: iniciativa prevista para arrancar a **1 de
  outubro de 2025**, com impacto em obrigações de reporte e partilha de
  dados de consumo.
- **Regularização após notificação**: contribuintes notificados têm 15
  dias para atualizar software e processos, devendo o projeto prever
  fluxos de correção rápidos e auditorias internas.
- **Séries de faturas emitidas pela AGT**: o sistema Codex deve suportar
  a gestão de séries atribuídas centralmente e sincronizar atualizações
  com o Portal do Contribuinte.
- **Monitorização contínua**: manter registo de consultas periódicas aos
  canais oficiais (UCM, Portal do Contribuinte, comunicados AGT) e
  documentar cada revisão com data. Ponto de contacto técnico confirmado:
  `sifp@minfin.gov.ao`.
