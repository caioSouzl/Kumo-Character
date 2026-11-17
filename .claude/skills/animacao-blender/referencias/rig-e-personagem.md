# Rig e criação de personagem no Blender

Fonte: 43 vídeos de @tiago_prlco (TikTok), estudados em 17/11 pela transcrição das narrações. São três séries: rig de corpo (17 dias), rig de rosto (16 dias) e criação de personagem (6 partes). Um vídeo de dúvidas, de 153 s, não tinha fala reconhecível e ficou de fora.

A coluna "No Kumo" diz o que já temos e o que vale trazer.

## 1. As três camadas de ossos
Um rig de animação separa os ossos por função:
- **Deformadores:** os únicos que deformam a malha. No rig do autor são 25 de 149 no braço; no fim, cerca de 500 ossos, com 177 controladores.
- **Mecânicos:** não deformam; montam a lógica (centralizar parentesco, servir de alvo, ligar e desligar comportamentos).
- **Controladores:** os únicos que o animador toca.

A cadeia é: o controlador move os tweaks, os tweaks movem os deformadores, e os deformadores movem a pele.

**No Kumo:**
- Hoje o animador mexe direto nos deformadores. Os únicos controladores são `controle_olhos`, `controle_olhar` e `lingua_controle`.
- **Para o jogo, só os deformadores e as shape keys exportam.** Constraints, bendy bones e spline IK não vão para o Godot: a animação precisa ser assada (baked) nos deformadores antes de exportar.

## 2. Pintura de peso
- **Grupo = nome do osso:** um grupo de vértices funciona porque tem o mesmo nome do osso. "With Automatic Weights" só cria esses grupos sozinho.
- **Os pesos são relativos (a regra das cordas):** cada osso é uma corda puxando o vértice. Um osso com 50% de peso sozinho move o vértice 100%, porque nenhuma outra corda puxa. Dar 100% ao osso certo não basta; é preciso garantir que outros ossos não estejam puxando junto.
- **Sintomas:** braço que afina ao dobrar, ou queixo que fica para trás ao erguer a cabeça. A causa é outro osso (clavícula, pescoço) ainda com peso ali.
- **Método:** pintar osso por osso dá mais controle do que pintar tudo de uma vez.
- **Transferir pesos do corpo para roupas e acessórios:**
  1. Parentar ao rig com *With Empty Groups*.
  2. Adicionar o modificador *Data Transfer* **acima** do Armature.
  3. Escolher o corpo como origem e marcar Vertex Data → Vertex Groups.
  4. Clicar em *Generate Data Layers* e aplicar.
  5. Fazer os ajustes finos à mão.

**No Kumo:**
- A regra das cordas explica os defeitos de ombro e de boca que tivemos (peso de `head` sobrando na mandíbula).
- Nossos scripts já normalizam para 4 ossos com soma 1.
- Já usamos transferência de pesos por vizinhança para as camadas do olho, a boca e o contorno.

## 3. Parentesco
- **Conectado:** o filho só gira (mão no braço).
- **Com offset** (*keep offset*): o filho segue o pai, mas pode se mover por conta própria (dedos na mão; tweaks nos controladores).
- **Cuidado:** um controlador de IK não pode ser filho de nenhum osso da própria corrente, senão dá dependência circular.

## 4. Tweak bones, FK e IK
- **Tweaks:** em cada junta, um Copy Transforms na base do deformador e um Stretch To na ponta. Os tweaks permitem ajuste fino. Os 4 ossos por braço servem para torcer o pulso sem quebrar o antebraço.
- **IK:** selecionar o controlador e depois o antebraço, e apertar Shift+I. Serve para contato: mão apoiada, pé no chão.
- **Foot roll:** pivôs no calcanhar, na ponta e no meio do pé.
- **Dedos:** IK nos dedos com um osso mecânico e um constraint *Armature*, para ligar ou desligar "os dedos seguem a mão".
- **Espelhar:** nomear tudo com `.L` e usar *Symmetrize*, que copia ossos e constraints para o outro lado.

**No Kumo:**
- O Estúdio tem "puxar mão ou pé" (IK na página).
- O rig do Blender não tem IK nem foot roll. Para andar, correr e pular, **IK nos pés é o que mais falta**: ele mantém o pé parado no chão.
- Os ossos do Kumo já usam `.L` e `.R`.

## 5. Controles que poupam trabalho
- **Mão (Action constraint):** grava-se uma ação da mão abrindo e fechando, e um controlador a dispara pela posição. Um *Transformation* faz os dedos abrirem em leque pela rotação ou pela escala. Tudo é **aditivo**: ainda dá para mexer dedo por dedo por cima.
- **Tronco:** um controlador geral dobra a coluna inteira com suavidade, e os controles individuais continuam valendo. O pivô da cintura é isolado com tweaks, para o quadril girar sem levar o corpo todo.
- **"Cabeça de galinha" (isolar rotação):**
  - a cabeça (ou os braços, ou os olhos) mantém a orientação enquanto o tronco se mexe;
  - faz-se separando a herança em Copy Location e Copy Rotation;
  - um slider define o quanto da rotação do pai é herdado.
