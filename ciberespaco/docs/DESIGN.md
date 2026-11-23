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

- Chão de circuitos azuis e roxos que correm para o horizonte e se desfazem em
  pontos até sumir no céu roxo escuro.
- No meio, um campinho redondo de grama com flores, pedras e brinquedos nas
  bordas (bola, blocos, carrinho, pião).
- No campo, um tronco retorcido com um terrário de vidro no topo: a cama do Kumo.
- Na frente do campo, a plataforma quadrada onde o ZodIA projeta os objetos.

## Ciclo

1. O ZodIA começa um projeto. Lasers roxos "desenham" cada peça de baixo para
   cima, em roxo translúcido. Sem interferência, um projeto leva 2 min
   (`project_build_sec`).
2. O Kumo começa dormindo no terrário. Em ~1 min (`kumo_wake_sec`) aparece
   "Kumo está acordando!", a câmera mostra o Kumo descendo da árvore, e daí em
   diante ele brinca com os brinquedos ou fica observando o ZodIA.
3. Projeto pronto: ZodIA fica orgulhoso, o objeto se desfaz e começa o próximo.
   Todos prontos: óculos da vitória, e a lista recomeça embaralhada.

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
| Perfume | `zodia_trip` | Kumo rola por baixo do ZodIA, que cai; a peça em construção racha e volta ao começo (assustado → inexpressivo → confuso → chateado). |
| Galáxia | `kumo_knockdown` | Kumo pula na plataforma e derruba tudo. Painel holográfico se quebra, ZodIA fica enfurecido, choraminga e recomeça o projeto. |

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
