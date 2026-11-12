# Olhos do Kumo para jogo (aparência da v5, exportável)

**Pedido do Caio (2026-11-12):** criar os olhos do Kumo 3D sem nenhuma mudança visual.

**Resultado:** os olhos que piscam e olham (sistema `olhos-v5`, variante B) agora exportam para GLB e FBX, com a mesma aparência.

## Como foi feito (`src/olhos_jogo.py`)

A v5 desenha o olho com camadas finas sobre a pele: Geometry Nodes prendem as camadas, a textura vem projetada, a piscada é um recorte no material e o olhar desliza a textura. Nada disso exporta. A conversão troca cada peça por algo que exporta:

| Peça | Na v5 | Na versão de jogo |
|---|---|---|
| Fundo do olho | camada com textura projetada | a mesma malha com UV fixa; textura = olho × máscara (exato) |
| Íris, pupila e brilho | textura que desliza no olhar | malha fina só onde há textura; o olhar vira 4 shape keys (direita, esquerda, cima, baixo) |
| Recorte do olho no olhar | máscara no material | "moldura": cópia exata da pele em volta do olho, por cima das camadas. Em repouso coincide com a pele; no olhar, esconde o que sai do olho |
| Pálpebras | recorte por tabela + relevo da borda | malha em grade, com a forma de cada estágio (25, 50, 75 e 100 %) tirada da própria v5; a linha escura da borda é uma tira própria |
| Presas à pele | Geometry Nodes | pesos copiados da pele (até 4 ossos, soma 1) |

## Controles (exportam)

- **Osso `controle_olhos`:** posição X = piscar o olho esquerdo, Y = piscar o direito (0 aberto, 1 fechado).
- **Osso `controle_olhar`:** X = olhar para a direita (+1) ou a esquerda (−1); Y = para cima (+1) ou para baixo (−1). O alcance é de 11°, o mesmo da v5.
- **No motor de jogo**, os mesmos movimentos ficam nos pesos dos morphs `Piscar_25/50/75/100` (um estágio de cada vez) e `Olhar_*`.

## Medições

| Teste | Resultado |
|---|---|
| Kumo inteiro em repouso contra o Kumo atual (render de frente) | diferença média de 0,29 em 255; 546 pixels acima de 24, só na borda dos olhos |
| v5 contra a conversão (`comparacao-v5-x-jogo.png`), diferença média em 255 | repouso 0,4 · piscar 25 % 0,5 · 50 % 1,1 · 75 % 1,2 · 100 % 0,7 · um olho 0,6 · olhar 0,8 a 2,0 |
| GLB e FBX reimportados (18 objetos dos olhos, 7 quadros de teste: aberto, meia piscada, piscada, um olho, olhar direita, cima, diagonal) | diferença de **0,0 mm** |
| Arquivos | `kumo_v6_jogo.glb` (18 MB, com texturas) e `.fbx` (6 MB) |

## Diferenças que sobram (pequenas, à vista em zoom)

- No olhar extremo (11°), aparecem pontinhos na borda da pupila e a íris fica um pouco diferente bem na borda do olho.
- Na piscada parcial, a transparência das pontas da pálpebra é aproximada.

## Arquivos

- `kumo_v6_olhos_jogo.blend`: Kumo com mãos e dedos + olhos de jogo + controles.
- `kumo_v6_jogo.glb` e `.fbx`: o mesmo, exportado.
- `kumo-v6-olhos-jogo.png`: olhos em 8 estados + corpo inteiro.
- `comparacao-v5-x-jogo.png` e `comparacao/`: v5 contra a conversão, estado por estado.
- `texturas/`, `medicoes_conversao.json` e `medicoes_integracao.json`.
- `src/olhos_jogo.py` (conversão + comparação), `src/integrar.py` (junta ao Kumo com mãos + exporta + reimporta) e `src/fotos_final.py`.

> **Atualização (12/11):** os GLB/FBX desta pasta exportam as camadas dos olhos sem transparência. Use os arquivos de `../ombros/`, que já trazem a correção (veja o RELATORIO de lá).
