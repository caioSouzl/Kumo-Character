# Pesquisa 001 — skills e ferramentas de Blender (2026-11-09)

Fontes lidas: o artigo da Snyk "As 8 principais Claude Skills para modelagem 3D, desenvolvimento de jogos e programação de shaders" (31/03/2026) e os repositórios `blender-agent-studio`, `blender-skills`, `claude-blender` e `blender-mcp`. Só li: **nada foi instalado, e o modelo não foi alterado**.

## Segurança (recomendação do artigo, seguida aqui)

Antes de usar qualquer skill, leia o SKILL.md e os scripts, confira a origem e os `allowed-tools`. Os scripts de validação do `blender-agent-studio` que li (`fit_reference_camera.py`, `compare_reference.py`, `review_likeness.py`, `inspect_asset.py`, `diagnose_topology.py`) não fazem chamadas de rede. Só os arquivos de teste usam `subprocess`, e apenas para chamar o próprio Blender.

## O que se aplica ao Kumo

| # | Fonte | Lição | Situação atual do Kumo |
|---|---|---|---|
| L1 | blender-agent-studio, *likeness-refinement* | **Separar alinhamento de geometria.** Primeiro se ajusta a câmera de cada vista com pontos correspondentes (landmarks) entre o modelo e a referência (`fit_reference_camera.py`, modos `pose` e `framing`, com landmarks reservados para validação). Depois a câmera é congelada e só então se mede a geometria. Não se deve alternar câmera e geometria atrás de um número menor. | Na P8, escolhi o ângulo 3/4 (40°) varrendo IoU de silhueta **depois** de mudar a geometria. O método das ferramentas é mais rigoroso: ajustar a câmera por landmarks (olhos, ponta da crista, focinho, queixo, mãos) e congelar. |
| L2 | blender-agent-studio | "Ângulos gerados podem guiar um design original, mas não verificam a forma invisível de um personagem existente." Referências que discordam entre si devem ser rotuladas pela característica que sustentam. | Bate com D1 e D2: as vistas da referência são inconsistentes entre si em 3D. |
| L3 | blender-skills, *retopology* e *3d-modeling* (artigo) | Quads obrigatórios onde a malha deforma. Triângulos são aceitáveis em malha rígida. Nada de n-gons. Loops concêntricos em volta dos olhos e da boca para expressões. | A cabeça nova tem 34 triângulos, 6 quads e 0 n-gons. Está correto **se a cabeça for rígida** (expressões feitas com peças: pupilas, pálpebras, bocas). Se a boca e os olhos tiverem de deformar a pele, a cabeça precisa de retopologia em quads com loops. |
| L4 | blender-skills, *npr-rendering* e *npr-shaders*; artigo, *shader-techniques* | Contorno: **casca invertida** (Solidify negativo + normais invertidas) funciona em tempo real e em motores de jogo. **Freestyle** dá o melhor controle, mas só existe na renderização do Blender. Cel shading: Shader-to-RGB + ColorRamp (só no EEVEE) ou rampa sobre N·L. | O Kumo usa Freestyle e rampa sobre N·L em emissão (funciona no Cycles, sem GPU). Para animação em tempo real ou exportação a motores, a casca invertida seria necessária. |
| L5 | blender-skills, *lowpoly-style* | Personagem low poly: 500–3.000 triângulos. Sombreamento chapado e faces coplanares unidas. Teste de silhueta em cor sólida. | O corpo está dentro do orçamento. As bocas-decalque (cerca de 9.000 faces) estão fora, o que já é a P10. |
| L6 | blender-skills, *reference-image-match* e *visual-match-checklist* | Fluxo: análise da referência → **câmera primeiro** → silhueta → detalhes → materiais → comparação, no máximo 3 passadas por fase com lista de lacunas. Checklist Match/Close/Miss, com aprovação em pelo menos 8 de 10 categorias. | Já fazemos a comparação numérica (IoU e perfis). Podemos acrescentar a checklist Match/Close/Miss nos relatórios. |
| L7 | claude-blender, blender-mcp | Servidores MCP para controlar um Blender aberto: folha de várias vistas, diff de cena, pontos de restauração. | Exigem Blender com interface e um addon rodando. Aqui usamos o `bpy` sem interface, que cobre o mesmo trabalho por script. Ficam para quando houver um Blender na sua máquina. |

## Propostas decorrentes (aguardando aprovação)

- **M1:** refazer a câmera 3/4 pelo método L1 (landmarks), congelar a câmera e medir a geometria de novo. Pode mudar o valor de 40° da P8 por um ajuste mais preciso, sem mudar a decisão "seguir a referência".
- **M2:** decidir se a cabeça é **rígida** (como está, com expressões por peças) ou **deformável** (exige retopologia em quads com loops nos olhos e na boca, antes do rig).
- **M3:** decidir o contorno: manter o Freestyle (renderização) ou adotar a casca invertida (tempo real e motores), ou ter os dois.
- **M4:** acrescentar a checklist Match/Close/Miss aos relatórios.
