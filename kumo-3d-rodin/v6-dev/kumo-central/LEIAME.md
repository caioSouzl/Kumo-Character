# Central do Kumo (página de teste)

Evolução do Estúdio do Kumo para uma central de desenvolvimento, feita em fases. O Estúdio original (`../kumo-studio/`) continua intacto até o Caio aprovar esta página.

O modelo é o mesmo do Estúdio (`../kumo-studio/kumo.glb`); esta pasta não guarda uma cópia.

## Fase 1 (feita): reorganização visual e navegação
- **Barra de visualização:**
  - vistas (padrão, frente, lado, costas, cima);
  - perspectiva ou ortográfica;
  - modo de exibição (material, sólido, aramado);
  - enquadrar;
  - tema (sistema, claro, escuro).
- **Abas por assunto:** Pose, Mãos, Rosto (olhos, boca e língua), Animação, Projeto (troca com o Blender e opções).
- **Novo:** controles de boca e língua, com a animação "Lançar a língua". A língua segue as mesmas contas do `.blend`.
- **Mantido:** tudo o que o Estúdio fazia (pose, puxar mão ou pé, mãos, cauda, olhos, losangos, ombro automático, linha do tempo, copiar para o Blender).

## Testes da Fase 1
Navegador automático, em tela de computador e de celular:
- sem erros de script;
- vistas, ortográfica, sólido, aramado e tema trocam;
- boca e língua entram na pose copiada;
- ombro automático, losangos e pontos de articulação continuam funcionando.

## Problemas conhecidos
- Com a boca aberta, o contorno marrom aparece esticado em volta da abertura: o contorno do modelo ainda não foi cortado na boca.
- Em "sólido" e "aramado", os olhos continuam com o material normal.

## Fase 2 (feita): componentes e versões
- **Aba Componentes:** as peças reais do modelo, em 7 grupos.
  - Corpo: uma malha só, dividida em 12 regiões pelos ossos.
  - Olho esquerdo e olho direito: 9 camadas cada.
  - Boca e língua.
  - Contorno.
  - Esqueleto.
  - Materiais e texturas.
  - Ações: selecionar (mostra a ficha e foca a câmera), ocultar ou exibir (só as peças de verdade), e travar.
  - As cristas aparecem como pintura na textura, porque não são peças.
- **Aba Versões:** 20 versões registradas, cada uma com situação, data, descrição, alterações, testes, arquivos e relatório. Duas versões podem ser comparadas lado a lado pela imagem.
  - A lista vem de `versoes.json`, gerado por `gerar_versoes.py` a partir das pastas reais.
  - Para atualizar: editar a lista no script, rodar e publicar de novo.
- **Correção:** o painel agora rola por dentro, sem empurrar o palco.
- **Testes:** em tela de celular, sem erros de script:
  - seleção, ficha, trava (a cauda travada recusa a seleção) e ocultar o contorno;
  - 20 versões carregadas;
  - comparação de duas versões.
- **Limites:**
  - ocultar e travar valem só na tela, e voltam ao normal ao recarregar;
  - a comparação é por imagem, não por modelo 3D;
  - a situação de cada versão foi tirada dos relatórios e do `DECISOES.md`, e o Caio deve corrigir o que estiver errado.


## Fase 3 (feita): etapas e tarefas
- **Aba Etapas:** 9 etapas do projeto (Modelagem até Exportação) com 46 tarefas.
  - Situações: pendente, em andamento, aguardando aprovação e feita. Um toque na tarefa troca a situação.
  - Cada etapa mostra o percentual (tarefas feitas sobre o total); o resumo mostra 4 números.
  - Formulários para criar tarefa e etapa nova.
- **Dados salvos de verdade:** ficam no banco da própria página (coleções `etapas` e `tarefas`) e atualizam ao vivo.
  - Só o dono (Caio) pode escrever; quem só vê o link pode ler, mas não altera.
  - Situação inicial: 26 feitas, 1 em andamento, 19 pendentes.
