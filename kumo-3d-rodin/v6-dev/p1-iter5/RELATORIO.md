# P1 iteração 5: pesos testados articulação por articulação, metacarpo e amplitudes

**Situação: para a sua avaliação.** Não me autoaprovo. O modelo oficial e as tentativas 1 a 4 estão intactos (os hashes da auditoria conferem). Nenhum osso corretivo foi usado.

## O que mudou em relação à tentativa 4

- **Mesma malha da tentativa 4:** mesma geometria, 1.354 vértices, 100% quads. Esta iteração mexe só em pesos e ossos, então a forma, e com ela a identidade visual pendente da mão, **não mudou**.
- **Pesos com razão janela/raio por articulação:** a largura da transição de pesos agora é definida como múltiplo do raio local e testada **em cada articulação separadamente**. Depois testei a combinação (decisão 1 de 2026-11-11). Valores do teste a seguir.
- **Osso estrutural `DEF-metacarpo.L`** (decisão 2):
  - vai do punho, do lado lateral, até a base do dedo 3, do lado oposto ao polegar;
  - o dedo 3 passa a ser filho dele;
  - a metade lateral da palma acompanha esse osso com gradiente suave; a outra metade segue a mão.
- **Não esconde defeitos:** o osso foi testado curvando a palma sozinho e também ligado e desligado com a mão fechada. A mão fechada já era limpa sem ele.
- **Testes novos:** cotovelo a 100° e 115° (faixas da `../AMPLITUDES.md`) e palma curvada a 20°.

## 1. Razão janela/raio, articulação por articulação

Os raios locais medidos são: cotovelo 0,057; punho 0,046; dedo 0,027; polegar 0,026.

Cada linha varia **só aquela articulação** e mantém as outras como na tentativa 4. Resultados em pares reais (travessia de 0,5 mm ou mais) e compressão mínima das arestas.

### Cotovelo

| Razão | 90° | 100° | 115° | 130° |
|---|---|---|---|---|
| 1,0× | 30 reais | 56 | 89 | 110 |
| 1,5× | 19 | 41 | 82 | 111 |
| **2,1×** (o limite é 0,8 do segmento, ou seja, 2,18×) | **0** | **0** | 65 | 89 |
| Braço atual | 5 | 29 | 46 | 75 |

O cotovelo pede cerca de 2×, como no punho.

### Punho

Nenhuma razão produziu cruzamentos. A tabela mostra a compressão mínima.

| Razão | ±45° | Lateral ±30° |
|---|---|---|
| 1,1× (tentativa 4) | 0,27 | 0,46 |
| 1,5× | 0,37 | 0,57 |
| 2,0× | 0,49 | 0,66 |
| **2,5×** | **0,58** | **0,72** |
| Braço atual | 0,62 / 0,49 | 0,65 / 0,82 |

O punho pede mais que 2×: o melhor resultado testado foi 2,5×.

A janela de 2,5× entra na metade do antebraço. Comparei a silhueta de 2,0× e 2,5× (`p1i5-punho-2x-vs-2.5x.png`) e elas são praticamente iguais. A leve ondulação de perfil do antebraço já existe em repouso e vem da forma, não dos pesos.

### Base dos dedos (nó)

| Razão | Mão fechada | Mão aberta |
|---|---|---|
| 0,75× | 0 reais, compressão 0,14 | 0,59 |
| 1,1× (tentativa 4) | 0 reais, 0,13 | 0,70 |
| **1,5×** | 0 reais, **0,30** | 0,70 |
| 2,0× | 0 reais, 0,41 | 0,70 |

Escolhi 1,5× e não 2,0×. Com 2,0×, a janela avança mais de metade da palma para dentro. Nos dedos, o limite real é o **comprimento do segmento** (cerca de 0,035), menor que 2× o raio.

### Junta dos dedos

| Razão | Mão fechada | Fechamento a 65–70° |
|---|---|---|
| 0,5× | **16 reais** (1,2 mm) | 4 a 16 reais |
| 0,82× (tentativa 4) | 0 reais, 3 rasantes | 0 a 2 |
| 1,2× | 0 reais, 2 rasantes | 0 |
| **1,6×** | **0 pares de nenhum tipo** | 0 |

Com 1,6×, a transição cobre quase o dedo inteiro, que passa a curvar em arco em vez de dobrar como dobradiça. Isso é coerente com dedos curtos e grossos de cartoon. É visível na prancha; aprovar ou não o efeito fica com você.

### Polegar

| Razão, testada sozinha | Mão fechada |
|---|---|
| 0,6× | 1 real (2,6 mm) |
| 1,0× (tentativa 4) | 0 reais, 3 rasantes |
| 1,5× | 1 real (0,8 mm) |
| 2,0× | 0 pares |

### Combinação

