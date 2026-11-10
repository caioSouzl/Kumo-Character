# Especificação oficial — Kumo 3D (2,5D cel-shaded)

Este é o registro dos elementos **aprovados**. Um item só entra aqui depois de aprovado. Para mudar um item já aprovado, é preciso primeiro apresentar a divergência e pedir aprovação; nada aqui é substituído direto.

## Fonte da verdade

| Item | Valor | Aprovado em |
|---|---|---|
| Referências oficiais | `referencia de modelo/kumo-referencia-01.png` (vistas de rotação) e `kumo-referencia-02.png` (detalhes) | 2026-11-08 (fornecidas pelo dono) |
| Técnica | Modelo 3D com cel-shading / toon shading (2,5D), para animação 3D e 2D | 2026-11-09 (pedido do dono) |
| Arquivo base | `kumo-3d-toon/base/kumo_toon_base_v1.blend` + `base/kumo_toon_base_v1.py`, congelados | 2026-11-09 ("mantenha esse arquivo base") |
| P1: topologia da cabeça | 25 vértices nomeados (lista `HEAD_VERTS`), 40 faces, 0 n-gons, 15 faces frontais | proposta aprovada em 2026-11-09; resultado no [RELATORIO-002](RELATORIO-002.md), aguardando sua conferência visual |
| P2: crista como geometria | 4 faces de material verde-escuro (losango frontal, topo, crista traseira, nuca) | proposta aprovada em 2026-11-09; resultado no RELATORIO-002 |
| P8: vista 3/4 | segue a imagem de referência; câmera a 40° | decisão do dono em 2026-11-09 |
| P9: cauda | segue a imagem de referência em cada vista; pose por vista: 3/4 −45°, costas +80°, frente e perfil 0° | decisão do dono em 2026-11-09 |
| **Arquitetura deformável** | Personagem totalmente deformável: topologia de quads nas regiões que deformam; loops em olhos, boca, focinho, mandíbula, pescoço, ombros, cotovelos, punhos, quadris, joelhos e tornozelos; sem subdivisão nem suavização; partes rígidas só com justificativa técnica; pronto para rig facial e corporal | decisão do dono em 2026-11-09 (plano em [PLANO-003](PLANO-003-arquitetura-deformavel.md), aguardando aprovação) |
| **Contorno** | Casca invertida (geometria expandida, normais invertidas, renderização de faces de trás) como sistema principal; espessura ajustável e constante; sem artefatos em sobreposições e articulações; acompanha a deformação; compatível com Blender e tempo real | decisão do dono em 2026-11-09 |
| **Identidade visual (restrição crítica)** | Antropomórfico, bípede, facetado e angular, low poly, fiel às referências, cel shading controlado. A topologia deformável não pode comprometer a silhueta angular, as proporções faciais, a geometria da cabeça, a crista nem a identidade. | decisão do dono em 2026-11-09 |
| **D3: pose de repouso** | A-pose, braços cerca de 45° abaixo da horizontal, pernas levemente afastadas, mãos e dedos separados, cauda natural, cabeça alinhada. A pose da referência é preservada como pose de apresentação. | decisão do dono em 2026-11-09 |
| **D4: expressões** | Sistema híbrido: shape keys para pálpebras, boca, bochechas e expressões; ossos para a mandíbula e os olhos; controles independentes por olho | decisão do dono em 2026-11-09 |
| **D5: pupilas** | Pequenas malhas independentes, presas ao respectivo globo ocular | decisão do dono em 2026-11-09 |
| **Orçamento de polígonos** | Sem limite rígido: a qualidade da topologia e das deformações prevalece | decisão do dono em 2026-11-09 |
| **F1: cabeça deformável** | `v2-deformavel/`: 745 faces, 97 % quads, 0 n-gons, anéis nos olhos e na boca, rig de teste; IoU contra a P1 de 0,99 a 1,00 | executada; aguardando aprovação visual e técnica ([RELATORIO-F1](../v2-deformavel/relatorios/RELATORIO-F1.md)) |
| **F1.2: segunda versão visual da cabeça** | `v2-deformavel/f1.2/`: boca em "^", pupilas e brilho medidos na referência 01, faixa escura da pálpebra, narinas inclinadas, só linhas marcadas, 2 anéis de dobra, pesos da mandíbula corrigidos; IoU contra a P1 de 0,983 a 0,997 | **aprovada pelo dono em 2026-11-10** ("o resultado do V2 está ótimo") ([RELATORIO-F1.2](../v2-deformavel/f1.2/RELATORIO-F1.2.md)) |
| **Versionamento** | A base original não é modificada sem autorização explícita; geometria, scripts e shaders novos ficam versionados em separado | decisão do dono em 2026-11-09 |

## Elementos em avaliação (ainda não aprovados)

Os itens abaixo existem na base v1, mas ainda não foram aprovados individualmente. O diagnóstico de cada um está em [`DIAGNOSTICO-001.md`](DIAGNOSTICO-001.md).

| Elemento | Estado na base v1 | Pendência |
|---|---|---|
| Proporções (cabeça 1,00 H · tronco 0,59 H · pernas 0,37 H · total 1,96 H) | medidas na referência 01 | aprovação |
| Ombro e nuca da cabeça | desvios S1 e S2; cabeça larga na 3/4 e canto vivo na nuca (RELATORIO-002) | P3 |
| Olhos | sobressaem no perfil (S3) | P4 |
| Mãos (3 dedos + polegar) | posição baixa (S4) | P5 |
| Pés (3 dedos) | calcanhar curto (S5) | P6 |
| Cauda em espiral | menor e mais baixa (S6) | P7 |
| Paleta | `#1B5E3B` `#4CAF6B` `#C9D45B` `#EAD9B7` `#F4B642` `#5B3A2E` (da referência) | aprovação |
| Shader toon | 4 faixas chapadas, luz fixa (−0,55, −0,62, 0,58) | aprovação |
| Contorno | Freestyle `#5B3A2E`, espessura 3,0. Será substituído pela casca invertida na v2. | substituição decidida; implementação na F5 do PLANO-003 |
| Expressões (8) | pupilas, pálpebras planas, sobrancelhas, bocas | aprovação, P10 |

## Histórico de decisões

| Data | Decisão |
|---|---|
| 2026-11-09 | Base v1 congelada como ponto de partida para alterações futuras. |
| 2026-11-09 | P1, P2 aprovadas; P8 e P9: seguir a imagem de referência (inclui a cauda). Executadas, ver RELATORIO-002. |
| 2026-11-09 | Arquitetura deformável + casca invertida + preservação de identidade + versionamento separado (decisões do dono). PLANO-003 apresentado para aprovação. |
| 2026-11-09 | PLANO-003 aprovado com D3, D4 e D5; F1 autorizada com condições (silhueta e facetas preservadas, sem subdivisão nem suavização, testes reais de deformação, comparações e wireframes, sem limite rígido de polígonos). F1 executada em `v2-deformavel/`. Referência complementar `kumo-referencia-03-analise-geometrica.png` adicionada. |
| 2026-11-09 | F1.2 feita a pedido do dono ("segunda versão visual"), com as referências 01 e 03. A F1.0 foi preservada. A F2 não foi iniciada. |
| 2026-11-10 | F1.2 aprovada. Geração Rodin `fc410dfd` guardada como referência 3D externa. Skill `hyper3d-rodin` criada em `.claude/skills/`. |
| 2026-11-09 | Protocolo de trabalho: inspecionar → diagnosticar → propor → só alterar com autorização → render ortográfica e relatório após cada alteração. |
