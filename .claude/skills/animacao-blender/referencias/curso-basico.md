# Curso básico de Blender (playlist do Caio, 26/11)

**Fonte:** playlist de 15 aulas em português que o Caio mandou (youtube.com/playlist?list=PL-YgB1cUwWX0faPlCEbu8NjyYpWjtgl4w). O projeto do curso é uma rosquinha (donut) com cobertura e confeitos.

- **Estudadas pela legenda automática:** aulas 1, 2, 3, 7, 8, 9, 11, 13 e 14.
- **Não estudadas:** 4 (segredos), 5 (escultura), 6 (básico/Disney), 10 (Geometry Nodes 2 e materiais aleatórios), 12 (iluminação) e 15 (vídeo). O YouTube bloqueou o download das legendas.

O curso usa um Blender 4.x. Os atalhos valem no 5.2; nomes de menus e nós podem ter mudado.

Cada parte traz **"No Kumo"** quando a lição muda algo no projeto.

## 1. Interface e navegação (aula 1)

- **Mover, girar e escalar:** `G`, `R`, `S`. Depois `X`, `Y` ou `Z` trava no eixo, ou arraste com o botão do meio. Valores digitados são em metros.
- **Vista:**
  - botão do meio orbita, `Shift` + botão do meio arrasta, a roda aproxima;
  - `.` do teclado numérico centraliza o selecionado;
  - `0` é a câmera, `1`/`3`/`7` são frente, lado e topo, `5` alterna perspectiva e ortográfica.
- **Painéis:** `T` ferramentas, `N` propriedades (aba Item), Outliner com coleções.
- **Render:** `F12`.

## 2. Modelagem (aula 2)

- **Referências antes de tudo:** junte fotos do objeto real. A "perfeição digital" é reproduzir as imperfeições.
- **Comece pela forma mais parecida** (`Shift+A`). O menu de criação some no primeiro clique fora dele.
- **Poucos polígonos e faces quadradas:** malha densa é difícil de editar; quadrados deformam melhor em formas orgânicas.
- **Tamanho real e escala aplicada:**
  - deixe o objeto do tamanho real (a rosquinha tem ~10 cm);
  - depois `Ctrl+A` → Scale, para a escala voltar a 1;
  - escala não aplicada é só uma conta em cima do objeto. Modificadores, Geometry Nodes e distribuição de pontos erram com ela. **Quando algo dá errado, a primeira pergunta é se a escala foi aplicada.**
- **Suavizar:**
  - Shade Smooth suaviza o sombreado sem mudar a malha, mas o contorno continua facetado;
  - o modificador Subdivision Surface (nível 2) arredonda a malha de verdade.
- **Edit Mode (`Tab`):** vértices, arestas e faces.
- **Edição proporcional (`O`):** move os vizinhos junto; a roda do mouse muda o raio.
- **Shrink/Fatten (`Alt+S`):** move ao longo das normais, não na direção da câmera. Para ver as normais: Overlays → Normals.
- **Variação rápida:** Select → Select Random, `Alt+S` em todos e depois Vertex → Smooth Vertices para amaciar.

No Kumo:
- conferido em 26/11: todos os objetos de `kumo_v8_movimento.blend` estão com escala 1;
- o contorno de jogo é uma casca 2 cm para fora, pela normal: é o mesmo princípio do `Alt+S`.

## 3. Modificadores (aula 3)

- **Atalhos de seleção:**
  - `Ctrl+L` seleciona tudo que está ligado ao ponto;
  - `Ctrl+I` inverte;
  - `Alt+Z` (raio X) ou o modo Wireframe deixam selecionar o lado de trás.
- **Duplicar, separar e renomear:**
  - `Shift+D` duplica; botão direito ou `Esc` devolve a cópia ao lugar;
  - `P` → Selection separa em outro objeto;
  - `F2` renomeia.
- **Solidify** dá espessura. Offset −1 cresce para dentro e +1 para fora. Com `Shift` arrastando, o valor muda devagar.
- **A ordem dos modificadores muda o resultado:** Solidify antes do Subdivision arredonda a borda; Subdivision antes deixa a borda cortada.

## 4. Materiais e nós (aula 7)

- **Pense na história do objeto:**
  - a rosquinha é frita até a metade e virada, por isso tem borda dourada e meio claro;
  - material que contradiz a história (um "carro de madeira") parece errado, mesmo que sutil.
