# Braços originais com a técnica nova e exportação para jogos

**Pedido de 2026-11-11:** manter o modelo antigo dos dois braços e conseguir exportar para jogos.

**Situação:** para a sua avaliação.

## O que foi feito

- **A malha não mudou:** mesma geometria, vértices, UV, textura e contorno dos dois braços. As imagens em repouso são idênticas às do modelo atual.
- **Trabalho feito numa cópia:** `kumo_bracos_originais.blend`. O `kumo_rigged.blend` oficial não foi alterado (os hashes conferem).
- **O que mudou:** só a distribuição dos pesos entre braço, antebraço e mão, nos dois lados, com a técnica testada no P1.
  - O peso de cada vértice é definido pela posição ao longo do braço.
  - A transição em cada articulação tem largura proporcional à espessura local, com a mesma regra validada no P1.
  - A parte do peso que pertence ao ombro e ao peito foi preservada.
- **Regra dos motores de jogo, aplicada ao corpo inteiro:** no máximo 4 ossos por vértice, e pesos somando 1. Os grupos do contorno não foram tocados.

| Pesos | Original | Cópia |
|---|---|---|
| Máximo de ossos por vértice | 10 | **4** |
| Vértices com mais de 4 ossos | 544 | **0** |
| Vértices com soma diferente de 1 | 5.523 | **0** |

As razões janela/raio foram testadas nesta malha: cotovelo com 1,5×, 2,0× e 2,5× (estes dois chegam ao mesmo limite de segmento) e punho com 2,0× e 2,5×. Escolhi 2,0× nos dois.

Valores medidos nesta malha:

| Lado | Raio do cotovelo | Raio do punho | Janela do cotovelo | Janela do punho |
|---|---|---|---|---|
| Esquerdo | 0,086 | 0,060 | 0,147 | 0,119 |
| Direito | 0,085 | 0,059 | 0,148 | 0,117 |

Esses números valem para esta malha.

## Movimento (mesmo método da auditoria)

Repouso: 0 cruzamentos no original e na cópia, dos dois lados.

### Braço esquerdo

| Pose | Original | Pesos novos |
|---|---|---|
| cotovelo 45 | 0 reais · 0.0 mm · comp. 0.506 | 0 reais · 0.0 mm · comp. 0.701 |
| cotovelo 90 | 5 reais · 2.98 mm · comp. 0.217 | 0 reais · 0.0 mm · comp. 0.327 |
| cotovelo 100 | 29 reais · 6.53 mm · comp. 0.187 | 0 reais · 0.0 mm · comp. 0.242 |
| cotovelo 115 | 46 reais · 8.63 mm · comp. 0.161 | 32 reais · 4.21 mm · comp. 0.148 |
| antebraco torcao 60 | 0 reais · 0.0 mm · comp. 0.518 | 0 reais · 0.0 mm · comp. 0.753 |
| punho 45 | 0 reais · 0.0 mm · comp. 0.617 | 0 reais · 0.0 mm · comp. 0.685 |
| punho menos45 | 0 reais · 0.0 mm · comp. 0.491 | 0 reais · 0.0 mm · comp. 0.682 |
| punho lateral 30 | 0 reais · 0.0 mm · comp. 0.65 | 0 reais · 0.0 mm · comp. 0.842 |
| punho lateral menos30 | 0 reais · 0.0 mm · comp. 0.824 | 0 reais · 0.0 mm · comp. 0.832 |
| cotovelo 90 punho 45 | 5 reais · 2.98 mm · comp. 0.217 | 0 reais · 0.0 mm · comp. 0.326 |
| braco horizontal | 0 reais · 0.0 mm · comp. 0.57 | 0 reais · 0.0 mm · comp. 0.57 |
| braco para frente 90 | 0 reais · 0.0 mm · comp. 0.704 | 0 reais · 0.0 mm · comp. 0.704 |
| braco para tras 40 | 0 reais · 0.0 mm · comp. 0.827 | 0 reais · 0.0 mm · comp. 0.827 |
| braco torcao 45 | 0 reais · 0.0 mm · comp. 0.544 | 0 reais · 0.0 mm · comp. 0.544 |

Desvio da mão em relação ao osso da mão: punho 45° 22.5 mm → 9.2 mm; lateral 30° 10.5 mm → 4.6 mm.

### Braço direito

