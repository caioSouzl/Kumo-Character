# Kumo · olhos-v3: ajustes visuais e relevo da borda

**Data:** 2026-11-10 · **Estado:** **para avaliação do Caio.** Não está aprovado. A `olhos-v2` e o modelo principal não foram tocados (hashes conferem).

## O que foi mantido (aprovado na v2)

- O vínculo dos olhos à pele deformada, sem alterar pesos, malha ou folgas.
- Malha da cabeça idêntica (mesmo hash de vértices e faces, mesmos modificadores); deformação da cabeça zero.

## O que mudou

| Item | v2 | v3 |
|---|---|---|
| Tom da pálpebra | Verde puro amostrado de um anel estreito, muito suavizado | Verde e verde-amarelado de um anel mais largo, menos suavizado. O brilho médio é igualado à pele visível em volta: luminância E 0,476 (antes 0,480; pele 0,476) e D 0,430 (antes 0,431; pele 0,430). |
| Canto interno do olho esquerdo | Laranja da textura da cabeça aparecia com o olho fechado (a casca não chegava ao canto) | A casca passou a incluir as faces do canto (5 no olho E, 1 no D) |
| Borda da pálpebra | Sem volume | **Relevo de 8 mm** (pálpebra superior) e 4,4 mm (inferior), só para fora e ao longo da normal, apenas junto à borda. Ver as pranchas `11` e `12`. |
| Base das camadas | Quadriláteros copiados da pele | **Os mesmos triângulos que o Blender usa para renderizar a pele**, para as camadas ficarem paralelas à pele mesmo subdivididas |
| `Kumo_Olhos_PeleGloboRef` | Cópia oculta sem uso | **Removida**. Confirmado antes que nada a referenciava: o modificador que a usava foi retirado na v2. |

### Como o relevo funciona (Geometry Nodes `Kumo_Relevo_<pálpebra>`)

- Vem depois do vínculo à pele, então acompanha o rig.
- Lê a mesma tabela da borda que o material e é movido pelos mesmos ossos `lid_up`/`lid_low`, então segue o arco da piscada.
- Em cada ponto, a altura nunca passa da **folga disponível até a pele**, medida em 9 direções com 3 mm de margem. Perto da borda da órbita o relevo diminui sozinho, em vez de encostar nela.
- A altura se ajusta num único valor (nó `Altura`) por pálpebra.

## Penetração

Agora a medição testa também os pontos **dentro** de cada triângulo, não só os vértices. Com isso apareceu algo que a v2 tinha mas não conseguia medir: em vincos da órbita, a face entre dois vértices afundava até cerca de 1 mm. Na v3 isso foi corrigido erguendo só os triângulos afetados. Onde não havia espaço, embaixo da borda da órbita do olho esquerdo, as camadas dividem o espaço disponível proporcionalmente, mantendo a ordem.

| Caso | Passos | Profundidade máxima | Onde |
|---|---|---|---|
| Piscada simultânea, E, D | 41 cada | 0,46 mm | Canto da órbita do olho E (fixo) |
| Semicerrar; olhar para os 4 lados | 22 cada | 0,46 mm | Idem |
| Cabeça virada ±18° e ±25°, piscando | 22–41 | 0,46 mm | Idem |
| Olhar lateral com a cabeça virada ±25° | 22 cada | 0,46 mm | Idem |
| Cabeça inclinada 25°; erguida + virada + inclinada | 22 cada | 0,46 mm | Idem |

**Resíduo conhecido:**
- São de 3 a 7 pontos das pálpebras do olho esquerdo, com no máximo 0,46 mm (0,1% da largura do olho), sempre os mesmos.
- Não crescem com a piscada, com o relevo nem com a rotação.
- Ficam onde a pele faz uma pequena saliência entre dois vértices, logo abaixo da borda da órbita, e não há espaço para afastar sem encostar na borda.
- Não são visíveis nas renders.
- Para zerar: subdividir a casca só nesse canto ou usar uma folga menor ali. Posso fazer qualquer dos dois se você quiser.

Fora da área visível do olho ficam de 11 a 16 pontos ocultos dentro da cabeça. São a parte recolhida da casca, invisível.

## Identidade e silhueta

| Vista | Diferença média na região dos olhos (aberto) | Deslocamento do olho |
|---|---|---|
| Frente | 4,6 / 255 (v2: 4,5) | 0,4 px |
| 3/4 | 1,8 (v2: 1,7) | 0,45 px |
| Perfil, olho direito | 4,5 (v2: 4,4) | 0,9 px |
| Perfil, olho esquerdo | 3,0 (v2: 2,9) | 0,2 px |

Silhueta do corpo: IoU de 0,99979 / 0,99985 / 1,0 / 0,99987 (frente, 3/4, perfil e costas). Distância entre os olhos: 326,0 px → 326,5 px.

## Pranchas (`renders/`)

| Arquivo | Conteúdo |
|---|---|
| `09-v2-x-v3-{frente,34,perfil_E,perfil_D}.png` | **v2 × v3**: aberto, semicerrado 40%, 50% e fechado |
| `11-relevo-alturas.png` | Relevo de 0, 4, 8 e 12 mm na vista tangente ao globo |
| `12-relevo-final.png` | Sem relevo × relevo final (8 mm) |
| `01` a `08`, `10` | Mesmas pranchas da v2: aberto × original, fechamento, foco 50%, piscada individual, olhar, cabeça virada 18°/25°/−25°, olhar durante a rotação, fidelidade com rotação, GIF |

## O que ainda vejo (para sua avaliação)

1. **Tom:** melhorou pouco. Com o olho fechado, na 3/4 e no perfil, ainda se percebe uma área oval suave no lugar do olho. O brilho médio já é igual ao da pele em volta, então o que resta é a falta da variação de textura. A próxima opção seria pintar a pálpebra com a própria textura da pele das bordas, espelhada para dentro, em vez de um preenchimento suave.
2. **Canto interno do olho esquerdo:** o ponto laranja diminuiu, mas **não sumiu**: resta um fio claro com o olho fechado, na vista de frente, junto à marca escura do lado do nariz. É a textura original da cabeça numa área que a pálpebra ainda não cobre.
3. **Relevo:** em 8 mm, aparece no perfil como um pequeno lábio na linha do cílio e não se nota nas vistas normais. Na vista tangente, a linha do cílio fica levemente serrilhada sobre o relevo.
4. **Resíduo de 0,46 mm** no canto da órbita esquerda (ver acima).