- **Os três campos do Principled BSDF:** quase todo material usa só Base Color, Roughness e Normal.
- **Use o Shader Editor**, não só a aba de material.
- **Ruído procedural** (Noise Texture):
  - ponha um Texture Coordinate → **Object** no Vector, para a textura não esticar como acontece na UV;
  - depois um ColorRamp, que faz as manchas com as cores escolhidas.
- **Relevo:**
  - o mesmo ruído entra num nó Bump (Height) e o Bump vai ao Normal;
  - ajuste a **Distance** do Bump, não a Strength;
  - a Distance é em metros, então precisa caber no tamanho do objeto (2 mm na rosquinha).
- **Ligações e atalhos de nó:**
  - mesma cor de soquete liga com a mesma cor; cinza e amarelo se misturam;
  - `Ctrl` + botão direito arrastando corta ligações;
  - `H` esconde e `Alt+H` revela. No Blender, `Alt` desfaz o atalho de mesma letra.

## 5. Pintura de textura (aula 8)

- **Rosa no modelo** quer dizer textura faltando.
- **Crie a imagem** no Shader Editor (Image Texture → New).
  - Use resolução do tamanho do objeto: 512 para um objeto de 15 cm. 4K ou 8K pesa à toa.
  - Os campos aceitam contas: `/2` divide o valor.
- **Pincel e balde:**
  - `F` muda o tamanho do pincel, `Shift+F` a força;
  - `X` troca a cor principal pela secundária;
  - o balde de tinta tem cor própria: copie com `Ctrl+C` e cole com `Ctrl+V` sobre a cor.
- **Salve a imagem pintada** (Image → Save As, `Alt+S`). Um asterisco indica que ela só existe na memória e se perde ao fechar.
- **Mix (Color):**
  - funciona como as camadas do Photoshop, e o Factor vira a opacidade;
  - Add guarda o claro, Multiply guarda o escuro;
  - Overlay junta a pintura com o procedural.

No Kumo:
- as texturas de olho geradas por script já são salvas em arquivo e embutidas no GLB;
- só uma pintura feita à mão precisaria do Save.

## 6. Geometry Nodes: espalhar objetos (aula 9)

- **Geometry Nodes é um modificador próprio:** muda o objeto sem mexer na malha.
- **A sequência:**
  1. Distribute Points on Faces;
  2. **Join Geometry** com a malha original, senão a malha some;
  3. Instance on Points, com o objeto vindo do Outliner (Object Info);
  4. ligue o Rotation dos pontos no Rotation das instâncias.
- **Aplique a escala da peça instanciada**, senão ela sai achatada. Gire a peça no Edit Mode, não no Object Mode.
- **Rotação aleatória só em Z:**
  - Random Value em modo Vector, com X e Y em 0;
  - Rotate Euler em espaço Local (Object);
  - os valores são em radianos, e os campos aceitam `pi*2`.
- **Sem sobreposição:** modo **Poisson Disk**, com distância mínima e Density Max. A densidade é por metro quadrado, por isso os números ficam enormes em objetos pequenos. Um nó Math (multiplicar) deixa o controle mais confortável.
- **Onde espalhar, a pincel:**
  - Weight Paint (`Ctrl+Tab`) cria um grupo de vértices;
  - o Density Factor vira entrada do modificador;
  - o botão de atributo dessa entrada recebe o nome do grupo.
- **Entradas expostas:** renomeie e ordene as entradas do grupo, para o modificador virar uma ferramenta reutilizável.

No Kumo:
- Geometry Nodes não vai para o jogo; seria preciso aplicar o modificador antes;
- serve para renders e para gerar malha que depois é aplicada.

## 7. Animação (aula 11)

- **Telas:** além do 3D, trabalhe com Timeline, Dope Sheet e **Graph Editor**.
- **Chaves:**
  - `I` insere uma chave;
  - campo **amarelo** tem chave neste quadro, **verde** tem chave em outro quadro, **laranja** foi mudado sem chave (o valor se perde ao trocar de quadro).
- **Graph Editor:**
  - as alças das curvas aceitam `G`, `R` e `S`, e é nelas que se controla aceleração e desaceleração;
  - apague os canais que não animam;
  - `Ctrl` + botão do meio arrastando estica a vista.
- **Loop perfeito:** o primeiro e o último quadro com o mesmo valor **e a mesma inclinação**. Alças na mesma diagonal nas duas pontas apagam a emenda.
- **Quadros por segundo:**
  - 24 é cinema, 30 TV, 60 jogos;
  - View → Show Seconds mostra a linha do tempo em segundos.