| Pose | Original | Pesos novos |
|---|---|---|
| cotovelo 45 | 0 reais · 0.0 mm · comp. 0.49 | 2 reais · 1.32 mm · comp. 0.723 |
| cotovelo 90 | 19 reais · 4.79 mm · comp. 0.149 | 3 reais · 1.79 mm · comp. 0.374 |
| cotovelo 100 | 25 reais · 6.51 mm · comp. 0.205 | 3 reais · 1.43 mm · comp. 0.296 |
| cotovelo 115 | 49 reais · 12.45 mm · comp. 0.236 | 0 reais · 0.04 mm · comp. 0.181 |
| antebraco torcao 60 | 0 reais · 0.0 mm · comp. 0.499 | 0 reais · 0.0 mm · comp. 0.703 |
| punho 45 | 0 reais · 0.0 mm · comp. 0.645 | 0 reais · 0.0 mm · comp. 0.692 |
| punho menos45 | 0 reais · 0.0 mm · comp. 0.542 | 0 reais · 0.0 mm · comp. 0.606 |
| punho lateral 30 | 0 reais · 0.0 mm · comp. 0.885 | 4 reais · 1.44 mm · comp. 0.843 |
| punho lateral menos30 | 0 reais · 0.0 mm · comp. 0.719 | 0 reais · 0.0 mm · comp. 0.839 |
| cotovelo 90 punho 45 | 19 reais · 4.79 mm · comp. 0.149 | 5 reais · 1.94 mm · comp. 0.374 |
| braco horizontal | 0 reais · 0.0 mm · comp. 0.676 | 0 reais · 0.0 mm · comp. 0.692 |
| braco para frente 90 | 6 reais · 15.07 mm · comp. 0.431 | 6 reais · 10.7 mm · comp. 0.446 |
| braco para tras 40 | 1 reais · 1.95 mm · comp. 0.836 | 0 reais · 0.0 mm · comp. 0.836 |
| braco torcao 45 | 0 reais · 0.0 mm · comp. 0.815 | 0 reais · 0.0 mm · comp. 0.815 |

Desvio da mão em relação ao osso da mão: punho 45° 22.2 mm → 10.7 mm; lateral 30° 8.8 mm → 4.2 mm.

**Leitura:**
- **Cotovelo:**
  - No **esquerdo**, as dobras de 90° e 100° (a faixa necessária) passaram a ter **zero** cruzamentos.
  - No **direito**, caíram de 19 e 25 para **3** (até 1,8 mm).
  - A 115° (faixa desejável), o esquerdo vai de 46 para 32 e o direito de 49 para 0.
- **Punho:** no original, a mão quase não acompanhava o osso, porque só 5 vértices tinham a mão como osso principal. Agora ela acompanha 2 a 2,5 vezes melhor.
  - Com a mão de fato dobrando, o punho em bloco do lado direito encosta no antebraço na dobra lateral: **4 pares reais, 1,4 mm**. Antes não havia contato porque a mão não se mexia.
  - No direito, o cotovelo a 45° também passou a ter 2 pares (1,3 mm), onde antes tinha 0.
  - Esses resíduos vêm da forma original, que é assimétrica e irregular, e não da regra de pesos: mudar as razões não os removeu.
- **Desempenho:** 0,22 → 0,24 ms por atualização (sem diferença prática).

## Exportação para jogos

| Teste | Resultado |
|---|---|
| **glTF/GLB** (`kumo_bracos_originais.glb`, 3,6 MB) | Exporta. Reimportado: 30 ossos, até 4 influências, soma 1 em todos os vértices, ações preservadas. |
| **Deformação do GLB contra o Blender** (animação de teste com cotovelos, punhos, torção e braço erguido) | **Diferença máxima de 0,001 mm** nos 3 quadros, ou seja, o arquivo exportado se move igual ao Blender. |
| **FBX** (`kumo_bracos_originais.fbx`, 0,9 MB) | Exporta. Reimportado: 30 ossos, até 4 influências, soma 1, ações preservadas. A comparação quadro a quadro foi feita só no GLB. |

**O que ainda não vai para o jogo, e por quê:**
- **Contorno marrom:** no Blender, ele é um modificador e não é exportado. Em motores de jogo, o contorno se faz no material (shader de contorno) ou com uma cópia da malha com normais invertidas. Isso é uma decisão para a etapa de exportação, e posso preparar as duas opções.
- **Sistema de olhos v5:** está em outro arquivo e usa Geometry Nodes, que não exporta (auditoria, A4). Os olhos para jogo dependem do P2.
- **Dedos:** a mão original não tem dedos articuláveis, porque a malha não tem dedos. Mantida como você pediu.

## Arquivos

- `src/repeso_bracos.py`: gera tudo (`BO_RE` e `BO_RW` são as razões; `BO_FAST=1` só mede).
- `kumo_bracos_originais.blend`: cópia com os pesos novos.
- `kumo_bracos_originais.glb` e `.fbx`: exportações testadas.
- `medicoes.json`: todas as medidas.
- `renders/` e `bracos-originais-comparacao.png`: comparação visual.
