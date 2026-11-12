# Kumo · animação 2D

## Animação 2 (atual)
**Vídeo:** `kumo-animacao-2.mp4` (1080 × 1350, 24 quadros por segundo, 5 s, em loop). `comparacao-1-x-2.mp4` mostra a animação antiga e a nova lado a lado, e `kumo-animacao-2-quadros.png` mostra 12 quadros.

O roteiro é o mesmo da animação 1: o Kumo olha para um lado, depois para o outro, volta e dá um pulinho. O tempo agora segue a pesquisa (`../estudos-animacao/02-TEMPO.md`):
- **Piscadas:** a normal fecha em 2 quadros, fica 1 fechada e abre em 3. Há uma longa (3, 2, 4) quando ele muda de ideia e uma rápida na queda. Ele pisca em toda virada de cabeça.
- **Olhar:** os olhos se mexem sozinhos, em olhadas de 3 quadros, 2 quadros antes da cabeça. A cabeça passa um pouco do ponto e assenta.
- **Respiração:** inspira mais devagar do que expira, e os braços acompanham com 3 quadros de atraso.
- **Pulo:**
  - prepara em 6 quadros e desce os braços;
  - estica ao sair do chão e abre os braços, com arrasto;
  - fica 14 quadros no ar;
  - achata no máximo 2 quadros depois de tocar o chão e dá um pequeno quique;
  - cabeça e cauda reagem com atraso.
- **Enquadramento:** o Kumo cabe inteiro na tela. A animação 1 cortava a cabeça no alto do pulo.

## Camadas (`camadas/`)
A arte é a vista de frente da folha de modelo (`character-model-sheet/assets/view-front.png`), recortada da referência, **sem redesenho**. Ela foi separada em peças:
- `corpo` (com a cauda);
- `braco_E` e `braco_D`;
- `cabeca`;
- `iris_E` e `iris_D` (pupila, brilho e anel laranja, que se movem dentro do olho).

O que fica escondido atrás de cada peça foi preenchido, para aparecer quando ela se mexe: o tronco atrás dos braços e a parte branca do olho atrás da íris. Montadas paradas, as camadas refazem a arte **pixel a pixel** (diferença zero, conferida pelo próprio script).

Consertos na arte, todos invisíveis sobre o fundo branco da folha:
- **Brilho da pupila direita:** o recorte da folha tinha tirado esse brilho como se fosse fundo, deixando um furo; aqui ele volta a ser branco.
- **Halo branco:** o halo branco das bordas, sobra do fundo branco, foi tirado.
- **Véu de pixels quase invisíveis em volta do recorte:** foi tirado, porque deixava riscos quando uma peça saía do lugar.

As pálpebras são desenhadas com as cores e o traço da folha de expressões aprovada.

## Ferramentas (`src/`)
- `camadas.py <saída>`: gera as camadas a partir da arte e confere a montagem.
- `rig2d.py`: monta uma pose a partir das camadas (giros de cabeça, braços e cauda; olhar; piscar de cada olho; achatar e esticar; altura).
- `planilha.py`: a planilha de tempo. Cria canais com chaves e curvas, desenha a planilha e **confere as regras de tempo**: piscadas, piscar ao virar a cabeça, olhos antes da cabeça, duração das olhadas, preparação, achatamento na queda e loop.
- `animar_v2.py <camadas> <saída>`: faz a animação 2. Com `--so-planilha`, só confere o tempo e desenha a planilha. Ao gerar os quadros, também confere se o Kumo cabe na tela.
- `animar.py`: a animação 1, guardada como histórico.

Para refazer:
1. `python3 src/camadas.py camadas`
2. `python3 src/animar_v2.py camadas <pasta>`
3. `ffmpeg -framerate 24 -i <pasta>/quadros/q%04d.png -c:v libx264 -pix_fmt yuv420p -crf 18 kumo-animacao-2.mp4`

**Pontos fracos conhecidos:**
- Com o braço bem aberto, aparecem pequenos riscos escuros perto dos ombros e das mãos: sobras do contorno original, que era um desenho só.
- Na curva da cauda aparecem pontinhos claros quando ela balança.

São pequenos no tamanho do vídeo, mas existem.

## Animação 1
`kumo-animacao-5s.mp4` e `kumo-animacao-quadros.png`, feita com `src/animar.py`. A cabeça e a cauda se mexem sobre a arte inteira, e a pálpebra é desenhada por cima.
