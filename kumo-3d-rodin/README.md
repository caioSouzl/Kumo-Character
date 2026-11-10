# Kumo — modelo 3D oficial (Rodin Gen-2.5)

**Decisão do dono (2026-11-10):** o modelo gerado no Hyper3D/Rodin passa a ser o **modelo oficial do Kumo**. O trabalho com o modelo procedural (`kumo-3d-toon/`) foi **encerrado e arquivado**, sem nada apagado.

![referência × modelo oficial](renders/comparacao-referencia.png)

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `base_basic_pbr.glb` | Modelo original do Rodin com textura PBR (difusa, metal/rugosidade, normal). Use em motores de jogo e na web. |
| `base_basic_shaded.glb`, `texture_emissive.png` | Variantes entregues pelo Rodin |
| `kumo_rodin.blend` | Cena do Blender pronta: modelo na escala do Kumo (pés em z = 0, altura total 1,96 = 1,96 cabeças), material toon de cor chapada, contorno por casca invertida e câmeras ortográficas (frente, 3/4 a 40°, perfil, costas, rosto) |
| `src/kumo_rodin_scene.py` | Gera o `.blend` e as renders a partir do GLB: `python src/kumo_rodin_scene.py --render --res 1400` (precisa de `bpy`) |
| `renders/` | Turnaround, vistas, rosto e comparação com a referência |

## Origem

- Geração `fc410dfd-caab-423a-8928-47542680b15e` na conta do dono, feita com a skill `.claude/skills/hyper3d-rodin`.
- Entradas: 5 recortes das referências oficiais (frente, 3/4, perfil, costas e rosto). Gen-2.5-Medium, 0,5 crédito.
- Cópia de referência intocada: `referencia de modelo/externas/rodin-fc410dfd/`.

## Ajustes feitos sobre o GLB (só na cena `.blend`; o GLB original fica igual)

- **Escala e posição:** padronizadas no sistema de medidas do projeto (fator 1,0356).
- **Costuras de textura soldadas por posição:** os UVs ficam nos cantos das faces, então a textura não muda. Eram 2.546 arestas não-manifold e agora são **0**.
- **Normais recalculadas para fora**, necessárias para o contorno funcionar.
- **Contorno por casca invertida:** modificador Solidify com normais invertidas, cor `#5B3A2E`. A espessura é ajustável pela propriedade `outline_thickness` do objeto (padrão 0,02).

## Malha

16.591 vértices (após a solda) e 33.178 faces, todas triângulos, numa malha única com olhos, corpo e cauda. Fechada e sem arestas defeituosas depois da solda.

## Silhueta contra a referência (IoU corpo inteiro / só cabeça)

| Frente | 3/4 | Perfil | Costas |
|---|---|---|---|
| 0,748 / 0,909 | 0,691 / 0,917 | 0,860 / 0,937 | 0,877 / 0,936 |

## Limitações conhecidas

- **Sem esqueleto e sem expressões.** Para animar, os caminhos são: o rig automático do Rodin (`hyper3d rigging`, gasta créditos, pose de corpo inteiro) ou um rig próprio no Blender. A malha triangulada deforma pior que quads nos olhos e na boca.
- **A cauda fica atrás do corpo** nas vistas de frente e de costas. Na referência ela aparece ao lado.
- **Facetas um pouco suavizadas** pela textura em relação à referência.
