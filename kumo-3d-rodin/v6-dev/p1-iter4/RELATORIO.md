# P1 iteração 4: braço e mão reconstruídos a partir da referência

**Situação: não aprovado na minha avaliação.** Os critérios foram atingidos só em parte. Parei aqui, como você pediu, e documentei o que falta. Há uma nova proposta no fim.

## Escopo e proteções

- **Nada foi alterado** no modelo oficial nem nas tentativas anteriores (`v6-dev/p1/` está intacta).
- **Hashes:** os de `auditoria/hashes-antes.sha256` conferem.
- **Ossos corretivos:** nenhum foi acrescentado.
- **Arquivos desta iteração:**
  - `src/p1_iter4.py` gera tudo;
  - `p1_iter4.blend` tem só o braço novo e o rig dele;
  - `p1-iter4-medicoes.json` guarda as medições;
  - `renders/` guarda as imagens;
  - `p1i4-identidade.png` e `p1i4-poses.png` são as pranchas;
  - `MEDIDAS-REFERENCIA.md` traz as medidas.

## O que mudou em relação à tentativa 3

- **Forma:** vem das medidas da referência. Do modelo atual vieram só o ombro e a régua do tronco (ver `MEDIDAS-REFERENCIA.md`).
- **Malha:** anéis de 12 vértices, mais finos que antes.
  - O cotovelo ganhou volume atrás (olécrano) e ficou 35% mais fino na dobra da frente.
  - Os anéis do cotovelo e do punho estão espaçados de acordo com o raio, e não comprimidos.
- **Punho:** afina até 0,092 m e depois abre para a palma. Isso corrige o punho redondo.
- **Mão:** a palma termina em 3 colunas de dedo separadas por faixas estreitas, e os dedos não nascem colados.
  - Os dedos são curtos e grossos (medidos na referência) e levemente curvados para a palma.
  - O polegar sai da lateral medial da palma, primeiro para fora e depois para baixo e para a frente.
- **Pesos procedurais:**
  - Calculados na malha base, pela posição exata de cada anel. A subdivisão interpola esses pesos.
  - Transição de 0,12 m de cada lado do cotovelo, que nunca alcança o ombro nem o punho.
  - O pivô de cada dedo e do polegar fica dentro da palma.
  - No máximo 3 influências por vértice, com soma 1.

## Medições (mesmo método da auditoria e das tentativas 1 a 3)

**Repouso:** atual 0 cruzamentos, novo **0** (0 reais, 0 rasantes).

**Como ler cada célula:** pares novos (quantos deles são reais) · área dos triângulos que se atravessam de verdade · profundidade máxima · menor razão de compressão de aresta.

**Como separei reais de falsos positivos:**
- **Real:** um triângulo atravessa o outro em 0,5 mm ou mais.
- **Rasante:** menos de 0,5 mm. É contato ou ruído numérico, ou seja, possível falso positivo.

A contagem de pares depende da densidade da malha: a região do braço atual tem 329 vértices e o braço novo tem 1.354. Por isso a área e a profundidade são as medidas mais justas para comparar.

| Pose | Atual | P1 iteração 4 |
|---|---|---|
| Braço na horizontal | 0 (0 reais) · 0 cm² · 0.0 mm · 0.57 | 0 (0 reais) · 0 cm² · 0.0 mm · 1.0 |
| Braço à frente 90° | 0 (0 reais) · 0 cm² · 0.0 mm · 0.704 | 0 (0 reais) · 0 cm² · 0.0 mm · 1.0 |
| Braço para trás 40° | 0 (0 reais) · 0 cm² · 0.0 mm · 0.827 | 0 (0 reais) · 0 cm² · 0.0 mm · 1.0 |
| Torção do úmero 45° | 0 (0 reais) · 0 cm² · 0.0 mm · 0.544 | 0 (0 reais) · 0 cm² · 0.0 mm · 1.0 |
| Cotovelo 45° | 0 (0 reais) · 0 cm² · 0.0 mm · 0.506 | 0 (0 reais) · 0 cm² · 0.0 mm · 0.705 |
| Cotovelo 90° | 6 (5 reais) · 11.08 cm² · 2.98 mm · 0.217 | 0 (0 reais) · 0 cm² · 0.0 mm · 0.369 |
| Cotovelo 130° | 77 (75 reais) · 205.06 cm² · 14.23 mm · 0.194 | 121 (88 reais) · 75.24 cm² · 6.4 mm · 0.272 |
| Torção do antebraço 60° | 0 (0 reais) · 0 cm² · 0.0 mm · 0.518 | 0 (0 reais) · 0 cm² · 0.0 mm · 0.866 |
| Punho +45° | 0 (0 reais) · 0 cm² · 0.0 mm · 0.617 | 0 (0 reais) · 0 cm² · 0.0 mm · 0.269 |
| Punho −45° | 0 (0 reais) · 0 cm² · 0.0 mm · 0.491 | 0 (0 reais) · 0 cm² · 0.0 mm · 0.269 |
| Punho lateral +30° | 0 (0 reais) · 0 cm² · 0.0 mm · 0.65 | 0 (0 reais) · 0 cm² · 0.0 mm · 0.46 |
| Punho lateral −30° | 0 (0 reais) · 0 cm² · 0.0 mm · 0.824 | 0 (0 reais) · 0 cm² · 0.0 mm · 0.46 |
| Cotovelo 90° + punho 45° | 6 (5 reais) · 11.08 cm² · 2.98 mm · 0.217 | 0 (0 reais) · 0 cm² · 0.0 mm · 0.269 |
| Mão fechada (70°/70°, polegar 35°) | sem dedos | 3 (0 reais) · 0 cm² · 0.43 mm · 0.133 |
| Mão aberta (dedos abertos 15°) | sem dedos | 0 (0 reais) · 0 cm² · 0.0 mm · 0.696 |

