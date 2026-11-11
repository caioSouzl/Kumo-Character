# P1 · braço esquerdo e mão: relatório das iterações

**Situação: reprovado na minha própria avaliação.** Nada foi substituído no modelo oficial; os hashes de `auditoria/hashes-antes.sha256` conferem.

- **Arquivos:** `src/p1_braco_mao.py` (gera tudo), `p1_braco_mao.blend` (só o braço novo e o rig dele), `p1-medicoes.json`, `renders/` e `p1-prancha-iter3.png`.
- **Prancha:** à esquerda o braço atual; à direita o P1, em verde liso sem textura.

## Iterações

| Iteração | Método | Resultado |
|---|---|---|
| 1 | Modificador Skin + Subsurf, pesos por calor | Dedos minúsculos, mão em bloco. Cotovelo a 90° piorou (44 contra 6 pares); punho a ±45° piorou (78 e 11 contra 0). |
| 2 | Skin com mais anéis e mão maior | A medição em repouso, acrescentada nesta iteração, revelou **657 pares já em repouso**: o Skin cruzava a palma e os dedos. Os números de pose da iteração 1 não eram confiáveis (eram diferenças sobre uma malha já quebrada). |
| 3 | Modelagem em caixa: anéis octogonais, palma fechada com 3 quads extrudados como dedos, polegar extrudado da face frontal, pesos procedurais suavizados | Malha 100% quads, 1.050 vértices, até 3 influências com soma 1, **0,12 ms** por atualização. Repouso: **36 pares** (o atual tem 0). |

## Medições da iteração 3

Pares novos de triângulos se atravessando, por pose. A coluna "Compressão mín." mostra a menor razão de comprimento de aresta: abaixo de 1, a aresta encurtou.

| Pose | Atual | P1 | Compressão mín. (atual / P1) |
|---|---|---|---|
| Braço na horizontal | 0 | 0 | 0,57 / 1,00 |
| Braço para a frente a 90° | 0 | 0 | 0,70 / 1,00 |
| Cotovelo a 90° | 6 | 72 | 0,22 / 0,21 |
| Cotovelo a 130° | 77 | 115 | 0,19 / 0,19 |
| Punho a 45° | 0 | 77 | 0,62 / 0,50 |
| Punho a −45° | 0 | 17 | 0,49 / 0,36 |
| Mão fechada | sem dedos | 173 | — / 0,19 |
| Mão aberta | sem dedos | 52 | — / 0,52 |

## Por que falhou

1. **A forma veio do braço atual, e o braço atual não serve de guia.**
   - A pele é ondulada pela retopologia automática.
   - A "mão" atual é um punho redondo e grande, maior que o antebraço.
   - Ao medir as seções a partir dessa pele, o braço novo ficou grosso demais (raios de 0,09 a 0,13 no cotovelo, contra cerca de 0,07 no braço atual) e a mão ficou menor que o antebraço.
   - O resultado se afasta da referência, que mostra braço fino e mão com 3 dedos e polegar bem legíveis.
2. **Um tubo grosso sem anéis de apoio colapsa mais nas dobras.** Com deformação linear por ossos (a regra v6 para exportar), a dobra interna do cotovelo se atravessa.
3. **Os dedos estão juntos demais.** Na mão fechada eles se tocam e atravessam a palma.

## O que proponho em seguida (precisa da sua decisão)

- **A.** Construir o braço e a mão a partir de **medidas tiradas da referência**: comprimentos e espessuras na proporção de 3,5 cabeças. Assim, o braço atual deixa de ser a fonte da forma. Depois, ajustar só o ombro para encaixar no tronco atual.
  - Manter da iteração 3: modelagem em caixa, pesos procedurais e testes.
  - Acrescentar o que falta: anel de apoio na dobra interna do cotovelo e do punho, dedos mais separados e fechamento testado.
- **B.** Fazer o mesmo, mas aceitar osso auxiliar de cotovelo e punho (osso extra que segura o volume na dobra). Continua exportável para glTF/FBX.

Nenhuma das duas mexe no modelo oficial.
