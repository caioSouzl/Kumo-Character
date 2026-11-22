# Modelagem por frente e lado, e olhos estilizados

Fontes, estudadas em 22/11 quadro a quadro (a cada 2 s, com closes nos trechos-chave) e pela transcrição do áudio:
- **A.** Vídeo enviado pelo Caio, @dreamstudio32 (TikTok, 94 s, "A New Character coming to Life"): uma bruxinha modelada do zero a partir de duas imagens. Só música; as teclas aparecem na tela.
- **B.** @pol.gc, "Anima tus ojos 2D con decals y rigging" (TikTok, 172 s, https://vt.tiktok.com/ZSsRNS75J/): olho 2D projetado por decal e preso a ossos. Só música; o processo está na tela.
- **C.** @mokunachoi, "3D eye tutorial" (TikTok, 59 s, https://vt.tiktok.com/ZSsRN6muT/): íris que afunda para dentro do olho. Narrado em inglês.

## 1. Modelar com duas imagens cruzadas (A)

**A ideia:** não é preciso a volta inteira do personagem. Uma imagem de **frente** dá a largura e a altura; uma de **lado** dá a profundidade e a altura. As duas juntas definem o volume, e uma vista 3/4 serve só para conferir.

### Montagem
1. Duas imagens da mesma pose, na mesma escala e com os pés na mesma linha. Se a cabeça e os pés não batem nas duas, todas as medidas brigam depois.
2. Cada uma vira um **Empty de imagem**. A da frente fica de pé encarando a vista de frente (Numpad 1). A do lado é a mesma coisa girada 90° em Z (`R Z 90`), encarando a vista lateral (Numpad 3).
3. Os dois planos ficam **cruzados** (perpendiculares), afastados para trás do modelo: o da frente atrás em Y, o do lado atrás em X. Assim o modelo sempre fica na frente da imagem.
4. O autor deixa as duas imagens também numa janela pequena no canto da tela, para consultar o original sem os planos atrapalharem.
5. Script: `scripts/referencias_cruzadas.py`.
   - `montar(frente, lado, altura)` cria os dois planos. Cada imagem aparece só na vista que a encara e some na perspectiva.
   - `conferir()` mede quanto os pés e o topo das duas imagens diferem. No teste, imagens certas deram 0 m de diferença, e uma imagem com os pés 5% mais altos deu 0,1 m.

### Modelagem (box modeling, uma peça por vez)
- **Sempre em ortográfica e com raio X** (`Alt+Z`), para ver a imagem através da malha.
- O vaivém é **sempre o mesmo**:
  - na frente, mover vértices em X e Z até casar com o contorno;
  - no lado, mover os mesmos vértices em Y e Z;
  - as teclas que aparecem o tempo todo são `G X`, `G Y` e `G Z`, sempre com o eixo travado.
- **Corpo:** começa num cubo.
  - `Ctrl+R` cria os loops onde a forma muda: cintura, quadril, peito, ombro;
  - `E` puxa as pernas para baixo e os braços para os lados;
  - `S` acerta a largura de cada anel.
  - O corpo vem primeiro, com poucos loops; o detalhe só entra quando a silhueta das duas vistas já bate.
- **Cabeça:** uma esfera com poucos gomos, ajustada na frente e no lado.
  - O nariz é um bico puxado com `E`.
  - Os olhos são esferas posicionadas na vista lateral, onde a profundidade do olho dentro da cabeça fica clara.
- **Peças separadas:** chapéu, botas, meias, mãos e cabelo são objetos próprios.
  - O chapéu vem de um cilindro, com loops e a ponta dobrada.
  - A bota sai de um cubo moldado na vista lateral.
  - A meia é a perna duplicada (`Shift+D`) e engordada.
  - As mãos e os dedos são puxados de um bloco; as unhas são peças à parte.
- **No fim:** Subdivision Surface para suavizar, e mechas de cabelo como faixas.
- Pela contagem de teclas na tela, a maior parte do tempo vai para ajustar vértice por vértice nas duas vistas, e não para criar forma nova.

### Quando usar
- **Personagem novo a partir de desenho**, no lugar de gerar no Rodin e retopologizar.
  - A malha já nasce leve e em loops, pronta para rig.
  - O Rodin dá volume rápido, mas pede retopologia (7,5 mil pontos no Kumo).
  - Para personagens secundários do jogo, frente e lado costumam bastar.
- **Para conferir um modelo pronto:** com as imagens cruzadas atrás, a diferença entre o modelo e o desenho aparece nas duas vistas. É a comparação com a referência que o projeto já usa, agora em ortográfica e sem distorção.

## 2. Olho 2D por decal, com rig (B)

Os olhos não são globos. A pupila é uma **imagem projetada na pele** a partir de um Empty, como um adesivo. Mover o Empty move a pupila.

### Passo a passo do vídeo
1. **Material do olho:**
   - no Edit Mode, selecionar as faces do olho (`L` pega a ilha);
   - criar um slot de material ("Ojo.L") e clicar em **Assign**;
   - fazer o mesmo no outro olho com "Ojo.R".
2. **Empty no centro:**
   - `Shift+S` → *Cursor to Selected* leva o cursor ao centro das faces;
   - `Shift+A` → Empty → Plain Axes;
   - `F2` para renomear ("Decal_Ojo.L");
   - ligar **In Front**, para o Empty não sumir dentro da cabeça.
3. **Nós do material:** Texture Coordinate → Mapping → Image Texture → Mix → Principled BSDF.
   - Texture Coordinate: saída **Object**, com o Empty escolhido no campo Object.
   - Mapping: tipo **Point**, Location 0,5 nos três eixos (o centro do Empty vira o centro da imagem) e Rotation 90° em X (deixa a imagem de pé na frente).
   - Image Texture: a imagem da pupila, em PNG com fundo transparente.
   - Mix (Color): **A** = cor da esclera (branco), **B** = Color da imagem, **Factor** = Alpha da imagem.
   - A pupila só aparece onde a imagem é opaca; no resto fica a esclera.
4. **Ossos:**
   - uma armadura com um osso por olho (OJO.L, OJO.R), apontando para a frente;
   - um osso-alvo à frente do rosto (FOCUS, com um círculo como forma);
   - os ossos dos olhos com **Damped Track** no alvo.
5. **Prender:** cada Empty vai preso ao seu osso (`Ctrl+P` → **Bone**). Mover o FOCUS faz os dois olhos acompanharem.

### O que o teste mostrou (`scripts/olhos.py`)
- **O pivô do osso tem de ficar para dentro da cabeça.**
  - Com o osso girando no próprio olho, o Empty, que está nesse ponto, só gira no lugar, e a pupila quase não anda.
  - Com a base do osso a uns 0,3 de profundidade e a ponta no olho, o Empty desliza pela pele.
  - O script faz isso com o parâmetro `profundidade`.
- **Teste:** esfera, render em Cycles e alvo movido 0,9 m para o lado.
  - O Empty andou 0,107 m pela superfície.
  - O pixel no lugar novo ficou escuro (0,047) e o do lugar antigo voltou à esclera (0,425).
- No script a rotação do Mapping é −90° em X, porque o Empty não é girado. O vídeo usa +90° com o Empty em outra orientação. O que importa é a imagem ficar de pé na vista de frente.
- **Extension = Clip** na Image Texture: fora da imagem não aparece borda esticada.
- Funções:
  - `decal(obj, nome, imagem, centro, tamanho)` cria o Empty e o material;
  - `faces_no_raio(obj, centro, raio)` e `atribuir_faces(obj, nome, faces)` dizem quais faces são o olho;
  - `rig_olhar(rig, [(osso, empty, centro)], foco, profundidade)` cria os ossos e o alvo.

### Limites
- **No jogo:** um decal depende do nó Object do Blender, que não sai no glTF nem no FBX.
  - No Godot, isso se refaz com um shader que recebe a posição do olho como parâmetro.
  - Outra saída é assar o movimento em ossos da malha do olho.
- O decal **não tem volume**: de lado, a pupila desliza na pele. Para um olho que parece fundo, veja a parte 3.

## 3. Íris que afunda para dentro (C)

**O efeito:** de frente e de lado, a íris parece estar **dentro** do olho, com paralaxe, em vez de pintada na superfície.

### Passo a passo do vídeo
1. O olho é uma **esfera achatada**.
2. As ilhas de UV da frente e de trás do globo ficam **empilhadas**, usando a mesma textura. Assim o fundo do globo mostra a mesma íris que a frente mostraria.
3. **Para mais efeito 3D:** a pupila e os brilhos são modelados à parte, como peças pequenas na frente da íris.
4. No Edit Mode, selecionar a íris e **`Alt+N` → Flip** para inverter as normais.
5. **Conferir:** no overlay **Face Orientation**, a parte invertida fica **vermelha**.
6. **Se não funcionar:** no material, em Settings, ligar **Backface Culling → Camera**.
   - Com isso a frente da íris, agora de costas para a câmera, é descartada, e o que aparece é o lado de dentro do fundo do globo.
   - É esse fundo, mais afastado, que dá a sensação de profundidade.

### No script (`olhos.iris_para_dentro(globo, grupo)`)
- Inverte as faces do grupo de vértices e liga o Backface Culling.
- **No teste:** esfera achatada, com a frente da íris num grupo. 52 faces foram invertidas; as 24 que sobraram para fora são a borda, que só tem parte dos vértices no grupo.
- **Onde vale:** o Backface Culling vale no **EEVEE e no viewport**; o **Cycles** não tem essa opção.
- **No Godot:** o material padrão já descarta as faces de trás (Cull Mode: Back), então a íris invertida funciona sem ajuste. Basta não exportar como "double sided".

## No Kumo
- **Aparência travada (D8):** nada disto muda os olhos do Kumo sem pedido explícito do Caio. Os olhos atuais (camadas, `olhos-v5` e `olhos-jogo`) continuam.
- **Duas imagens cruzadas:**
  - A folha `referencia de modelo/kumo-referencia-02.png` já tem **FRENTE e PERFIL** lado a lado, na mesma régua de 0 a 3,5 cabeças.
  - Recortadas na mesma altura, essas duas vistas servem direto para `montar()`, para **conferir** o modelo do Kumo nas duas vistas, sem gerar imagem nova.
  - Vale também para **modelar personagens novos** do jogo. Gerar a vista de lado de um personagem novo com IA gasta créditos e precisa de aprovação do Caio.
- **Decal e íris para dentro:** são técnicas para **personagens novos**, ou para uma versão de teste do Kumo **só se o Caio pedir**.
  - O decal é o que mais se parece com o "olho de desenho" de um personagem 2D.
  - A íris para dentro dá profundidade a olhos grandes vistos de lado.
- **O que já confirma o nosso rig:**
  - olhos com Damped Track num alvo à frente, que é o mesmo do `eye_target` da v5 e do rig de @tiago_prlco (`rig-e-personagem.md`, parte 6);
  - o pivô do olho tem de ficar no centro da esfera do olho, e o teste do decal mostrou o mesmo: pivô na superfície não move nada.
