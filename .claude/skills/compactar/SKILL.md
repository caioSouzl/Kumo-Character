---
name: compactar
description: Resume a conversa inteira em 5 a 7 pontos prontos para colar num chat novo. Use quando o usuário escrever "compactar" (sozinho ou como pedido, com ou sem barra, com ou sem acento) ou pedir para resumir a conversa para continuar em outro chat.
---

# compactar

Quando o usuário escrever **compactar**, produza um resumo da conversa **inteira** (do primeiro pedido até agora) para ele copiar e colar num chat novo, de modo que outro assistente consiga continuar o trabalho sem perder nada importante.

## Regras

1. **De 5 a 7 pontos numerados, nem mais nem menos.** Agrupe assuntos relacionados para caber.
2. **Contexto crítico:** objetivo do projeto, repositório e branch, caminhos de arquivos importantes, ambiente e ferramentas (versões, comandos de execução), restrições e preferências do usuário (por exemplo, começar as mensagens pelo nome dele e responder em português).
3. **Decisões:** o que foi aprovado, recusado ou adiado, e por quê. Diga o estado de cada item: aprovado, em avaliação ou descartado. Inclua números medidos importantes, sempre os valores reais, nunca inventados nem arredondados sem avisar.
4. **Trechos de código:** inclua os trechos essenciais para retomar o trabalho, como comandos de execução, parâmetros escolhidos e funções-chave. Copie-os exatamente como estão, em blocos com a linguagem indicada e só com as linhas que importam.
5. **Pendências:** feche com o próximo passo combinado e o que está aguardando decisão do usuário. Isso pode ficar dentro do último ponto.
6. **Nada inventado:** se algo não foi verificado ou ficou incompleto, diga isso.
7. **Idioma:** o mesmo da conversa.

## Formato de saída

- Uma linha curta antes do bloco, por exemplo: "Caio, aqui está o resumo para colar no chat novo:". Siga a preferência de saudação do usuário, se houver.
- **Todo o resumo dentro de um único bloco de código** cercado por quatro crases e a palavra `markdown`, para que ele copie de uma vez. Use quatro crases porque o resumo contém blocos internos de três crases.
- Dentro do bloco:
  - primeira linha: `# Contexto para continuar — <nome do projeto> (<data>)`;
  - depois, os pontos numerados de 1 a 5–7, cada um com um título curto em negrito e o conteúdo em tópicos;
  - trechos de código dentro do ponto a que pertencem, em blocos de três crases.
- Depois do bloco, não escreva mais nada.

## Ambiente Claude Code (terminal, app desktop, web)

Use esta seção quando a conversa acontecer no Claude Code, que é um ambiente de programação com acesso a arquivos e terminal, e não num chat comum.

1. **Mesmo formato:** continue com 5 a 7 pontos, o bloco único de quatro crases e a linha de abertura. A diferença está só no conteúdo.
2. **Repositório e branch:** diga o caminho do projeto e o branch ativo. Se houve commit ou push, diga o hash ou o nome do branch, nunca invente.
3. **Arquivos:** liste os caminhos alterados ou criados nesta sessão, com o estado de cada um: salvo, commitado, enviado ou só no disco.
4. **Comandos:** copie só os comandos que foram executados e que importam para retomar, como testes, builds e scripts de render, com o resultado real (passou, falhou, valor medido).
5. **Ferramentas externas:** cite o que estava conectado (MCP, sessões remotas, capacidades de página) e o que não foi testado de verdade.
6. **Não copie o conteúdo de arquivos grandes** nem saídas de terminal longas. Resuma e aponte o caminho.
7. **Ao final:** se o usuário pedir, grave o resumo também em um arquivo `RESUMO-<data>.md` na raiz do projeto ou no rascunho da sessão, mas só quando ele pedir.