- **Testes:**
  - página testada no celular com banco de teste: contagens e troca de situação certas, sem erros de script;
  - banco real conferido: 9 etapas e 46 tarefas lidas como visitante;
  - escrita como visitante recusada pelo banco (regra de dono funcionando).
- **Limites:** a lista de tarefas não se atualiza sozinha a partir do repositório; quem muda é o Caio na página (ou eu, quando ele pedir).

## Fase 4 (feita): assistente e fila de pedidos
- **Aba Assistente:** conversa com o Claude dentro da Central.
  - A cada mensagem ele recebe o estado da tela: aba aberta, componente escolhido, articulações fora do repouso, rosto, quadros da animação, etapas e tarefas, versões e a fila.
  - Pode mexer na pose, no rosto e nas poses prontas **só na tela** (tudo volta com Desfazer). Abaixo da resposta aparece o que ele mexeu.
  - Não abre arquivos, não usa o Blender e não altera o projeto. Quando o pedido exige isso, ele mostra um **rascunho de pedido**; só entra na fila quando o Caio toca em "Adicionar à fila".
  - Usa a conta do claude.ai de quem está vendo (sem chave de API na página). Na primeira pergunta o claude.ai pede permissão.
- **Fila de pedidos** (coleção `pedidos` no banco da página):
  - situações: novo, lido, em andamento, feito, recusado;
  - pedido que mexeria nos arquivos oficiais tem a caixa "Autorizo…", desmarcada por padrão;
  - o Claude Code lê a fila quando o Caio pede na conversa e escreve a resposta no pedido. A página não chama o Claude Code sozinha.
  - só o dono escreve; quem só vê, lê.
- **Testes:** no celular, com um Claude simulado: o contexto chegou completo; girar o braço, abrir a boca, articulação inexistente recusada, rascunho com aviso de arquivo oficial, adicionar à fila, autorizar, trocar situação, pedido escrito à mão, Desfazer, sem rolagem lateral e sem erros. No banco real: escrita de visitante recusada.
- **Limites:** a conversa some ao recarregar a página; o assistente não vê as imagens do palco; cada pergunta gasta o uso do claude.ai de quem pergunta.

## Fase 5 (feita): botões próprios, layouts e atalhos
- **Aba Personalizar:**
  - **Meus botões:** cada botão guarda a pose atual (corpo, mãos e rosto), a vista atual (câmera e modo) ou a animação atual. Tem nome, cor, tecla opcional e pode ficar na barra do palco. Dá para usar, mudar a ordem, regravar, renomear, tirar da barra e apagar.
  - **Layouts:** escolhem as abas que aparecem, a aba que abre, o tamanho do palco no celular, o lado do painel no computador e quais barras aparecem. São 4 prontos (Completo, Rosto, Animação, Revisão), e o Caio pode salvar os dele. O layout em uso fica lembrado em cada aparelho. A aba Personalizar nunca some.
  - **Atalhos de teclado:** Esc, Espaço, K, Ctrl+Z e Ctrl+Y, F (enquadrar), O (ortográfica), M (modo), 1 a 5 (vistas), L (próximo layout) e as teclas dos botões.
- **Barra do palco:** troca de layout e os botões marcados. No celular, faz o papel dos atalhos.
- **Assistente:** vê os botões e o layout em uso e pode apertar um botão com `usar_botao`, só na tela.
- **Dados:** coleções `botoes` e `layouts` no banco da página. Só o dono escreve; quem só vê, lê.
- **Correções:** os losangos da linha do tempo ficavam enormes no celular; a aba aberta agora rola para a vista; o sublinhado deixou de ficar preso na aba tocada.
- **Testes:** no celular (Pixel 7) com banco simulado, sem erros de script:
  - criar botão de pose, de vista e de animação;
  - recusa de tecla reservada e de animação sem quadros;
  - usar pela barra;
  - trocar a ordem;
  - os 4 layouts prontos, salvar um layout próprio;
  - sem rolagem lateral.
- **Limites:** os ajustes no editor de layout valem só na tela até serem salvos; um botão de animação aceita até cerca de 200 mil caracteres de dados.
