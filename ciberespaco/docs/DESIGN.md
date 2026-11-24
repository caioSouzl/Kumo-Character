# Ciberespaço: documento de design

Jogo para lives interativas. O ZodIA, assistente de IA do Criador, tenta
terminar projetos holográficos enquanto o Kumo, curioso, atrapalha quando a
live manda o presente certo. Base: apresentação "Ciberespaço" no Canva.

## Decisões fechadas

| Tema | Decisão |
|---|---|
| Engine | Godot 4.4, renderizador Mobile, qualidade mínima (sem sombras em tempo real, escala 3D 0.8) |
| Tela | 3D, vertical 9:16 (1080 x 1920) |
| Câmera | Foca o ZodIA quase sempre; às vezes (ou quando um presente mexe com o Kumo) foca o Kumo |
| Modelos | Provisórios em formas simples; os .glb do Hyper3D entram sem mexer no código (`assets/models/`) |
| Presentes | Configuráveis em `config/gifts.json` |
| Projetos | Configuráveis em `config/projects.json` (objetos reais em formas simples) |
| Live | Simulador primeiro; a live real entra pelo mesmo WebSocket do Kumo Pizzaria |

## Cenário

- Campo redondo de grama com 40 m de raio, borda ondulada. Na borda a grama
  se desfaz em quadradinhos (pixels) e o circuito aparece por baixo: o campo se
  mistura com o espaço digital.
- Árvore do Hyper3D no centro (60% maior), com o terrário de vidro onde o
  Kumo dorme. Brinquedos (bola, bloco, carrinho, argolas, balanço) a 10 m da
  árvore. O balanço é 50% maior e funciona: às vezes o Kumo senta e balança.
- Ninguém atravessa o tronco: o Kumo contorna a árvore, e a câmera fica sempre
  do lado de fora (corta direto quando o alvo muda para o outro lado).
- Pedras, moitas com flores, tufos de grama e caminho de pedras chatas.
- Fora do campo: placa de circuito escura com trilhas, vias e chips, que se
  desfaz no horizonte roxo.
- Paredes invisíveis na borda: nada sai do mapa. Kumo e ZodIA não andam para
  fora. A única exceção é a queda do ZodIA, que pode passar do limite.

## Ciclo

1. O ZodIA escolhe um lugar livre do campo, perto de onde está, sem árvore,
   pedras, brinquedos nem objetos que ele já fez. A plataforma aparece ali e
   ele vai até ela.
2. Com os dois braços estendidos para frente, ele dispara dois lasers roxos
   que "desenham" cada peça de baixo para cima. Sem interferência, um projeto
   leva 2 min (`project_build_sec`).
3. Projeto pronto: a câmera mostra o objeto, o ZodIA comemora, a plataforma
   some e **o objeto fica no mapa**. O próximo projeto vai para outro lugar
   livre. Acima de `max_built_objects`, o objeto mais antigo some.
4. Todos os projetos prontos: óculos da vitória, e a lista recomeça.
5. O Kumo começa dormindo no terrário. Em ~1 min (`kumo_wake_sec`) acorda,
   desce da árvore e passa a brincar ou observar. Anda em pé devagar e corre
   de quatro patas (`kumo.quad_above_speed`). O passo é medido pela perna do
   modelo e avança pela distância andada (sem pés patinando); no trote as
   pernas abrem para os lados e o corpo e a cauda ondulam, como um lagarto.

## Câmera

- Foca o ZodIA e as reações dele aos eventos.
- Foca o Kumo nas ações de evento dele (acordar, ir aprontar).
- Foca o objeto quando ele fica pronto e quando está quebrando.

## Quebra

O painel "Projeto derrubado!" aparece e estoura em meio segundo, antes do
efeito no objeto. Depois: rachado (linhas de falha piscando, o objeto treme) → se despedaça em
estilhaços → os estilhaços caem no chão → somem. Vale para a derrubada
(Galáxia: o objeto todo) e para o tombo (Perfume: só a peça em construção).

## Bateria (curtidas)

- A bateria cai sozinha (`drain_per_sec`); cada curtida recarrega (`per_like`).
- Abaixo de `low_at`: ZodIA fica lento, rosto "bateria fraca" e aviso
  "ZodIA está ficando sem bateria! Curta para recarregar."
