# Kumo — sistema ocular experimental (olhos-v2)

**Estado:** experimental, **aguardando avaliação do Caio**. A v1 (`../olhos-v1/`) e a versão aprovada (`../kumo_rigged.blend` e o resto) não foram tocadas: os hashes SHA-256 conferem.

Resultados: [`RELATORIO-OLHOS-V2.md`](RELATORIO-OLHOS-V2.md).

## O que mudou em relação à v1

| | v1 | v2 |
|---|---|---|
| Como os objetos do olho seguem a cabeça | Pesos próprios de armadura, mais uma "guarda" de colisão que empurrava para fora | **Vínculo à pele deformada** (Geometry Nodes): cada vértice segue o ponto da pele que está embaixo dele, com a deformação do rig aprovado. Sem pesos próprios e sem guarda. |
| Pálpebra | Folha flutuante em 40 estágios (shape keys) | **Casca que copia pele e globo**. A borda percorre a superfície seguindo o mesmo arco de rotação em torno do centro do globo, pré-calculado numa tabela. |
| Cor da pálpebra | Textura real na faixa da borda, que trazia os pontos alaranjados | **Pele lisa**: verde tirado só do anel de pele lisa em volta |
| Contorno pintado em volta do olho | Aparecia com o olho fechado | **Coberto só pela pálpebra fechada**: a área coberta inclui o contorno detectado. A textura da cabeça não muda e, com o olho aberto, o contorno continua igual. Para reverter, basta usar `olho_X_mask` no lugar de `olho_X_lidmask` no material da pálpebra. |

A malha da cabeça, os pesos do rig, os materiais e as texturas aprovados **não foram alterados** (mesmo hash de vértices e faces, mesmos modificadores).

## Objetos (coleção `Kumo_Olhos_v1`, nome herdado)

`X` = `L` (olho esquerdo do Kumo) ou `R` (direito).

| Objeto | Função |
|---|---|
| `Kumo_EyeWindow_X` | Vazio do contorno do olho (coordenadas das camadas fixas), preso ao osso `head` |
| `Kumo_EyeGaze_X` | Vazio preso ao osso `eye.X`: gira a projeção de íris, pupila e brilho |
| `Kumo_Eye_X` | Globo/esclera, 1 mm acima da pele |
| `Kumo_Iris_X`, `Kumo_Pupil_X`, `Kumo_Catchlight_X` | Camadas a +0,4, +0,8 e +1,2 mm. O brilho fica preso ao globo e gira com o olhar. |
| `Kumo_LidLow_X`, `Kumo_LidUp_X` | Pálpebras a +1,8 e +2,4 mm do globo. A borda é a fronteira lida da tabela `Kumo_Lid*_X_borda`, embutida no `.blend`. |
| `Kumo_Olhos_PeleRef` | Cópia oculta do corpo com os pesos aprovados e o atributo `rest_position`: é a referência do vínculo |
| `Kumo_Olhos_PeleGloboRef` | Cópia oculta que sobrou de um teste. **Não é mais usada**; pode ser apagada. |

Todos os objetos oculares têm o modificador `VinculoPele` (grupo de nós `Kumo_VinculoPele`).

## Ossos e controles (iguais à v1)

`eye.L/R`, `eye_target` (com `.L/.R`), `lid_up.L/R`, `lid_low.L/R`. No osso `head` ficam as propriedades `piscar`, `piscar_E`, `piscar_D`, `fechar_parcial_E/D` e `acompanhar_olhar`. A rotação dos ossos `lid_*` alimenta o estágio `t` da borda por um driver no material.

## Refazer

```
python src/kumo_eyes.py ../kumo_rigged.blend .
python src/validate_eyes.py orig ../kumo_rigged.blend .
python src/validate_eyes.py exp kumo_eyes_exp.blend .
python src/compose_sheets.py .
```
