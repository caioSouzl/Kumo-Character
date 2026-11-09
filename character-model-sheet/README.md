# Kumo — Character Model Sheet

Folha de referência técnica oficial do **Kumo**, camaleão antropomórfico bípede.

**Toda a arte do personagem vem das imagens de referência aprovadas** em
[`../referencia de modelo/`](../referencia%20de%20modelo/). As vistas, o rosto e os detalhes
anatômicos foram recortados das próprias renderizações, sem redesenho. Assim o Kumo é idêntico à referência.

![Kumo — Character Model Sheet](kumo-model-sheet.png)

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `kumo-model-sheet.png` | Folha completa, 4800 × 3800 px (render 2×) |
| `kumo-model-sheet.svg` | Folha completa (usa as imagens de `assets/`) |
| `assets/view-{front,three-quarter,side,back}.png` | As quatro vistas, recortadas da referência 01, com fundo transparente, mesma escala e mesma linha de chão |
| `assets/face-front.png` | Rosto de frente (referência 02), base das expressões |
| `assets/detail-*.png`, `assets/sketch-*.png` | Olho, mão, braço, perna, pé, focinho, espiral da cauda e etapas de construção, todos da referência 02 |
| `expressions/kumo-<expressão>.svg/.png` | As 8 expressões isoladas |
| `src/prep.py` | Recorta e prepara a arte a partir das referências |
| `src/build.mjs` | Monta a folha e as expressões |
| `src/render.cjs` | Converte SVG → PNG (Playwright/Chromium) |

## Seções da folha

1. **Turnaround**: frente (0°), 3/4 (45°), perfil (90°) e costas (180°), na mesma escala e sobre a mesma linha de chão.
2. **Proporções**: medidas tiradas da vista frontal da referência.
3. **Expressões faciais**: neutro/observador, curioso, surpreso, feliz, confuso, desconfiado, empolgado e pensativo. São feitas sobre o rosto original, mudando só pupilas, pálpebras, cristas das sobrancelhas e boca. A cabeça facetada nunca muda.
4. **Construção anatômica**: as seis etapas de construção da referência (cabeça poligonal com 12 a 16 faces → refinamento final), olho, mão (3 dedos + polegar), pé (3 dedos para a frente), espiral da cauda e crista → linha dorsal.
5. **Identidade visual**: paleta oficial, estilo e restrições.

## Proporções (medidas na arte, 1 H = altura da cabeça)

| Medida | Valor |
|---|---|
| Altura total | 1,96 H |
| Cabeça (ponta da crista → queixo) | 1,00 H |
| Largura da cabeça | 1,09 H |
| Tronco (sem pescoço visível) | 0,59 H |
| Pernas com pés | 0,37 H |
| Largura do olho / largura da cabeça | 29 % |
| Pupila / íris | 45 % |
| Diâmetro da espiral da cauda | 0,44 H |

> A referência anota "3,5 cabeças", mas na própria arte a cabeça ocupa cerca de 51 % da altura (1,96 H no total). A folha registra o que o desenho mostra.

## Paleta

| Cor | Hex | Uso |
|---|---|---|
| Verde escuro | `#1B5E3B` | Topo da cabeça, crista e linha dorsal |
| Verde médio | `#4CAF6B` | Corpo, tronco e membros |
| Verde-amarelado | `#C9D45B` | Manchas orgânicas de camuflagem |
| Bege claro | `#EAD9B7` | Barriga / região ventral |
| Âmbar dourado | `#F4B642` | Íris (pupila preta) |
| Marrom escuro | `#5B3A2E` | Contornos e linhas de detalhe |

## Restrições

Sem roupas, sapatos, mochilas, acessórios ou objetos. Não alterar o número de dedos (3 + polegar) nem de artelhos (3). Cores e proporções idênticas em todas as vistas. Sem versões alternativas do Kumo.

## Regenerar

```bash
cd character-model-sheet
python3 src/prep.py                       # recorta a arte → assets/   (requer Pillow)
node src/build.mjs                        # kumo-model-sheet.svg + expressions/*.svg
node src/render.cjs kumo-model-sheet.svg kumo-model-sheet.png 2
for f in expressions/*.svg; do node src/render.cjs "$f" "${f%.svg}.png"; done
```