- Em 0: rosto "sem bateria", ele afunda e para. Volta quando receber curtidas.

## Presentes

Todo presente gera um quadro de agradecimento ("Obrigado @usuario, pelas X
rosas!") no estilo ZodIA (neon) ou Kumo (folhas), e soma pontos no ranking
"Top presenteadores" (estilo misto).

| Presente | Evento | O que acontece |
|---|---|---|
| Rosa | `recharge` | Recarrega a bateria. |
| Heart Me | `zodia_boost` | ZodIA constrói mais rápido por um tempo (acumula). |
| GG | `kumo_wake` | Acorda o Kumo na hora. |
| Finger Heart | `kumo_bump` | Kumo esbarra na plataforma: o projeto treme mas não cai (assustado → aliviado). |
| Rosquinha | `kumo_spin` | Kumo passa correndo pertinho e o ZodIA rodopia (confuso). |
| Perfume | `zodia_trip` | Kumo rola por baixo do ZodIA, que cai; a peça em construção e a anterior racham e somem (assustado → inexpressivo → confuso → chateado). |
| Galáxia | `kumo_knockdown` | Kumo derruba o projeto em construção; se ele mal começou, derruba um objeto pronto do mapa (o mais perto). Painel holográfico se quebra, ZodIA fica enfurecido, choraminga e recomeça o projeto. |

Se o Kumo estiver dormindo quando chega uma sabotagem, ele acorda rápido e já
vai aprontar. A fila de eventos funciona como no Kumo Pizzaria: ordem de
chegada, no máximo um a cada 3 s, sabotagens seguram a fila até a animação
terminar.

## Expressões do ZodIA

Desenhadas na tela do rosto (`scripts/world/zodia_face.gd`): normal (pisca),
chateado, inexpressivo, desconfiado (Kumo chegou perto ou acordou), assustado,
aliviado, confuso, bateria fraca, sem bateria, enfurecido, choramingando,
orgulhoso e óculos da vitória.

## Próximos passos

1. Trocar os modelos provisórios pelos do Hyper3D (ZodIA, Kumo, ambiente) e
   ajustar a tela-rosto no modelo final (`models.zodia_face` em `config/game.json`).
2. Sons: lasers, quebra do holograma, Kumo, ZodIA.
3. Conectar a live real (mesma ponte do Kumo Pizzaria, agora com curtidas).
4. Mais projetos em `config/projects.json`.
5. Exportar para Android/PC.

## Quadros da live

Toda a arte dos quadros foi desenhada para o jogo (`assets/ui/*.svg`), sem
usar elementos do Canva. Fontes livres (licença OFL, em `assets/fonts/`):
Orbitron (ZodIA) e Baloo 2 (Kumo).

| Estilo | Visual | Entrada |
|---|---|---|
| ZodIA | painel escuro, cantos chanfrados, borda neon magenta + ciano, trilhas de circuito, varredura de holograma | piscadelas de neon ou glitch (sorteado); glitch curto de vez em quando |
| Kumo | painel creme, borda de madeira, cipó, folhas, flores e pedrinhas | brota com as folhas crescendo; folhas balançam |
| Ranking (misto) | painel neon com folhagem, coroa no 1º lugar | quem sobe pisca; o 1º faz a coroa pular |

Agradecimentos mostram a inicial de quem mandou e o ícone do presente.
`thanks_one` em `config/gifts.json` é o texto para 1 presente ("pela rosa").

## Anéis de flutuação

Embaixo do ZodIA, dois anéis em loop: saem pequenos de baixo dele, descem
crescendo e somem. Indicam que ele funciona e flutua: desaparecem quando ele
cai ou fica sem bateria.

## Painéis em SVG (editáveis fora do Godot)

Os painéis podem ser desenhados em arquivos SVG em `assets/ui/paineis/` e
abertos no Figma, Inkscape ou navegador. O Godot importa o arquivo e usa como
fundo do painel. Primeiro exemplar: `ranking.svg` (usado pelo "Top
presenteadores"). Para trocar um painel, substitua o SVG mantendo o tamanho
indicado no código.
