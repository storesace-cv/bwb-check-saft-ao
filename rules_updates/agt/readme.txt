# 📘 AGT — Regras, Comunicados e Atualizações Oficiais

Esta pasta contém **documentos oficiais da Administração Geral Tributária de Angola (AGT)** relacionados com o **SAF-T (AO)**, **faturação certificada** e demais legislação fiscal aplicável aos produtos da BWB / StoresAce-CV / ZoneSoft-AO e seus parceiros.

Os ficheiros aqui incluídos (PDF, DOCX, MD, etc.) destinam-se a:
- servir de **referência normativa** para validações internas de ficheiros SAF-T (AO);
- manter histórico de **circulares, despachos e orientações técnicas** emitidas pela AGT;
- suportar a **atualização contínua das regras de negócio e validação** implementadas nas ferramentas `bwb-check-saft-ao`, `bwb-saft-pt`, e módulos relacionados.

## 📂 Estrutura

rules_updates/
└── agt/
├── 2025-11-06_Circular_SAFT-AO_HeaderTaxBasis.pdf
├── 2025-10-01_Comunicado_Nova_Tabela_IVA.pdf
├── 2024-12-15_Guia_Submissao_Ficheiros_SAFT-AO.pdf
├── README.md  ← este ficheiro

## 🧭 Convenções

- Cada documento deve ter o nome no formato:  
  **AAAA-MM-DD_Título_Simplificado.pdf**
- Sempre que aplicável, indicar na descrição do *commit*:
  - o **tema principal** (ex.: “Nova tabela de IVA”, “Atualização de layout SAF-T”);
  - e a **data oficial de emissão** da AGT.

## 🧩 Integração com as aplicações

Os documentos desta pasta são referenciados automaticamente por:
- `src/lib/validators/rules_loader.py` — que atualiza as regras de validação em função das versões legais;
- `docs/en/codex/runners/` — onde são geradas notas técnicas e relatórios de impacto.

> ⚠️ **Nota:** Os ficheiros aqui armazenados são cópias públicas ou reencaminhadas pela própria AGT.  
> A BWB e parceiros apenas os conservam para efeitos de conformidade e consulta técnica.  
> Não substituem a publicação oficial no portal da AGT.