- **Custom shapes:** formas próprias para os controladores, com prefixo `WGT-` e cores por função (IK vermelho, FK azul, tronco amarelo).
- **Painel próprio em Python:** uma aba com os sliders e botões do personagem (intensidades, esconder a cabeça para ver a boca, etc.).

**No Kumo:**
- A "cabeça de galinha" serve direto para a **cabeça grande**: o tronco pode balançar na caminhada com a cabeça estável.
- O controle de mão já existe no Estúdio (sliders Fechar e Abrir).
- Faltam custom shapes e um painel no Blender.

## 6. Rig de rosto
- **Malha de deformadores em bendy bones**, com um tweak em cada encontro. As expressões saem desses pontos.
- **Olhos:**
  - o deformador fica **exatamente no centro** da esfera do olho;
  - cada olho tem um osso-alvo com *Damped Track*;
  - os dois alvos são filhos, com offset, de um controlador geral: movem-se juntos, mas ainda um por um.
- **Brilho do olho:** tem rig próprio com Damped Track, para manter controle artístico da posição e do tamanho, sempre por cima do olho.
- **Pálpebra acompanha o olhar:** de leve, com um slider de intensidade. O Damped Track aponta para um osso **mecânico**, filho do controlador, e não para o controlador, para não mudar a pose inicial.
- **Shape key + driver:** a pupila dilata por uma shape key, controlada pela escala do osso-alvo.
- **Pálpebras por Action constraint:** ossos `ACT-` rodam a ação de fechar e abrir conforme o controlador sobe e desce; os tweaks continuam livres por cima.
- **Mandíbula:**
  - o pivô fica perto da base das orelhas;
  - os tweaks da parte de baixo do rosto são filhos dela;
  - ao abrir, os pontos da bochecha se aproximam do centro, para **preservar o volume** da pele.
- **Cantos da boca:**
  - um controlador por canto, com os pontos presos a um osso-guia por Copy Transforms em posições ao longo dele;
  - um constraint *Armature* com 50% e 50% mantém o canto centralizado entre o lábio de cima e o de baixo.
- **Zíper da boca:**
  - uma segunda corrente mantém a boca fechada;
  - um driver, pela escala dos cantos, troca cada ponto entre aberta e fechada **em sequência**, com um atraso por ponto;
  - assim a mandíbula mexe sem abrir a boca, e a boca abre do canto para o meio.
- **Língua:** corrente de deformadores com **Spline IK** sobre uma curva Bézier; cada ponto da curva é preso a um osso por *Hook*. Dobra e estica.
- **Sobrancelha:** tweaks, um controlador geral e guias para a parte de cima, a de baixo e o conjunto. Um modificador *Corrective Smooth* suaviza a pele.

**No Kumo:**
- **Já temos:** `eye_target` com Damped Track (v5); olhar e piscar por shape keys com drivers; mandíbula com dobradiça nos cantos; língua com corrente de ossos.
- **Vale trazer:**
  1. **Pálpebra acompanhando o olhar**, de leve.
  2. **Cantos da boca com controlador**, para sorriso e tristeza: hoje a boca só abre e fecha.
  3. **Preservar volume ao abrir a boca.**
  4. **Zíper da boca.**
- **Curvar a língua:** nossa língua desliza em linha reta. Para curvar, a ideia do Spline IK serve, mas tem de ser assada em ossos para o jogo.

## 7. Criar um personagem a partir de um modelo gerado por IA
Processo do autor, igual ao ponto de partida do Kumo (Rodin):
1. Gerar a imagem em pose T e levá-la a um gerador de imagem para 3D. O resultado é **só uma base**: tem o volume geral, sem informação no rosto.
2. **Modelo base:**
   - tirar cabelo, roupas e acessórios;
   - definir joelhos, cotovelos e costas;
   - refinar o rosto: pálpebras com **espessura**; boca marcada pelos cantos e pelo encontro dos lábios; a região **em volta** da boca também modelada, porque ela define a leitura da boca.
3. **Retopologia:** o modelo gerado tinha 542 mil faces, impossível de animar e de abrir UV. Refazer com *Poly Build*, organizando em **loops**: anéis de faces em volta dos olhos e da boca, seguindo o fluxo da deformação. Um modelo base retopologizado serve para os próximos personagens.
4. **Pistas visuais:**
   - antes de ajustar o modelo à referência, colocar olhos, sobrancelhas, cílios, tons de pele e os acessórios, mesmo provisórios;
   - a comparação só funciona com o conjunto à vista: não se julga a semelhança numa pele cinza.

**No Kumo:**
- O Kumo já passou pela retopologia (7,5 mil pontos).
- **A boca foi cortada sem loops em volta**, só dividindo faces. Para as expressões dos cantos, a boca vai precisar de anéis de faces em volta dos lábios.
- A regra das pistas visuais confirma nosso método de comparar sempre com a referência, com tudo à vista.
