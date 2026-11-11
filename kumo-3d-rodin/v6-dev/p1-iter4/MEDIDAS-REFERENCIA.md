# P1 iteração 4: medidas tiradas da referência

**Fonte:** `referencia de modelo/kumo-referencia-01.png`, vista **FRENTE**, braço esquerdo do Kumo (lado direito da imagem), medido em grade ampliada de pixels. As medidas estão no topo de `src/p1_iter4.py`.

## Do modelo atual, só duas coisas

1. **A articulação do ombro** (`upper_arm.L`, em 0,25 / −0,04 / 0,74), para o encaixe.
2. **O tronco**, que serve de régua para converter pixels em metros:
   - **Espessuras:** largura do tronco = 0,40 m no modelo e 52 px na referência, ou seja, 0,00769 m/px.
   - **Comprimentos:** ombro até a virilha = 0,46 m no modelo e 83 px na referência, ou seja, 0,00554 m/px.

Usei duas réguas porque o tronco do modelo tem proporção diferente do tronco desenhado. Medir cada dimensão contra a dimensão equivalente do tronco preserva a relação local entre braço e corpo. A proporção de 3,5 cabeças serviu de conferência: as pontas dos dedos chegam à altura da virilha, como no desenho.

## Medidas

| Medida | Referência (px) | Metros | Braço atual |
|---|---|---|---|
| Úmero (ombro → cotovelo) | 29 | 0,161 | 0,226 |
| Antebraço (cotovelo → punho) | 28 | 0,155 | 0,184 |
| Espessura do braço | 16 | 0,123 | cerca de 0,13 a 0,16 |
| Espessura do antebraço | 14 | 0,108 | — |
| Espessura do punho | 12 | 0,092 | — |
| Mão: comprimento total | 32 | 0,177 | punho redondo |
| Mão: largura vista de frente | 28 | 0,215 | — |
| Palma: comprimento | 18 | 0,100 | — |
| Dedo: comprimento | 13 | 0,072 | sem dedos |
| Dedo: espessura | 7 | 0,054 | sem dedos |
| Inclinação do braço (vista de frente) | 24° para fora | — | — |
