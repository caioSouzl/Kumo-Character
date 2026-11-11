# Braços originais + mãos com 3 dedos e polegar

**Pedido de 2026-11-11:** manter os dois braços antigos, criar dedos sem mudar o estilo do Kumo e continuar exportável para jogos. A imagem de esqueleto que você mandou foi usada como apoio: metacarpo, 3 dedos com polegar e controles.

**Situação:** para a sua avaliação. O modelo oficial não foi alterado (os hashes conferem); todo o trabalho está numa cópia.

## O que foi feito

1. **Braço e antebraço:** os originais, com a mesma malha, textura, contorno e cor.
2. **Mão:**
   - Só a ponta (o punho em bloco, a partir do plano do punho) foi trocada por uma mão em "luva", costurada à borda original.
   - A mão nova tem 3 dedos curtos e grossos, polegar na lateral e palma arredondada.
   - As duas mãos ficaram do mesmo tamanho: a média dos dois punhos originais, que eram diferentes entre si (esquerdo 0,16 × 0,21; direito 0,23 × 0,20).
3. **Cor:** a mão nova usa a mesma textura e o mesmo material, mas num ponto de cor única, o verde típico do punho original (RGB cerca de 0,25 / 0,63 / 0,28). A primeira tentativa, que copiava a textura do punho, gerou listras com cores dos olhos e foi descartada. **Diferença visível:** a mão não tem as manchas amarelas do braço.
4. **Rig da cópia:**
   - O punho foi movido para onde a mão começa.
   - Ossos novos dos dois lados: metacarpo, dedo1 a dedo3 (2 segmentos cada) e polegar (2 segmentos). Total: 48 ossos.
5. **Pesos:**
   - Braço: mesma técnica de `bracos-originais`.
   - Mão: técnica do P1 iteração 7; cada vértice pertence à peça que o criou, e o metacarpo é estrutural.
   - No máximo 4 ossos por vértice, soma 1.
6. **Malha:** 7.548 vértices (o original tem 7.398). A costura entre a borda irregular do braço antigo e a mão nova tem **74 triângulos**; o resto continua em quads. No glTF, tudo vira triângulo de qualquer forma.

## Ajustes encontrados por teste (varredura)

| Ajuste | Resultado |
|---|---|
| Polegar mais baixo na palma, saindo mais para o lado | Repouso: de 8 cruzamentos para **0** |
| Dedos menos curvados em repouso e palma menos espessa | Menos contato dos dedos com a palma ao fechar |
| **Polegar ao lado na mão fechada** (ele não dobra por cima dos dedos) | Ao fechar de 30° a 60°: de 25–40 cruzamentos para **0**. Testei pivô mais fundo e transições diferentes: o polegar dobrando sobre os dedos sempre atravessa os dedos e a palma, porque a mão é grossa. |

## Testes (mesmo método)

Pares reais (0,5 mm ou mais) e profundidade máxima.

| Pose | Esquerda | Direita |
|---|---|---|
| Repouso | **0** | **0** |
| Dedos a 45° | 0 | 0 |
| Fechar de 30° a 60° | **0** em todos | **0** em todos |
| Mão fechada a 70° | 6 · 3,4 mm | 7 · 4,1 mm |
| Mão aberta | 2 · 1,9 mm | 6 · 1,9 mm |
| Polegar isolado | 1 · 2,6 mm | 8 · 2,1 mm |
| Dedos alternados | 2 · 2,8 mm | 2 · 2,9 mm |
| Palma curvada a 20° | 1 · 2,9 mm | 1 · 2,8 mm |
| Punho +45° | 0 | 0 |
| Punho −45° | 2 · 1,5 mm | 0 |
| Punho lateral ±30° | 0 | 0 |
| Cotovelo 90° e 100° | 0 | 0 |
| Cotovelo 90° + punho 45° + mão fechada | 209 · 16 mm | 100 · 16 mm |

**Pesos:** até 4 ossos, soma 1, nenhum vértice sem peso.
**Desempenho:** 0,55 ms por atualização, contra 0,22 ms dos braços originais sem dedos (mais ossos e vértices).

**O que ainda não está bom:**
- **Mão fechada a 70°:** com a mão grossa do estilo antigo, os nós dos dedos e o dedo 3 encostam na palma no fechamento total, com 3 a 4 mm.
- **Polegar sobre os dedos:** ainda não é possível sem cruzamentos.
- **Pose combinada** (cotovelo 90° + punho 45° + mão fechada): é contato de verdade, não defeito dos pesos. O antebraço original é muito curto (o punho em bloco ocupava 60% dele: 0,064 m até o novo punho no esquerdo e 0,083 m no direito), então a mão encosta no braço.
- **Mão aberta e polegar:** pequenos contatos de 1,9 a 2,6 mm.
- **Contorno:** entre os dedos aparecem traços marrons onde a casca do contorno passa pela fenda. Lembram as linhas internas do desenho, mas são da técnica e precisam da sua avaliação.
- **Fechamento completo:** para fechar a mão inteira com o polegar por cima sem cruzamentos, o caminho seria uma forma corretiva (shape key) para a mão fechada. Ela exporta para glTF, mas é um passo seguinte, que depende da sua autorização.

## Exportação para jogos

| Teste | Resultado |
|---|---|
| GLB (`kumo_maos_dedos.glb`, 3,7 MB) | Reimportado: 48 ossos, até 4 influências, soma 1 |
| Deformação do GLB contra o Blender (repouso, mão fechada, mão aberta, cotovelo + punho + mão fechada) | **Diferença máxima de 0,003 mm** |
| FBX (`kumo_maos_dedos.fbx`, 1,1 MB) | Exportado; não reimportado nesta rodada |

Continua valendo o que foi dito em `bracos-originais`: em jogo, o contorno é feito no material, e os olhos da v5 dependem do P2.

## Imagens e arquivos

- `dedos-corpo.png`: referência, modelo atual e braços antigos com dedos (frente e 3/4).
- `dedos-vistas.png`: mão atual contra a mão com dedos, nos dois lados, em quatro vistas.
- `dedos-movimentos.png`: repouso, aberta, fechada, polegar, dedos alternados e punho a 45°, nos dois lados.
- `src/maos_com_dedos.py`: gera tudo. `MD_P='{json}'` muda parâmetros; `MD_FAST=1` só mede; `MD_PREVIEW=1` faz renders rápidos.
- `kumo_maos_dedos.blend`, `.glb`, `.fbx`, `medicoes.json` e `renders/`.
