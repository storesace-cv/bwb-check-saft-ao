# Futuro do projeto

Este projeto continuará a ser mantido pelo **Codex GPT** e pela comunidade.
O foco é evoluir de um conjunto de scripts isolados para uma ferramenta
modular, bem testada e fácil de operar por utilizadores técnicos e não técnicos.

## Prioridades de curto prazo
- **Reorganizar** a estrutura de ficheiros para privilegiar o pacote `src/saftao`
  como fonte de verdade, mantendo os scripts legados apenas como _wrappers_.
- **Mapear o estado atual** do código (scripts, CLI e módulos) e propor melhorias
  na coesão entre eles.
- **Melhorar a documentação** com fluxos de utilização, exemplos de entrada e
  saída e tabelas de referência às regras AGT.
- **Automatizar a validação básica** com _linters_ e testes unitários para as
  funções críticas de arredondamento e reconciliação de totais.
- **Integrar Faturação Eletrónica (FE)** alinhando o mapeamento SAF-T (AO) ↔
  DS-120, cobrindo endpoints REST/SOAP de homologação e tabelas de códigos.
- **Configurar alertas recorrentes** (a cada 30 dias) para rever versões DS-120 e
  decretos AGT relacionados, mantendo o histórico de revisões no repositório.

## Evolução de médio prazo
- Criar um modo "assistido" na CLI com mensagens mais descritivas e guias sobre
  como resolver erros frequentes.
- Consolidar a lógica de correção "soft" e "hard" numa API comum para facilitar
  integrações com outros sistemas.
- Publicar _artifacts_ reprodutíveis (p. ex. `pipx`, _container_) para facilitar a
  adoção em ambientes corporativos.

## Visão de longo prazo
- Disponibilizar um painel web leve para carregar SAF-T, executar validações e
  descarregar relatórios.
- Integrar com serviços de arquivo para guardar _logs_ e históricos de execução.
- Contribuir de volta para a comunidade SAF-T (AO) através de guias e exemplos
  oficiais revistos.
