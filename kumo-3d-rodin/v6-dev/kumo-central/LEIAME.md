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

## Próximas fases
3. Painel de etapas e tarefas.
4. Assistente Claude com contexto e fila de pedidos.
5. Botões próprios, layouts e atalhos.
