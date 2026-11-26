# Movimento do Kumo (26/11)

**Pedido do Caio:** "Pode resolver tudo". Eram as pendências antigas:
- ponta da cauda que não esticava;
- ossos corretivos de costas e pescoço;
- pés presos ao chão e cabeça estável;
- caminhada, corrida e pulo;
- losangos de piscar na Central.

**Base:** os olhos em calota aprovados (`../olhos-novos/calota/kumo_v7_calota.blend`). O resultado é `kumo_v8_movimento.blend`.

Fotos: `folha_cauda.png`, `folha_corretivos.png`, `folha_ik.png`, `folha_animacoes.png` e o vídeo `animacoes_kumo.mp4`.

## 1. Cauda que estica até a ponta

**O problema:** os 10 ossos antigos acabavam antes do caracol. Uns 30 cm de malha ficavam sem osso, e a ponta continuava enrolada com a cauda esticada.

**Agora:**
- **Linha central:** feita pelo meio da própria malha, medindo a distância pela superfície desde a base. No caracol, onde as voltas ficam coladas, essa medida diz em que volta cada ponto está.
- **Ossos:** 26, mais curtos para a ponta (10 cm na base, menos de 1 cm no fim). O eixo X de todos é o X do mundo: girar em X enrola ou desenrola a cauda no plano dela.
- **Pesos:** refeitos na pele e no contorno de jogo. O contorno é uma casca 2 cm para fora da pele, e cada ponto dele segue o ponto da pele de onde saiu.

**Medidas:**

| | Antes | Agora |
|---|---|---|
| Cauda esticada | Caracol de ~30 cm sobra na ponta | Reta até ~3 cm da pontinha |
| Contorno longe da pele, com a cauda desenrolando | Até 85 cm (uma cunha marrom) | 2 cm em todos os estados (a espessura da casca) |

## 2. Ossos corretivos de pescoço e costas

**Onde amassava:** a cabeça do Kumo é grande e apoia direto nos ombros. Inclinada ou levantada, a borda de baixo dela entrava nos ombros e nas costas.

**Os ossos:** 8 ossos `corr_*`, presos ao peito, aos ombros, à cabeça ou ao quadril, cada um com peso numa região pequena da pele:

| Osso | Quando age | O que faz |
|---|---|---|
| `corr_trapezio.L/.R` | Cabeça de lado | O ombro desce do lado para onde a cabeça inclina |
| `corr_borda.L/.R` | Cabeça de lado | A borda de baixo da cabeça sobe um pouco |
| `corr_borda_tras` | Cabeça para cima | A borda de trás da cabeça sobe |
| `corr_garganta` | Cabeça para baixo | A garganta entra um pouco |
| `corr_lombar` | Tronco dobrando | A lombar se ajusta |
| `corr_nuca` | Cabeça para cima | Ficou parado (0 cm): a medida não melhorou com ele andando |

**Como funciona:**
- **O giro que move cada osso:** `MCH_cabeca_rel` mede o giro de pescoço + cabeça em relação ao peito; `MCH_peito_rel` mede o de coluna + peito em relação ao quadril.
- **Deslocamento:** uma restrição Transformation leva o giro ao deslocamento do osso. O tamanho e o sentido foram escolhidos medindo a pele.
- **Pesos:** cada corretivo recebe só parte do peso do próprio pai. Parados, não mudam nada.

**Cruzamentos da pele** (pares de triângulos que se atravessam):

| Pose | Antes | Agora |
|---|---|---|
| Cabeça de lado 45°, esquerda | 56 | 14 |
| Cabeça de lado 45°, direita | 41 | 12 |
| Cabeça para cima 55° | 36 | 10 |
| Cabeça para baixo 55° | 16 | 13 |
| Costas para trás, para o lado, torção | 7 a 12 | 8 a 12 |

## 3. Pés presos ao chão e cabeça estável

**Pernas:**
- `pe_ik.L/.R` são os controles dos pés: a canela tem IK de 2 ossos, e o pé copia o giro do controle;
- `joelho.L/.R` dizem para onde o joelho aponta;
- a propriedade `ik_pernas` liga e desliga o IK.

