# Actualizações a 08-10-2025

Este documento consolida todas as atualizações verificadas no dia **08/10/2025** relativas à Faturação Eletrónica da AGT (Angola) e integra as instruções necessárias para atualização interna do sistema **Codex SAFT‑AO**.

---

## Documento 1 — fe_servicos_api

```md
# Faturação Eletrónica — Serviços REST/SOAP (AGT)

**Fonte oficial:** DS-120 Especificação Técnica FE v1.0  
**Data:** 01/10/2025  
**Autoridade:** Administração Geral Tributária (AGT), Ministério das Finanças de Angola  
**Revisão:** 1.0  
**Ambiente:** Homologação (https://sifphml.minfin.gov.ao)

... [conteúdo completo conforme resumo anterior] ...
```

---

## Documento 2 — fe_ds120_index

```md
# Documento DS-120 — Especificação Técnica FE v1.0 (Resumo)

**Título completo:** Especificação Técnica de Serviço — FE (Facturação Electrónica)  
**Referência:** DS-120  
**Data de criação:** 01/10/2025  
**Última atualização:** 05/10/2025  
**Revisores:** Eduardo Cordeiro Alves (Líder de Equipa de Integração de Sistemas)

... [conteúdo completo conforme resumo anterior] ...
```

---

## Documento 3 — notas_legais_operacionais

```md
# Notas Legais e Operacionais Relevantes (FE / AGT)

**Fonte:** Decreto Presidencial n.º 71/25 e comunicados oficiais do MinFin/AGT

- Decreto Presidencial n.º 71/25 (20 de março de 2025) entra em vigor em **20 de setembro de 2025**.  
- Revoga os Decretos 292/18 e 144/23.  
- Introduz obrigações de facturação eletrónica faseadas.  
- Grandes contribuintes e fornecedores do Estado: aplicação inicial.  
- “Factura Premiada” prevista para início a 1 de outubro de 2025.  
- O software **SAC5** deixa de ter validade fiscal a partir de 1 de setembro de 2025.  
- Regularização de softwares deve ser feita em até 15 dias após notificação.  
- Séries de faturas passam a ser emitidas exclusivamente pela AGT.  

**Fontes confirmadas:**
- [ucm.minfin.gov.ao](https://www.ucm.minfin.gov.ao/...)
- [ey.com](https://www.ey.com/pt_ao/technical/tax-alerts/novo-regime-juridico-das-facturas)
- [portaldocontribuinte.minfin.gov.ao](https://portaldocontribuinte.minfin.gov.ao/noticia?id=985537)
- [expansao.co.ao](https://expansao.co.ao/gestao/detalhe/facturacao-eletronica-no-novo-regime-67421.html)

**Contacto técnico AGT:** `sifp@minfin.gov.ao`
```

---

## Instruções ao Codex

1. Incorporar as informações dos três documentos acima no módulo interno de conhecimento.  
2. Atualizar o mapeamento SAF‑T AO → Faturação Electrónica conforme DS‑120.  
3. Validar endpoints e parâmetros REST/SOAP conforme homologação.  
4. Atualizar regras de erro e códigos fiscais.  
5. Armazenar histórico de versões e data (08/10/2025).  
6. Criar alertas para verificação periódica (a cada 30 dias) de novas versões DS‑120 e decretos associados.

---
