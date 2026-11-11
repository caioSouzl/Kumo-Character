# P1 iteração 6: refinamento visual da mão

**Situação: para a sua aprovação visual.** Não me autoaprovo. A iteração 5 e as anteriores estão intactas, assim como o modelo oficial (os hashes da auditoria conferem). Nenhum osso foi acrescentado.

## O que foi feito

A iteração 6 muda **só a forma da mão**: braço, cotovelo e punho são os mesmos da iteração 5. O mesmo script gera mais de uma forma de mão (`P1_MAO`):

| Estilo | O que é |
|---|---|
| **I5** | A mão da iteração 5, reproduzida exatamente (mesmas medidas, mão fechada com 0 pares) para comparar nas mesmas câmeras |
| **A, "luva" (proposta)** | Palma mais estreita e mais alta, de perfil arredondado; dedos curtos e grossos, de ponta abaulada, que nascem largos da palma (sem "pescoço"), quase sem leque e curvados para a palma; fenda rasa entre os dedos; polegar em lóbulo maior, saindo da lateral da palma para baixo e para a frente, com curva suave |
| B (descartada) | Dedos curtos um pouco mais separados. Na mão fechada ficou com 15 a 27 cruzamentos reais, então parei nela; as medições estão nos registros desta rodada e não foi para as pranchas |

**Tentativas que não deram certo** (para não repetir):
- Polegar saindo da face da palma: 10 a 40 cruzamentos já em repouso.
- Dedos grossos a ponto de se tocarem, como no desenho: 40 cruzamentos em repouso. Dedos separados não podem encostar uns nos outros sem atravessar, então a proposta A deixa uma fenda de poucos milímetros, que lê como os vincos do desenho.

## Ajustes locais de pesos exigidos pela nova geometria

Os valores da iteração 5 continuam para cotovelo (2,1×), punho (2,5×), base dos dedos (1,5×) e junta dos dedos (1,6×). Na proposta A, três ajustes locais foram necessários e testados:

| Ajuste | Iteração 5 | Proposta A | Motivo medido |
|---|---|---|---|
| Transição de pesos do polegar | 1,0× | **2,0×** | O polegar novo é maior. Com 1,0×, a mão fechada tinha 5 cruzamentos reais polegar–palma; com 1,5×, 5; com 2,0×, 4, e depois 1 com o ajuste seguinte. |
| Gradiente do metacarpo (largura da faixa da palma que segue o osso) | 0,05–0,75 | **−0,25–0,85** | A palma mais alta formava vinco no limite do metacarpo (3 cruzamentos reais na mão fechada); com a faixa mais larga, o vinco some. |
| Pivô do polegar (profundidade dentro da palma) | 0,012 | **0,006** | Com 0,006, a mão fechada fica sem cruzamento real; com 0,020, sobram 2 reais. |

Nenhum desses ajustes muda o osso de metacarpo de função: ele continua estrutural. Esses valores valem só para esta geometria.

## Validação (mesmo método das iterações anteriores)

| Teste | Iteração 5 | Proposta A |
|---|---|---|
| **Repouso** | 0 | **0** |
| Mão aberta (dedos a 15°) | 0 · compressão 0,72 | 0 · 0,61 |
| **Mão fechada** (70°/70°, polegar 35°, metacarpo 20°) | 0 · 0,33 | **0 reais** (6 rasantes, menos de 0,5 mm) · 0,12 |
| Flexão dos dedos a 45° (sem polegar) | 0 · 0,69 | 0 · 0,37 |
| Movimento do polegar (abrir 20°, fechar 35° e 45°) | 0 · 0,41 | 0 · 0,29 |
| Dedos alternados (70°, 30°, 0°, polegar 15°) | 0 · 0,39 | 0 · 0,12 |
| Palma curvada (metacarpo 20°) | 0 · 0,79 | 0 · 0,70 |
| Punho ±45° | 0 · 0,58 | 0 · 0,58 |
| Punho lateral ±30° | 0 · 0,72 | 0 · 0,72 |
| Cotovelo 90° e 100° | 0 | 0 |
| Fechamento progressivo de 30° a 70° | 0 em todos | 0 em todos, **exceto 65°: 1 par real de 0,87 mm** |
| Malha | 1.354 vértices, 100% quads | igual |
| Pesos | até 4 influências, soma 1 | igual |
| Desempenho (braço novo sozinho) | 0,19 ms | 0,13 ms |