- **Parentesco:**
  - `Ctrl+P` → Object (Keep Transform); o último selecionado é o pai;
  - anime só o pai.
- **Composição:** a câmera tem Composition Guides, como a regra dos terços. `Ctrl+Alt+0` põe a câmera na vista atual.

No Kumo (medido em 26/11 em `kumo_v8_movimento.blend`):
- **Valores:** `Caminhar` e `Correr` fecham o loop com o mesmo valor em todas as 274 curvas.
- **Inclinação (corrigido em 26/11):** a medida por diferença de quadros enganava; o certo é comparar a inclinação das alças nas pontas.
  - Cada curva de `Caminhar` e `Correr` agora tem modificador Cycles, e as alças automáticas contam a volta.
  - Inclinação da emenda: 0,0 nas duas ações. Pés sem deslize (0,0 mm) e arquivos reexportados.

## 8. Compositor em tempo real (aula 13)

- **Ligar:** workspace Compositing → Use Nodes.
  - Na viewport, o Compositor pode ficar Disabled, Camera ou Always (menu de sombreamento).
  - O resultado é o mesmo do render final.
- **Montagem prática:** viewport 3D em cima, Image Editor com o Render Result embaixo. Um render de `F12` interrompido com `Esc` já serve de prévia.
- **Fundo novo:**
  - Film → Transparent;
  - um nó RGB e **Alpha Over** com o render por cima. O Alpha Over é o Mix feito para canal alfa.
- **Luz de fundo:**
  - Ellipse Mask, Blur com **Relative** ligado (o borrado acompanha a resolução) e Mix em Add;
  - ligado antes do Alpha Over, só afeta o fundo.
- **Brilho (glow):**
  - um ColorRamp isola os pontos mais claros;
  - um Blur pequeno (2 a 5%);
  - um Mix em Add com o Factor como intensidade;
  - Glare → Fog Glow faz parecido e mantém as cores.
- **Cor (Color Balance):**
  - Lift mexe nas sombras, Gamma nos meios-tons, Gain nas luzes;
  - confira na waveform (aba Scopes do Image Editor, `N`), tentando centralizar a faixa dos meios-tons.
- **Lente:**
  - Lens Distortion bem pouco (distorção ~0,003, dispersão ~0,005 a 0,01), com Fit para não perder os cantos;
  - Filter → Box Sharpen bem pouco (~0,008).
- **Organizar os nós:**
  - `Shift+P` (Node Wrangler) põe os nós numa moldura com nome e cor;
  - `M` desliga um nó para comparar;
  - `Ctrl+Shift+clique` mostra um nó no Viewer;
  - `Shift` + botão direito arrastando cria um reroute.

## 9. Render (aula 14)

- **Resolução** pelo lugar onde a imagem será vista: 1080×1350 para rede social no celular, 4K só para tela grande.
- **Amostras (samples):**
  - mais amostras dão menos ruído e mais tempo;
  - o limite por tempo deixa o tempo total previsível.
- **Em animação**, ligue a semente animada (Advanced → Seed com o relógio). O ruído parado no mesmo lugar parece sujeira na tela.
- **Light Paths:**
  - os rebatimentos da luz; com 0, as sombras ficam pretas;
  - Fast GI resolve na maioria das cenas.
- **Denoise:** só funciona bem com amostras suficientes (o curso usa ~500 no Cycles).
- **Persistent Data:** guarda dados entre quadros e acelera animações.
- **GPU** em Preferências → System: CUDA (GTX), OptiX (RTX), HIP (AMD), oneAPI (Intel).
- **Motion Blur:** dá sensação de movimento e custa tempo.
- **Profundidade de campo:** foco num Empty (Focus Object) e F-stop baixo.
- **EEVEE:**
  - resolução das sombras;
  - AO só com alguma luz no World (no Blender do curso);
  - Bloom;
  - Screen Space Reflections.

No Kumo:
- a pele, os olhos e a boca são de emissão;
- glow e bloom devem ficar leves para não desbotar as cores aprovadas;
- as folhas de conferência ficam sem efeitos de lente.

## Para conferir no Blender 5.2 antes de usar em script

- Os nomes dos nós do Compositor e do menu Mix mudaram entre versões.
- Confira o nome do nó com `bpy.types` antes de escrever o script.