| Combinação | Mão fechada | Fechamento a 70° |
|---|---|---|
| Cada uma no melhor valor isolado (polegar 2,0×) | **1 real (1,0 mm)** | 1 real |
| **Polegar 1,0× com as demais escolhidas** | **0 pares** | 0 em todos os ângulos de 30° a 70° |

Os melhores valores isolados **não se somam**: o polegar a 2× conflita com a junta dos dedos a 1,6×. A sua cautela se confirmou: não existe um número universal, e o teste combinado é obrigatório.

**Valores adotados:**
- cotovelo 2,1×;
- punho 2,5×;
- base dos dedos 1,5×;
- junta dos dedos 1,6×;
- polegar 1,0×.

**Não testados nesta etapa:** ombro, joelho, tornozelo, pescoço e cauda. Ficam fora do P1: o ombro depende da junção com o tronco, e as pernas, o pescoço e a cauda não têm protótipo. A mesma varredura será feita em cada um quando houver protótipo. Não estendo os valores do braço para eles.

## 2. Resultado final da iteração 5 (mesmo método da auditoria)

**Repouso:** atual 0, novo **0**.

**Como ler cada célula:** pares reais · área atravessada · profundidade · compressão mínima.

| Pose | Atual | P1 iteração 5 |
|---|---|---|
| Braço na horizontal, à frente 90°, para trás 40°, torção 45° | 0 | 0 |
| Cotovelo 45° | 0 · compressão 0,51 | 0 · 0,71 |
| Cotovelo 90° | 5 · 11 cm² · 3,0 mm · 0,22 | **0** · 0,37 |
| **Cotovelo 100°** (limite da faixa necessária) | 29 · 70 cm² · 6,5 mm · 0,19 | **0** · 0,32 |
| Cotovelo 115° (limite da faixa desejável) | 46 · 121 cm² · 8,6 mm · 0,16 | 65 · 48 cm² · 4,0 mm · 0,28 |
| Cotovelo 130° (extremo, não exigido) | 75 · 205 cm² · 14,2 mm | 89 · 75 cm² · 6,4 mm |
| Torção do antebraço 60° | 0 · 0,52 | 0 · 0,87 |
| Punho +45° | 0 · 0,62 | 0 · 0,58 |
| Punho −45° | 0 · 0,49 | 0 · 0,58 |
| Punho lateral +30° | 0 · 0,65 | 0 · 0,72 |
| Punho lateral −30° | 0 · 0,82 | 0 · 0,72 |
| Cotovelo 90° + punho 45° | 5 · 0,22 | 0 · 0,37 |
| Mão fechada (com metacarpo a 20°) | sem dedos | **0 pares** · 0,33 |
| Mão aberta | sem dedos | 0 · 0,69 |
| Palma curvada 20° (só o metacarpo) | sem dedos | 0 · 0,79 |
| Fechamento de 30° a 70° | — | 0 em todos |

- **Pesos:** até 4 influências, todos somando 1.
- **Desempenho:** 0,10 ms por atualização para o braço novo sozinho (o modelo atual inteiro mede 0,19 ms no mesmo teste).

## Critérios

| Critério | Resultado |
|---|---|
| Sem cruzamentos em repouso | ✅ |
| Supera o atual na faixa **necessária** (cotovelo até 100°, punho ±45° e lateral ±30°, torções, mão) | ✅ Zero cruzamentos em tudo. A compressão é melhor ou igual em quase tudo; ficam duas exceções: punho +45° (0,58 contra 0,62) e lateral −30° (0,72 contra 0,82). |
| Faixa **desejável** (cotovelo 115°) | ⚠️ Há contato antebraço–bíceps. Tem mais pares que o atual, mas menos da metade da área e da profundidade. **Limitação documentada.** |
| Metacarpo estrutural, sem esconder defeito | ✅ A mão fecha limpa com ou sem ele; ele só acrescenta a curvatura da palma. O efeito visual ainda é **sutil** nas imagens e pode precisar de mais ângulo ou de uma área maior da palma. |
| Identidade visual | ❌ **Inalterada desde a tentativa 4.** A mão ainda parece mais humana que a "luva" da referência. Pede a rodada só de forma que propus, com a sua aprovação visual. |

## Arquivos

- `src/p1_iter5.py`: gera tudo. Rodar com `P1_FAST=1` só mede, e as variáveis `P1_RE`, `P1_RW`, `P1_RK`, `P1_RJ`, `P1_RT` e `P1_MC` refazem a varredura.
- `p1_iter5.blend`: só o braço novo e o rig dele.
- `p1-iter5-medicoes.json`: medições.
- `renders/`: imagens.
- `p1i5-poses.png`: prancha de poses.
- `p1i5-punho-2x-vs-2.5x.png`: comparação de silhueta do punho.
- `../AMPLITUDES.md`: tabela de amplitudes.
- `../amplitudes/`: análise de alcance.