**Pioras da proposta A, sem esconder:**
1. **Compressão nas juntas dos dedos:** com os dedos mais grossos e curtos, as arestas internas da junta comprimem mais na mão fechada e nos dedos alternados (0,12 contra 0,33). Não há travessia, mas o vinco é mais forte.
2. **Um par real de 0,87 mm a 65° de fechamento,** entre o polegar e a palma. É uma pose intermediária; nas poses de 60° e 70° não aparece.
3. **Lasca na base do polegar** com a mão aberta: aparece nas duas versões e vem de aresta esticada (esticamento máximo de cerca de 3,1×). Precisa de mais um anel na base do polegar.

## Fidelidade à referência

As proporções foram medidas na vista de frente, igual à leitura da referência. Os valores da referência estão em `MEDIDAS-REFERENCIA.md` da iteração 4; o polegar é estimado, porque fica parcialmente oculto no desenho.

| Proporção | Referência | Iteração 5 | Proposta A |
|---|---|---|---|
| Largura da mão ÷ largura do antebraço | 2,00 | 2,46 | **2,26** |
| Comprimento ÷ largura da mão | 1,14 | 0,80 | 0,83 |
| Comprimento ÷ espessura do dedo | 1,86 | 1,83 | 1,83 |
| Palma ÷ dedo | 1,38 | 1,01 | **1,13** |
| Polegar ÷ dedo | cerca de 0,7 | 0,85 | 1,00 |

**Leitura visual (pranchas):**
- **Melhorou:** dedos curtos, grossos e arredondados, integrados à palma, sem o leque de mão humana; polegar como lóbulo; largura mais perto do desenho.
- **Ainda diverge:**
  - **A mão continua larga e curta demais** (0,83 contra 1,14).
  - O desenho mostra os dedos **mais dobrados para a frente**, com as pontas voltadas para dentro e os nós aparecendo. A proposta ainda lê como mão semiaberta.
  - **O polegar ficou grande demais** (1,00 contra cerca de 0,7). Ele aparece mais para o lado do que no desenho, onde fica junto aos dedos.

## Imagens

- `p1i6-comparacao-vistas.png`: referência, mão do modelo atual, iteração 5 e proposta A, cada uma de frente, de lado, por cima (dorso) e em perspectiva. A mão do modelo atual é renderizada por `src/render_mao_atual.py`, só leitura.
- `p1i6-arame.png`: wireframe da iteração 5 e da proposta A, em repouso e com a proposta A fechada.
- `p1i6-movimentos.png`: repouso, aberta, fechada, dedos a 45°, polegar, dedos alternados e punho ±45°, em perspectiva e de frente, para as duas versões.
- `p1i6-encaixe.png`: referência, iteração 5 e proposta A encaixadas no corpo.

## Próximo passo sugerido (depende da sua avaliação)

Se a direção da proposta A estiver certa, uma rodada curta só de forma:
1. Palma mais longa, para levar o comprimento ÷ largura de 0,83 para perto de 1,1.
2. Curvatura de repouso maior nos dedos, para mostrar os nós como no desenho.
3. Polegar menor (cerca de 0,7 do dedo) e mais junto aos dedos.
4. Mais um anel na base do polegar, para eliminar a lasca e o par de 0,87 mm.

Tudo validado de novo com a mesma bateria de testes.

## Arquivos

- `src/p1_iter6.py`: gera tudo (`P1_MAO=I5|A|B`; `P1_FAST=1` só mede).
- `I5/` e `A/`: arquivos `.blend` (só o braço e o rig), medições `.json` e `renders/`.
- `atual/`: renders da mão do modelo atual.
