# AGT SAF-T (AO) rules summary

_Last generated: 2025-11-06T15:23:16.576998+00:00_

## Documents

| Title | Type | Date | Version | Entities | Source |
| --- | --- | --- | --- | --- | --- |
|  Diario da Republica - Série - N.º 52 | - | - | - | - | `rules_updates/agt/ Diario da Republica - Série - N.º 52.pdf` |
| DIRECÇÃO DE COBRANÇA, REEMBOLSO E RESTITUIÇÕES | - | - | - | AGT, CIVA, IVA, SAF-T (AO), Software | `rules_updates/agt/799d189a-c2e9-4732-84d9-5bd00d5afc34.pdf` |
| Circular 20 1756751309 | circular | - | - | - | `rules_updates/agt/Circular_20_1756751309.pdf` |
| Circular AGT Mudança de Softwares 20 1756751309[1] Copy | circular | - | - | - | `rules_updates/agt/Circular_AGT_Mudança de Softwares_20_1756751309[1] Copy.pdf` |
| Comunicado - MINSA-ÓRGÃO CENTRAL CP2022 ENAPP-ERU | - | - | - | - | `rules_updates/agt/Comunicado - MINSA-ÓRGÃO CENTRAL_CP2022_ENAPP-ERU.pdf` |
| DECRETO EXECUTIVO 683 25 DEFINE A ESTRUTURA DE DAD 250828 092409 | decreto | - | - | - | `rules_updates/agt/DECRETO EXECUTIVO 683_25 DEFINE A ESTRUTURA DE DAD_250828_092409.pdf` |
| Decreto Presidencial n.º 71-25 | decreto | - | - | - | `rules_updates/agt/Decreto Presidencial n.º 71-25.pdf` |
| diploma que define a estrutura de dados de software (1) | - | - | - | - | `rules_updates/agt/diploma que define a estrutura de dados de software (1).pdf` |
| DS.120 DESIGN SERVICES CONSTRUCTION | - | 2025-08-14 | - | AGT, IVA, Software | `rules_updates/agt/DS-120 Especificação Técnica Consulta de Contribuinte - Consultar (Produtores de Software) v5.0.1.pdf` |
| OUM | - | 2025-10-01 | - | AGT, CIVA, IVA, SAF-T (AO), Software | `rules_updates/agt/DS-120.Especificacao.Tecnica.FE.v1.0.pdf` |
| DIRECÇÃO DE COBRANÇA, REEMBOLSO E RESTITUIÇÕES | - | - | - | AGT, CIVA, IVA, SAF-T (AO), Software | `rules_updates/agt/ESTRUTURA DE DADOS DE SOFTWARE MODELO DE FACTURAÇÃO ELECTRÓNICA ESPECIFICAÇÕES TÉCNICAS E PROCEDIMENTA.pdf` |
| DIRECÇÃO DE COBRANÇA, REMBOLSO E RESTITUIÇÕES | - | - | - | AGT, CIVA, IVA, SAF-T (AO), Software | `rules_updates/agt/ESTRUTURA_DE_DADOS_DE_SOFTWARE_MODELO_DE_FACTURAÇÃO_ELECTRÓNICA.pdf` |
| REGRAS E REQUISITOS PARA VALIDAÇÃO DE SISTEMAS | decreto | - | - | AGT, IVA, SAF-T (AO), Software | `rules_updates/agt/minfin055809.pdf` |
| PROJECTO DE DECRETO EXECUTIVO | decreto | - | - | AGT, IVA, SAF-T (AO), Software | `rules_updates/agt/Projecto_Decreto_Executivo_regras_e_requisitos_para_validação.docx` |
| # 📘 AGT — Regras, Comunicados e Atualizações Oficiais | circular | 2024-12-15 | - | AGT, IVA, SAF-T (AO) | `rules_updates/agt/readme.txt` |
| DS.120 DESIGN SERVICES CONSTRUCTION | - | 2023-09-22 | - | AGT, CIVA, IVA, Software | `rules_updates/agt/TA.020 Technical Architecture Requirements and Strategy.pdf` |

