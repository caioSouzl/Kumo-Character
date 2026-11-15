# Boca anatômica e língua retrátil do Kumo 3D

Pedido do Caio: boca como parte da anatomia, **sem dentes**; interior vermelho escuro; espaço para uma língua retrátil de camaleão.

## Boca
- **Onde foi cortada:** na borda entre o focinho (verde escuro) e a mandíbula (verde claro), que já existe na textura oficial. O modelo não tem boca pintada; essa borda é a boca natural.
  - Medição: `src/mapa_rosto.py` desenrola a pele da cabeça num mapa e acha a borda.
  - Eixo: a curva segue o eixo do rosto, porque no modelo oficial a cabeça está girada ~16° (ver `fotos/mapa-do-rosto.png` e `linha_da_boca.json`).
  - Forma: a curva é simétrica, alta no centro (logo abaixo das narinas) e descendo até os cantos, atrás e abaixo dos olhos (±62°).
- **O corte não move nenhum ponto existente** (`src/boca.py`):
  - as faces que a linha atravessa viram primeiro os mesmos triângulos com que o Blender já as desenha;
  - depois as arestas são divididas exatamente na linha.
- **Mandíbula:** osso `jaw`, filho de `head`, com a dobradiça entre os cantos da boca. Girar negativo em X abre (−32° é bem aberta). O contorno de jogo (`Kumo_Contorno`) também segue a mandíbula.
- **Interior:** `Kumo_Boca`, uma bolsa presa nos dois lábios. O teto segue a cabeça, o chão segue a mandíbula, e o fundo fica mais escuro. As cores são vermelho escuro (`Kumo_Boca_Interior`) e quase preto (`Kumo_Boca_Fundo`). Com a boca fechada, a bolsa fica toda por dentro da pele.
- **Moldura dos olhos:** a moldura de pele dos olhos (uma cópia da pele em volta de cada olho) descia até a boca e ficava parada por cima da abertura. As partes dela abaixo da linha da boca foram removidas.

## Língua (`src/lingua.py`)
Segue a mecânica do camaleão (de Groot & van Leeuwen 2004; Anderson & Deban 2010):
- **Guardada:** no chão da boca, com folga de 13 mm por dentro da pele.
- **Mira:** sai um pouco antes do disparo (o hioide empurra).
- **Disparo:** num estalo elástico, alcança até ~1,5–2× o corpo em ~0,07 s.
- **Formato esticada:** afina enquanto estica e tem uma bola na ponta (a almofada que gruda).
- **Volta:** é mais lenta.

Rig, só com ossos, que exporta para o Godot:
- `jaw` → `lingua_mira` → `lingua_00`…`lingua_10` e `lingua_ponta`, além de `lingua_controle`.
- **Alcance:** a posição Y local de `lingua_controle` é o quanto a língua sai, em metros. Os segmentos deslizam (`lingua_i.y = alcance·i/10`, `ponta.y = alcance`) e os do meio afinam.
- **Mira automática:** `lingua_mira` desfaz metade do giro da mandíbula, então a língua sai pelo **meio da abertura**, e não pelo queixo.

## Animações para o jogo (24 qps)
- **`Boca_Abrir`:** abre em 6 quadros, segura e fecha.
- **`Lingua_Lancar`:** em sequência:
  1. abre e mira (quadros 1–6);
  2. dispara 2,4 m em 2 quadros (7–9);
  3. gruda (9–11);
  4. volta em 12 quadros;
  5. fecha a boca.

  Vídeo: `lingua_lancar.mp4`, e a versão lenta em `lingua_lancar_lento.mp4`.
- **Mirar num alvo no Godot:** gire `lingua_mira` para o alvo e ponha o alcance (a distância) nos ossos, com as mesmas contas acima.

## Conferências
- **Kumo parado:** o render antes e depois é igual, a não ser por uma diferença mínima onde a cópia da pele da moldura foi tirada e a pele verdadeira aparece. Veja `fotos/repouso-diferenca.png`: a terceira imagem mostra a diferença ampliada 3×.
- **Exportação:** GLB e FBX reimportados batem com o Blender em **0,0 mm** em todos os quadros de `Lingua_Lancar`, para a pele, o interior da boca e a língua (`medicoes_boca.json`).
- **Arquivos oficiais:** os 27 continuam intactos.

## Arquivos
- `kumo_v6_boca.blend`: o Kumo atual, com olhos, mãos, ombros, boca e língua.
- `kumo_v6_jogo.glb` e `kumo_v6_jogo.fbx`: exportação completa para o jogo.
- `src/`: `mapa_rosto.py`, `boca.py`, `lingua.py`, `exportar_boca.py`.

## Ainda não feito
- O Estúdio do celular ainda não tem os controles de boca e língua.
- Expressões da boca (sorriso, cantos) ainda não existem: hoje a boca só abre e fecha.
- Nos cantos da boca aberta aparece um fio fino onde teto e chão se encontram.
