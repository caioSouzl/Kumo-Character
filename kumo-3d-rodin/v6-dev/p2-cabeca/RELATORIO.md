# P2: cabeça, olhos e boca · iteração 1 (estudo técnico)

**Autorização:** Caio, 2026-11-11 ("Autorizo todas as reclamações").

**Situação:** a mecânica funciona, mas o visual está **reprovado** por mim mesmo (motivos abaixo). Isto não está pronto para aprovação, e serve para você decidir a direção antes da iteração 2. O modelo oficial e as versões anteriores não foram alterados.

## O que foi feito

1. **Base:** a cabeça facetada F1.2 da linha arquivada `kumo-3d-toon` (aprovada em 2026-11-09), regenerada sem mudança pelo script original no Blender 5.2. Ela já tem:
   - órbitas abertas;
   - pálpebras na própria malha;
   - boca com lábios e cavidade;
   - mandíbula, narinas e crista;
   - 809 vértices, 97% quads.
2. **Posição:** levada ao quadro da cabeça do Kumo (queixo, topo e centro medidos no modelo oficial; escala 1,018).
   - O ajuste automático dos vértices de controle à cabeça do Rodin (`fit_cabeca_kumo.py`) foi **descartado**: ele encolhia a cabeça de 1,03 para 0,72 de largura, porque a cabeça do Rodin é arredondada e a F1.2 é um poliedro.
3. **Olho esférico:**
   - O olho da F1.2 era um elipsoide (0,18 × 0,10 × 0,22) e, ao girar, saía da órbita.
   - Agora é uma esfera de raio 0,235, com a frente no mesmo lugar do olho antigo.
   - O aro, a pupila e o brilho ficam colados na esfera (0,6 / 1,2 / 1,8 mm acima dela).
   - O olho gira pelo centro da esfera (ossos `Eye.L` e `Eye.R`).
   - O forro escondido da órbita foi afastado para fora da esfera (10 de 26 vértices).
4. **Piscada por ossos** (`Palpebra_sup` e `Palpebra_inf`, nos dois lados):
   - As pálpebras giram em arco pelo centro do olho.
   - Os pesos saíram da piscada antiga da F1.2.
   - O ângulo foi ajustado para as bordas se tocarem sem se sobrepor.
   - Seis shape keys corretivas ligadas aos ossos: fechada e meio fechada de cada olho, e dupla.
5. **Exportação:** a cabeça e os dois olhos com o rig (8 ossos), em GLB e FBX.

## Testes (mesmo método: pares de triângulos novos que se cruzam)

| Pose | Olho × cabeça | Cabeça × ela mesma |
|---|---|---|
| Olhar ±25° para os lados, 15° para cima e para baixo | **0** (antes: 129–201 pares) | **0** |
| Mandíbula 10° e 20° | 0 | **0** |
| Cabeça girada 30° e inclinada 20° | 0 | 0 reais |
| Piscada a 50% (os dois olhos) | **0** (antes: 330–345) | **0** |
| Piscada a 25% / 75% / 100% | 0 / 6 / 8 pares (só no olho esquerdo) | 18 / 13 / 23 reais, até 31 mm |
| Só o olho direito fechando (100% e 50%) | 0 | **0** |
| Só o olho esquerdo fechando (100% / 75% / 25%) | 0 | 5 / 4 / 12 reais |
| Pose combinada (cabeça, boca, olhar e piscada) | 0 | 8 reais |

**Outros números:**
- Pesos: até 2 ossos por vértice na cabeça e 1 nos olhos; soma 1.
- Desempenho: 0,29 ms por atualização.
- GLB e FBX reimportados: diferença menor que 0,001 mm em todos os 6 quadros de teste (neutro, piscada 50% e 100%, olho esquerdo, olhar, boca). A animação de fato move as malhas (até 326 mm), então a comparação vale.
- A cabeça F1.2 já tem 124 pares cruzados no repouso: o fundo da boca e o forro, escondidos. Eles foram descontados, como em todos os testes.

**A piscada ainda não fecha sem cruzamentos:**
- O olho direito sozinho fica limpo.
- O esquerdo e a piscada dupla não convergem. A pele da sobrancelha, levada pelas pálpebras, cruza a pele parada.
- A F1.2 original já tinha 27 a 145 pares na piscada.

## Por que reprovei o visual (`p2-corpo.png`, `p2-cabeca.png`, `p2-expressoes.png`)

1. **Forma da cabeça:** a F1.2 foi feita para o Kumo da linha toon.
   - De perfil, ela vira um "limão" pontudo para trás.
   - De frente, é mais estreita em cima e mais larga embaixo do que a referência e do que o Kumo atual.
2. **Olhos marrons:** o material da íris é procedural, calculado pela posição do objeto. Ao juntar as peças do olho, as coordenadas mudaram e o âmbar sumiu.
3. **Olhos saltados:** de perfil, a esfera passa da silhueta da cabeça.
4. **Linhas de contorno dentro do rosto:** a casca do contorno aparece em volta dos olhos e da boca.
5. **Cores:** são da linha toon (manchas recortadas), não as da textura do Kumo.

**O que funcionou e vale levar adiante:**
- olho esférico com íris e pupila coladas;
- olhar pelo centro;
- piscada em arco por ossos, com as bordas se tocando;
- correções ligadas aos ossos;
- boca abrindo pela mandíbula;
- exportação conferida.

## Decisão que preciso de você para a iteração 2

1. **Base da cabeça:**
   - **(a)** Manter a forma da cabeça do Kumo atual (Rodin) e abrir nela as órbitas, as pálpebras e a boca, com a mecânica acima. É o plano original do P2 e preserva a silhueta que você já conhece. **Recomendo esta.**
   - **(b)** Seguir com a F1.2 e corrigir a forma para a referência.
2. **Olho:** pode ficar um pouco saliente, como num camaleão, ou deve ficar dentro da silhueta da cabeça, como na referência de frente?

## Arquivos (`iter1/`)

- `kumo_p2_cabeca.blend`, `.glb` e `.fbx`
- `p2-medicoes.json`, `fit_cabeca_kumo.json`
- `p2-corpo.png`, `p2-cabeca.png`, `p2-expressoes.png` e `renders/`
- `src/`:
  - `p2_montagem.py`, que faz tudo, nesta ordem: olho esférico, ossos e pesos das pálpebras, posição, correções, testes, renders e exportação;
  - `fit_cabeca_kumo.py`;
  - cópias de `kumo_v2_head.py` e `kumo_common.py` da linha arquivada, que não foi alterada.

Para refazer:
```bash
python src/kumo_v2_head.py -- --out <tmp>
python src/fit_cabeca_kumo.py ../../kumo_rigged.blend <tmp>/fit.json
python src/p2_montagem.py <tmp>/kumo_v2_head.blend <tmp>/fit.json ../maos-corretivas/kumo_v6_maos_jogo.blend <saída>
```
