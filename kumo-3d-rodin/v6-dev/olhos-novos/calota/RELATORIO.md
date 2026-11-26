# Olhos em calota (25/11)

**Pedido do Caio:**
- As pálpebras de cima entravam em conflito com o globo na versão do decal.
- "Refaça um olho, da mesma forma, mas que dessa vez fosse uma esfera ou uma semiesfera", para não distorcer a íris, a pupila e o movimento da pálpebra.
- Escolheu a **opção 1:** calota de 10 cm, pálpebras refeitas e olhar limitado à abertura.
- Aprovou o resultado em 25/11.

## Como ficou

| Peça | O que é |
|---|---|
| Globo (`KumoOlho_Globo.L/.R`) | Pedaço de esfera com o branco, a íris e a pupila numa textura. Preso ao osso `olho.L/.R`, gira inteiro, sem esticar a arte |
| Pele em volta (`KumoOlho_Anel.L/.R`) | A pele em volta do olho com a abertura em elipse, a membrana e o contorno |
| Faixa da borda (`KumoOlho_Aro.L/.R`) | Casca um pouco maior que o globo, parada, com a mesma textura da pele em volta. Cobre a beirada da esfera quando o olho gira |
| Tampa da boca (`KumoOlho_Tampa.L/.R`) | Fica atrás da fenda da boca, na cor de dentro da boca. Esconde o globo quando o olho olha para baixo |
| Pálpebras (`KumoJogo_Palpebra_sup/inf.L/.R`) | Refeitas sobre uma esfera 6 mm maior que o globo. Abertas, ficam dobradas na borda; fechadas, se encontram no meio |

**Medidas:**

| Olho | Raio da abertura | Raio do globo | Ângulo da abertura |
|---|---|---|---|
| Esquerdo | 0,254 m | 0,372 m | 43° |
| Direito | 0,220 m | 0,291 m | 49° |

- **Profundidade da calota:** 10 cm.
- **Olhar:** ±11° em cada eixo, até cerca de 15,6° na diagonal.

## Bordas (o que foi preciso acertar)

O Kumo não é redondo em volta dos olhos. A bochecha recua e a boca fica perto. Por isso, girando, a esfera saía da pele em alguns pontos. Cada correção foi conferida nos 8 olhares extremos:

1. **Globo:** sai só o que nunca chega à abertura. Os pontos que aparecem na abertura num olhar, mas sairiam da pele em outro, afundam o necessário (439 no olho esquerdo, 512 no direito).
2. **Faixa da borda:**
   - cobre o globo até onde ele pode chegar;
   - sai onde fica bem por dentro da pele;
   - perto da boca, vira a tampa escura;
   - pedaços soltos são retirados.

**O que sobrou:** com o olho esquerdo olhando todo para baixo, um tracinho branco de poucos pixels no canto da boca.

## Rig

- **Ossos `olho.L/.R`:**
  - ficam no centro da esfera;
  - **Damped Track** num alvo a 1,35 m;
  - o alvo anda com `controle_olhar`.
- **Piscada:** shape keys `Piscar_25/50/75/100`, com os mesmos drivers de antes no `controle_olhos`.

## Jogo (`jogo/`) e Central (`central/`)

- **Arquivos do jogo:** `kumo_v7_jogo.glb` (9,3 MB) e `kumo_v7_jogo.fbx` (5,3 MB).
  - Materiais de emissão por textura.
  - A pele em volta e a faixa saem com transparência recortada (MASK), sem problema de ordem de desenho.
- **Reimportação:** GLB, FBX e o GLB da Central, com **0,0 mm** de diferença em todas as peças.
- **Olhar no motor de jogo:**
  - o GLB e o FBX não levam constraints;
  - o jogo gira o osso `olho.L/.R` com as contas de `olhar.json` (em coordenadas do glTF e do Blender);
  - a Central faz a mesma conta.
- **Central:**
  - `central/kumo_central.glb` (sem normais e sem animações), publicado como `kumo.wasm`;
  - os losangos do olhar ficam no centro da pupila (`P` em `olhar.json`).

## Arquivos

| Arquivo | O que é |
|---|---|
| `kumo_v7_calota.blend` | Kumo com os olhos em calota |
| `jogo/kumo_v7_calota_jogo.blend`, `jogo/kumo_v7_jogo.glb`, `jogo/kumo_v7_jogo.fbx` | Versão de jogo e exportações |
| `jogo/olhar.json`, `central/olhar.json` | Contas do olhar para o jogo e a Central |
| `folha_frente.png`, `folha_34_lado.png`, `renders/` | Fotos aprovadas |
| `medicoes_calota.json`, `jogo/medicoes_exportacao.json` | Medições |

Para refazer, a partir de `olhos-novos/`:

```
blender --background kumo_v6_olhos_novos.blend --python src/olhos_calota.py -- $PWD/calota/kumo_v7_calota.blend
blender --background calota/kumo_v7_calota.blend --python src/fotos.py -- $PWD/calota/renders
blender --background calota/kumo_v7_calota.blend --python src/exportar_calota.py -- $PWD/calota/jogo $PWD/calota/central
```

## Ajustes de 26/11 (depois do teste do Caio na Central)

- **Olho fixo, só a íris gira** (ideia do Caio):
  - o globo branco (`KumoOlho_Globo.L/.R`) fica parado, preso à cabeça;
  - a íris com a pupila virou uma peça própria (`KumoOlho_Iris.L/.R`), um pedaço da mesma esfera 1 mm acima do globo, preso ao osso do olho;
  - o globo não sai mais da abertura, então não há fresta nos cantos nem beirada na bochecha, nem olhando na diagonal (15,6°).
- **Pálpebras dentro da abertura:** em cada estágio da piscada, a parte da pálpebra que fica sob a pele desce para baixo dela. Não aparece mais maior que o olho, nem embaixo da mandíbula. Fechada, cobre o olho inteiro.
- **Arquivos:** os do jogo e da Central foram refeitos.
