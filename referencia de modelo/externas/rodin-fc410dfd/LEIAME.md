# Kumo — geração Rodin Gen-2.5 (referência 3D externa)

- **ID da geração:** `fc410dfd-caab-423a-8928-47542680b15e` (conta do dono, Hyper3D CLI 0.3.1, 2026-11-09). Custo: 0,5 crédito.
- **Entradas** (`entradas/`): 5 vistas de um único assunto cada, recortadas das referências oficiais: frente, 3/4, perfil e costas (referência 01) e rosto (referência 02). Modo: `Gen-2.5-Medium`, malha `Quad`, `glb`.
- **Arquivos:** `base_basic_pbr.glb` (textura difusa, metal/rugosidade e normal map), `base_basic_shaded.glb` e `texture_emissive.png`.
- **Renders** (`renders/`): ortográficas com a textura difusa em emissão.

## Malha

| | |
|---|---|
| Vértices / faces | 17.884 / 33.178 |
| Formato das faces | 100% triângulos (o GLB triangula; o modo Quad não sobrevive à exportação) |
| Arestas não-manifold | 2.546 |
| Objetos | 1 (corpo, olhos e cauda numa única malha) |

## Silhueta contra a referência (IoU corpo inteiro / só cabeça)

| Vista | Rodin | Kumo atual (P1/P2) |
|---|---|---|
| Frente | 0,748 / 0,909 | 0,857 / 0,953 |
| 3/4 | 0,691 / **0,917** | 0,730 / 0,714 |
| Perfil | **0,860** / **0,937** | 0,804 / 0,912 |
| Costas | **0,877** / 0,936 | 0,851 / 0,943 |

O Rodin foi normalizado pela altura total (1,96 H); o Kumo atual, pela escala do modelo. Na frente e nas costas, a cauda do Rodin fica escondida atrás do corpo, o que derruba o IoU do corpo inteiro.

**Uso recomendado:** referência 3D e molde (shrinkwrap) para a malha deformável v2. Não é modelo final: triangulado, com arestas não-manifold e sem anéis de deformação.