**Fechamento da mão por ângulo** (reais): 30°: 0, 35°: 0, 40°: 0, 45°: 0, 50°: 0, 55°: 0, 60°: 0, 65°: 2, 70°: 0. A 65° aparecem 2 pares de 0,6 mm.

**Desempenho:** 0,14 ms por atualização para o braço novo sozinho. O modelo atual inteiro mediu 0,28 ms neste mesmo teste sem interface.

**Malha:** 1.354 vértices, 100% quads, nenhum vértice sem peso.

## Critérios

| Critério | Resultado |
|---|---|
| Sem cruzamentos em repouso | ✅ 0 |
| Melhor que o atual: braço, cotovelo até 90°, torções, punho | ✅ zero cruzamentos onde o atual tinha 6 a 90° |
| Melhor que o atual: cotovelo a 130° | ⚠️ Misto. Área atravessada 75 cm² contra 205; profundidade 6,4 mm contra 14,2; mas **88 pares reais contra 75**. |
| Compressão das arestas no punho | ❌ Pior: 0,27 contra 0,62 a ±45°. A dobra do punho aperta mais (vincos visíveis na prancha), embora sem cruzamentos. |
| Mão: 3 dedos separados e polegar legível | ✅ Abre e fecha sem cruzamentos reais. |
| Identidade visual da referência | ❌ Ainda não. A mão parece mais uma mão humana aberta que a "luva" grossa de dedos curvados do desenho. O braço ficou um pouco mais fino que o desenho e o ombro escurece na junção com o tronco. É preciso o seu olho aqui. |

## Por que parei

O seu critério pede superar o atual em deformação **e** manter a identidade. Não cheguei a nenhum dos dois por inteiro:
1. **Cotovelo a 130°:** é contato real do antebraço contra o bíceps. Só com ossos e pesos, sem corretivos, uma dobra de 130° num braço dessa espessura sempre se atravessa. Só reduzi a área e a profundidade.
2. **Punho:** a transição mais curta, que evita cruzamentos, aperta as arestas da dobra.
3. **Identidade da mão:** ajustei as medidas, mas a forma geral (palma larga e dedos em leque) ainda lê como mão humana.

## Nova proposta

1. **Cotovelo a 130°.** Escolher uma de três opções:
   - (a) Aceitar área e profundidade como critério para dobras extremas.
   - (b) Limitar o cotovelo a cerca de 110° no rig. É comum em personagens cartoon, e a 90° o resultado já é perfeito.
   - (c) Deixar 130° para a etapa de ossos corretivos, que só começaria com a sua aprovação.
2. **Punho.** Mais um anel na dobra e janela de peso de 0,06. Isso deve subir a compressão mínima, mas é preciso testar se não volta a cruzar.
3. **Identidade da mão (precisa do seu olho).** Uma rodada só de forma:
   - dedos mais juntos e curvados (menos leque);
   - palma mais estreita e mais alta;
   - polegar mais encostado;
   - braço 10% mais grosso.
   Depois, apresentar a prancha ao lado da referência para você aprovar antes de mexer em pesos de novo.
