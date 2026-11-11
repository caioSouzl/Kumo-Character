# Kumo 3D — diagnóstico técnico geral

**Data:** 2026-11-11 · **Objeto auditado:** `kumo_rigged.blend` (modelo oficial) e o sistema ocular `olhos-v5` (variante B) · **Natureza:** somente leitura. Nenhum arquivo foi alterado (hashes em `hashes-antes.sha256`).

- **Ferramenta:** [`src/auditoria_modelo.py`](src/auditoria_modelo.py).
- **Dados brutos:** [`auditoria-dados.json`](auditoria-dados.json).
- **Evidência visual:** [`poses-articulacao.png`](poses-articulacao.png) e `poses/`.
- **Reaproveitado:** a inspeção de topologia de `../inspecao/RELATORIO-INSPECAO-TOPOLOGIA.md`.

## Resumo

O Kumo atual é uma **malha tecnicamente limpa sobre uma base estruturalmente inadequada**. Ele nasceu de um modelo gerado por IA e passou por uma retopologia automática. Isso produziu uma grade uniforme que segue a curvatura da superfície, não a anatomia: é assimétrica, tem olhos e boca apenas pintados, facetas suavizadas e um rig que é só um esqueleto de deformação.

O sistema ocular (v1 a v5) é um conjunto sofisticado de contornos para essas limitações. Ele funciona visualmente, mas é caro e complexo, não é exportável e nunca chegará a zero interseções, porque a causa está na base e não nos olhos.

## A. O que está comprovadamente bom

| Item | Evidência |
|---|---|
| Integridade da malha | 7.398 vértices, 7.396 faces, 100% quads; 0 arestas não-manifold, 0 bordas, 0 vértices soltos, 0 faces degeneradas, 0 duplicados; normais para fora (volume +0,676) |
| Densidade uniforme de textura | Razão p95/p05 de densidade de texel = 1,48 |
| Desempenho do rig base | 8,8 ms por atualização |
| Deformações leves | Cabeça erguer 30°, tronco curvar 30°, coxa abrir 45°, tornozelo 30°, punho 45°, cauda abanar: **0 autointerseções novas** |
| Volume global | Varia menos de 2,5% em todas as poses testadas |
| Contorno (inverted hull) | Funciona e está aprovado |

## B. Problemas comprovados, por gravidade

### 🔴 Críticos (impedem o objetivo de personagem fiel e animável)

| # | Problema | Evidência medida |
|---|---|---|
| C1 | **Desvios de identidade em relação à referência** | Ver a seção C abaixo. Assimetria: só **0,3%** dos vértices têm par espelhado a até 2 mm; desvio mediano de 2,4 cm, máximo de 17,5 cm. |
| C2 | **Mãos e dedos não articuláveis** | Dedos com 2–3 quads de volta; osso `hand.L` com 0,034 de comprimento (o direito tem 0,109); só **5 e 1 vértices** têm a mão como osso dominante. Não existem ossos de dedo. |
| C3 | **Boca apenas pintada** | Não há linha de lábio, cavidade nem osso de mandíbula. Fala e expressões de boca são impossíveis. |
| C4 | **Olhos pintados na pele da cabeça** | Não há órbita aberta, globo nem pálpebra na malha. Tudo o que existe são camadas externas (v1–v5). |
| C5 | **Rig é só um esqueleto FK de deformação** | 30 ossos; **0 restrições, 0 IK, 0 formas de controle, 0 coleções de ossos, 0 drivers**. Sem controles de pé e mão, sem dedos, mandíbula ou olhos. Assimétrico: `upper_arm` E com 0,226 e D com 0,283. |

### 🟠 Altos

| # | Problema | Evidência medida |
|---|---|---|
| A1 | **Articulações colapsam em dobras fortes** | Novos pares de triângulos se atravessando: braço acima da cabeça **+170**; joelho a 120° **+111** (a 90°: +57); cotovelo a 130° **+77**; coxa a 90° **+65**; agachar **+58**; cabeça baixar 30° **+43** (queixo entra no peito). Arestas comprimidas até 5–20% do comprimento e esticadas até 2,3 vezes. |
| A2 | **Pesos de pele irregulares** | **5.523 vértices** com soma de pesos diferente de 1 (mínimo 0,85). O Blender normaliza ao deformar, mas motores de jogo não. **544 vértices** têm mais de 4 influências (máximo 10). |
| A3 | **Sombreamento e cores divergem da identidade facetada** | 7.396 faces suaves, **0 arestas vivas**. A textura tem degradês assados em vez de planos de cor. Cores dominantes contra a paleta da referência: verde principal `#338C3F` (entre o escuro `#1B5E3B` e o médio `#4CAF6B`); manchas `#90A729` contra `#C9D45B` (mais escuras e oliva); barriga `#E3C57F` contra `#EAD9B7` (mais amarela). |
| A4 | **Sistema ocular v5: custo e limites estruturais** | 54.535 faces avaliadas (o corpo tem 7.396); **30,6 ms por atualização**, 3,5 vezes o rig base; 12 cascas, 1 cópia de referência da pele, 4 vazios, 22 imagens, 5 grupos de nós e 10 drivers dentro de nós. Não é exportável para glTF/FBX (Geometry Nodes e borda de pálpebra em shader). Resíduos: 13–22 triângulos tocando a pele na dobra da órbita; pálpebra sem geometria própria; olhar limitado a ±11°. |
| A5 | **Topologia sem anéis anatômicos** | Da inspeção anterior: pescoço com 54% de fluxo diagonal, ombro D com metade da resolução do E, joelho D com 67% diagonal, 21–27% de arestas concêntricas nos olhos e 15% na boca. |
| A6 | **Autointerseção já em repouso** | 10 pares de triângulos se atravessam na pose de repouso. |