## Rules

| Rule ID | Scope | Applies Since | Description | Constraints | Sources |
| --- | --- | --- | --- | --- | --- |
| agt.header.building_number.normalised | header.company_address.building_number | 2025-08-14 | BuildingNumber deve utilizar marcadores 'S/N' quando não existe número físico e rejeitar zeros. | allowed_markers: [S/N, SN]; forbidden_values: [0, 00, 000, 0000] | DS-120 Especificação Técnica Consulta de Contribuinte - Consultar (Produtores de Software) v5.0.1.pdf; DS-120.Especificacao.Tecnica.FE.v1.0.pdf; ESTRUTURA DE DADOS DE SOFTWARE MODELO DE FACTURAÇÃO ELECTRÓNICA ESPECIFICAÇÕES TÉCNICAS E PROCEDIMENTA.pdf; ESTRUTURA_DE_DADOS_DE_SOFTWARE_MODELO_DE_FACTURAÇÃO_ELECTRÓNICA.pdf; minfin055809.pdf |
| agt.header.postal_code.placeholder | header.company_address.postal_code | 2025-08-14 | PostalCode deve ser reduzido para '0000' quando o valor presente for '0000-000'. | placeholder: 0000; alias: 0000-000 | DS-120 Especificação Técnica Consulta de Contribuinte - Consultar (Produtores de Software) v5.0.1.pdf; DS-120.Especificacao.Tecnica.FE.v1.0.pdf; ESTRUTURA DE DADOS DE SOFTWARE MODELO DE FACTURAÇÃO ELECTRÓNICA ESPECIFICAÇÕES TÉCNICAS E PROCEDIMENTA.pdf; ESTRUTURA_DE_DADOS_DE_SOFTWARE_MODELO_DE_FACTURAÇÃO_ELECTRÓNICA.pdf; minfin055809.pdf |
| agt.header.tax_registration_number.digits_only | header.tax_registration_number | 2025-10-01 | TaxRegistrationNumber deve conter apenas dígitos (sem prefixos ou espaços). | format: digits-only; pattern: ^[0-9]+$; strip_non_digits: True | 799d189a-c2e9-4732-84d9-5bd00d5afc34.pdf (p. 5, 8, 22, 25, 27, 30, 33, 37, 38); DS-120.Especificacao.Tecnica.FE.v1.0.pdf (p. 8, 10, 12, 13, 19, 20, 22, 24, 26, 27, 28, 30, 32, 33); ESTRUTURA DE DADOS DE SOFTWARE MODELO DE FACTURAÇÃO ELECTRÓNICA ESPECIFICAÇÕES TÉCNICAS E PROCEDIMENTA.pdf (p. 5, 8, 22, 25, 27, 30, 33, 37, 38); ESTRUTURA_DE_DADOS_DE_SOFTWARE_MODELO_DE_FACTURAÇÃO_ELECTRÓNICA.pdf (p. 5, 7, 19, 22, 23, 24, 26, 28, 29, 33); minfin055809.pdf (p. 25) |
| agt.tax.country_region.required | tax.country_region | 2025-10-01 | TaxCountryRegion é obrigatório e deve usar o código 'AO' quando aplicável. | required: True; allowed_values: [AO] | 799d189a-c2e9-4732-84d9-5bd00d5afc34.pdf; DS-120.Especificacao.Tecnica.FE.v1.0.pdf; ESTRUTURA DE DADOS DE SOFTWARE MODELO DE FACTURAÇÃO ELECTRÓNICA ESPECIFICAÇÕES TÉCNICAS E PROCEDIMENTA.pdf; ESTRUTURA_DE_DADOS_DE_SOFTWARE_MODELO_DE_FACTURAÇÃO_ELECTRÓNICA.pdf |

