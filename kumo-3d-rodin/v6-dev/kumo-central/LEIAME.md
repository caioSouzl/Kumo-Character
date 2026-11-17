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

## Próximas fases
2. Explorador de componentes e gerenciador de versões.
3. Painel de etapas e tarefas.
4. Assistente Claude com contexto e fila de pedidos.
5. Botões próprios, layouts e atalhos.