### 🟡 Médios

| # | Problema | Evidência |
|---|---|---|
| M1 | UV fragmentado | **2.135 arestas de costura** (projeção automática); 55% do quadrado usado. Pintar ou corrigir a textura à mão é impraticável. |
| M2 | Exportações desatualizadas | `export/*.glb` e `.fbx` não têm o sistema ocular. O sistema v2–v5 não pode ser exportado. |
| M3 | Dados órfãos no arquivo oficial | Material PBR `model` sem usuários, com 3 imagens de 2048 px embutidas; pálpebras antigas ocultas; ação `Pose_Apresentacao`. |
| M4 | Versões pesadas | Cinco versões de olhos com `.blend` de cerca de 9 MB e 30 a 75 MB de renders cada (465 MB no total). |
| M5 | Testes espalhados | Cada versão de olhos tem sua cópia do validador. Antes desta auditoria não havia testes do corpo. |

### 🟢 Baixos

- Ponta da cauda (`tail_09`) com 65% de fluxo diagonal.
- Dedos dos pés sem divisão (o pé funciona como bloco).

## C. Identidade: referência × modelo atual

Comparação visual das quatro vistas (`../renders/comparacao-referencia.png`):

| Elemento | Referência | Modelo atual | Situação |
|---|---|---|---|
| Cabeça | Poliedro facetado, com planos nítidos e um tom por faceta | Volume correto, facetas suavizadas, degradês | 🟠 Diverge |
| Olhos | Grandes, **simétricos**, voltados para a frente; aro marrom na pálpebra superior | **Assimétricos**: meia-largura E 0,280 e D 0,214; o esquerdo aponta mais para o lado (eixos medidos diferentes) | 🔴 Diverge |
| Crista | Topo em ponta + **crista dorsal serrilhada** nas costas | Ponta do topo presente; costas lisas, sem serrilhado | 🔴 Ausente nas costas |
| Focinho e narinas | Linha da boca com leve sorriso, duas narinas | Presentes, pintados | 🟡 Só textura |
| Mãos | 3 dedos + polegar definidos | Massa pouco definida | 🔴 Diverge |
| Pés | 3 dedos frontais | Presentes como relevo | 🟢 Aceitável |
| Cauda | Espiral geométrica, visível à direita na vista frontal | Espiral presente, mas posicionada para trás e à esquerda | 🟡 Posição diverge |
| Manchas | Verde-amarelado claro, formas angulares | Mais escuras e oliva, formas parecidas | 🟡 Cor diverge |
| Proporção | 3,5 cabeças | Próxima; a medir no sistema de testes | 🟡 A medir |
| Contorno | Marrom escuro, traço firme | Presente (inverted hull) | 🟢 Coerente |

## D. Prontidão do rig para as ações pedidas

| Ação | Situação | Motivo |
|---|---|---|
| Caminhar | 🟡 Possível só em FK, sem controle de pé | Não há IK nem controle de planta do pé; coxa a 60° está limpa |
| Correr | 🟠 Limitado | Coxa a 90° e joelho a 90–120° colapsam |
| Virar a cabeça | 🟡 Até cerca de 45° | A 70°: +9 pares, arestas comprimidas a 26% |
| Baixar a cabeça | 🟠 | A 30°, o queixo atravessa o peito (+43) |
| Inclinar o corpo | 🟢 curvar · 🟡 torcer | Torcer 30°: +26 |
| Mover os braços | 🟢 até a horizontal · 🔴 acima da cabeça | +170 pares |
| Manipular objetos e mover os dedos | 🔴 Impossível | Não há dedos nem IK de mão |
| Expressar emoções | 🔴 Só piscar e olhar (v5) | Não há boca nem sobrancelha |
| Mover a cauda | 🟢 abanar · 🟠 enrolar mais | Ver a hipótese H3 |
| Movimentos rápidos e lentos | 🟡 | Sem controles, espaços de pai ou alternância IK/FK |

## E. Hipóteses (ainda não comprovadas)

- **H1.** O teste "braço acima da cabeça" usa um giro aproximado em eixos do mundo. Parte dos 170 pares pode vir da pose, e não só da malha. Os colapsos de joelho e cotovelo são confirmados pela compressão de arestas.
- **H2.** A assimetria da malha pode ser parcialmente intencional (cauda) e parcialmente defeito da IA (olhos, braços). Não há como separar as duas coisas sem a sua decisão.
- **H3.** "Cauda enrolar" (+315) soma 180° numa cauda que já é espiral. O número reflete mais o teste do que um defeito.
- **H4.** O destino final (animação renderizada no Blender ou motor de jogo) não está definido. Ele muda o peso de A2, A4 e M2.

## F. Limitações desta auditoria

- As poses são estáticas e isoladas. Não testei ciclos de animação contínuos.
- A autointerseção conta pares de triângulos, não profundidade.
- A comparação de identidade é visual, sobre renders e a prancha da referência. A referência é um desenho 2D, não um modelo.
- O desempenho foi medido em modo sem interface (avaliação da cena), não como taxa de quadros na viewport.