**Cabeça estável:** com a propriedade `cabeca_estavel` em 1, a cabeça mantém o giro do mundo, e quem a gira é `MCH_cabeca_mundo`. É a "cabeça de galinha" do estudo de rig.

**Conferido:**
- **Repouso:** igual com o IK ligado e desligado (0,0 mm).
- **Agachar:** o quadril desce 12 cm e os pés não saem do lugar.
- **Cabeça estável:** com o tronco inclinado 20°, a cabeça fica com 0,0° de desvio.

## 4. Caminhada, corrida e pulo

As três são animadas no lugar (o jogo move o personagem), a 24 quadros por segundo.

| Ação | Duração | Passo | Velocidade no jogo |
|---|---|---|---|
| `Caminhar` | 24 quadros (1 s), em loop | 0,18 m | 0,36 m/s |
| `Correr` | 16 quadros (0,67 s), em loop, com fase no ar | 0,26 m | 0,78 m/s |
| `Pular` | 36 quadros (1,5 s) | 40 cm de altura | |

- **Pés e braços:** no apoio, o pé fica parado no chão (0,0 mm de deslize). Os braços balançam ao contrário das pernas.
- **Corpo:** o quadril sobe e desce e gira um pouco. A cabeça fica estável e a cauda balança em onda.
- **Pulo:** preparo agachado com os braços para trás, impulso com os braços para cima, joelhos encolhidos no ar e pouso amortecido, com uma apertada de olhos.
- **Perna curta:** a perna do Kumo é curta (30 cm). Por isso o quadril anda sempre um pouco abaixado, com os joelhos dobrados; com a perna esticada, o pé ficaria para trás.

## 5. Jogo e Central

**Arquivos do jogo** (`jogo/`): `kumo_v8_jogo.glb` (9,6 MB) e `kumo_v8_jogo.fbx` (7,8 MB).
- **Animações:** `Caminhar`, `Correr` e `Pular`, mais `Boca_Abrir`, `Lingua_Lancar` e `Pose_Apresentacao`.
- **Restrições:** o IK, os corretivos, a cabeça estável e o olhar não vão no arquivo. O exportador grava o resultado deles em cada quadro.
- **Conferência:**
  - pés, cabeça, quadril, corretivos, olho e cauda saem iguais ao Blender (0,0 mm);
  - a reimportação do GLB, do FBX e do GLB da Central dá 0,01 mm de diferença.
- **Fora das animações:** o jogo refaz as contas com `corretivos.json` e `olhar.json`.

**Central** (`central/kumo_central.glb`, publicado como `kumo.wasm`):
- **Animações do Kumo:** botões Caminhar, Correr, Pular, Abrir a boca e Lançar a língua, que tocam as animações do arquivo, e "Parar e voltar à pose".
- **Cauda:** "Enrolar" para a esquerda estica até a reta (cada ponto do controle é um meio-termo); para a direita, enrola mais.
- **Corretivos:** a página faz a mesma conta do Blender. Contra o que o Blender gravou no pulo, a diferença é de 0 mm.
- **Losangos de piscar:** em cima de cada olho. Arrastar para baixo fecha; dois toques abrem ou fecham de uma vez.

## Para refazer (a partir de `movimento/`)

```
blender --background ../olhos-novos/calota/kumo_v7_calota.blend --python src/cauda.py -- $PWD/kumo_v8_movimento.blend $PWD/medicoes_cauda.json
blender --background kumo_v8_movimento.blend --python src/corretivos.py -- $PWD/medicoes_corretivos.json
blender --background kumo_v8_movimento.blend --python src/ik.py -- $PWD/medicoes_ik.json
blender --background kumo_v8_movimento.blend --python src/animacoes.py -- $PWD/medicoes_animacoes.json
blender --background kumo_v8_movimento.blend --python src/exportar.py -- $PWD/jogo $PWD/central
```

Fotos e vídeo: `src/fotos_cauda.py`, `src/fotos_tronco.py`, `src/fotos_ik.py`, `src/video_anim.py`. A medida dos cruzamentos está em `src/medir_tronco.py`.
