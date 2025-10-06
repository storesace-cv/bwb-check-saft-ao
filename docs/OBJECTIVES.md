# Objetivos do projeto

Este repositório disponibiliza ferramentas para validar e corrigir ficheiros
SAF-T (AO) segundo as normas da AGT. A visão de produto assenta nos seguintes
pilares:

## Conformidade
- Validar ficheiros SAF-T (AO) contra o XSD oficial e um conjunto de regras
  fiscais adicionais exigidas pela AGT.
- Garantir cálculos fiáveis de totais (`NetTotal`, `TaxPayable`, `GrossTotal`),
  arredondamentos (`q2`, `q6`) e percentagens de imposto coerentes.

## Correção assistida
- Disponibilizar modos de correção "soft" e "hard" para ajustar ficheiros com
  erros comuns sem intervenção manual extensa.
- Produzir relatórios em Excel com códigos de erro, sugestões e dados de apoio
  que acelerem a revisão por equipas de contabilidade ou auditoria.

## Evolução contínua
- Migrar gradualmente a lógica dos scripts legados para o pacote `src/saftao`,
  tornando o projeto mais fácil de testar, publicar e integrar.
- Manter documentação atualizada (arquitetura, _how-to_, notas legais) para
  reduzir a curva de aprendizagem e incentivar contributos externos.
