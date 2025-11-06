# AGT rules changelog

## 2025-11-06 – Automated ingestion

- **Documents added:**  Diario da Republica - Série - N.º 52.pdf, ESTRUTURA DE DADOS DE SOFTWARE MODELO DE FACTURAÇÃO ELECTRÓNICA ESPECIFICAÇÕES TÉCNICAS E PROCEDIMENTA.pdf, Circular_20_1756751309.pdf, Circular_AGT_Mudança de Softwares_20_1756751309[1] Copy.pdf, Comunicado - MINSA-ÓRGÃO CENTRAL_CP2022_ENAPP-ERU.pdf, DECRETO EXECUTIVO 683_25 DEFINE A ESTRUTURA DE DAD_250828_092409.pdf, Decreto Presidencial n.º 71-25.pdf, diploma que define a estrutura de dados de software (1).pdf, DS-120 Especificação Técnica Consulta de Contribuinte - Consultar (Produtores de Software) v5.0.1.pdf, DS-120.Especificacao.Tecnica.FE.v1.0.pdf, ESTRUTURA_DE_DADOS_DE_SOFTWARE_MODELO_DE_FACTURAÇÃO_ELECTRÓNICA.pdf, minfin055809.pdf, Projecto_Decreto_Executivo_regras_e_requisitos_para_validação.docx, readme.txt, TA.020 Technical Architecture Requirements and Strategy.pdf
- **Rules added:** agt.header.tax_registration_number.digits_only, agt.tax.country_region.required
- **Impacted modules:** src/saftao/autofix/_header.py, src/saftao/validator.py
- **Recommended actions:** Re-run `python scripts/agt_ingest_rules.py --rebuild` and ensure validators consume the refreshed constraints.

<!-- digest:0b1792f497f4af802ca0076e976df9af7985edf1c58ba9e9b72902e30a038a72 -->
## 2025-11-06 – Automated ingestion

- **Rules added:** agt.header.building_number.normalised, agt.header.postal_code.placeholder
- **Rules updated:** agt.header.tax_registration_number.digits_only, agt.tax.country_region.required
- **Impacted modules:** src/saftao/autofix/_header.py, src/saftao/validator.py
- **Recommended actions:** Re-run `python scripts/agt_ingest_rules.py --rebuild` and ensure validators consume the refreshed constraints.

<!-- digest:d354291728d44c711b32d7850724c060b4f6e094119f4f396e9c642d8b627dc6 -->
## 2025-11-06 – Automated ingestion

- **Rules updated:** agt.header.tax_registration_number.digits_only, agt.tax.country_region.required
- **Impacted modules:** src/saftao/autofix/_header.py, src/saftao/validator.py
- **Recommended actions:** Re-run `python scripts/agt_ingest_rules.py --rebuild` and ensure validators consume the refreshed constraints.

<!-- digest:2915cfc88ada11c04432757f71b4f66f965cb61641f2e9115401d4e709a25465 -->
