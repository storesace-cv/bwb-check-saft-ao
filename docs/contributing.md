# Guia de Contribuição

1. Instale as dependências listadas em `requirements.txt` dentro de um ambiente
   virtual dedicado.
2. Execute os testes com `pytest` antes de submeter alterações.
3. Ao migrar lógica dos scripts antigos, assegure-se de cobrir os novos módulos
   com testes e documentação adequados.

## Registo de alterações efectuadas pelo Codex

Sempre que o Codex adicionar blocos de código deve inserir imediatamente acima
dos novos trechos a linha de separador

```
#    -------- adicionado pelo Codex a <timestamp>  --------
```

utilizando a data e hora de Portugal (fuso horário `Europe/Lisbon`) no formato
ISO 8601, incluindo o desvio horário, por exemplo
`2025-10-07T11:37:03+01:00`.

Para remoções de código, acrescente antes da secção eliminada o marcador

```
#    -------- removido pelo Codex a <timestamp>  --------
```

também com data e hora de Portugal no mesmo formato. Estes registos facilitam a
auditoria das alterações automatizadas efectuadas pela ferramenta.
#    -------- adicionado pelo Codex a 2025-10-07T12:08:26+01:00  --------
Além disso, comentários adicionados em commits anteriores aos dois mais recentes
devem ser removidos ao atualizar ficheiros. Assim preservam-se apenas as
anotações que refletem o histórico imediato, evitando acumular contexto
desatualizado.

## Resolução de conflitos de merge no GitHub

Quando o GitHub detecta conflitos num ficheiro (por exemplo, `src/saftao/gui.py`)
durante um _Update branch_ ou na abertura de um Pull Request, a interface oferece
três opções para cada bloco em conflito:

1. **Accept current change** – mantém o conteúdo da _branch_ que está a ser
   atualizada (as alterações que acabou de enviar).
2. **Accept incoming change** – substitui o bloco pelo conteúdo da _branch_ base
   (normalmente `main` ou a _branch_ alvo do PR).
3. **Accept both changes** – coloca os dois blocos consecutivamente para que o
   conflito seja resolvido manualmente mais tarde.

Se a intenção for preservar o trabalho recente que acabou de desenvolver, em geral
deve escolher **Accept current change**. Ainda assim, é importante rever o bloco
para confirmar que nenhuma atualização importante da _branch_ base está a ser
descartada. Caso ambas as versões contenham partes relevantes, escolha **Accept
both changes** e edite o resultado final de forma a combinar manualmente o melhor
de cada lado antes de concluir o merge.
