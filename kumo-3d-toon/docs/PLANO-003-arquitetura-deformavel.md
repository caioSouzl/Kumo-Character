# Plano 003 — Arquitetura deformável e contorno por casca invertida

**Data:** 2026-11-09 · **Origem:** decisões de arquitetura do dono ("Character Architecture Decisions — Kumo") · **Estado:** **aguardando aprovação**

Este documento cumpre os passos 1 a 5 do protocolo: inspecionar, identificar o que reconstruir, avaliar a viabilidade, documentar e apresentar. Nenhum modelo foi alterado: `base/` e a versão atual (`kumo_toon.blend`) continuam intactos.

## 1. Inspeção da arquitetura atual

O Kumo atual é uma **montagem rígida de 63 objetos separados**, que se cruzam sem estar soldados: 13.362 vértices e 13.168 faces.

| Grupo | Objetos | Faces | Tipo de peça | Pode deformar? |
|---|---|---|---|---|
| Cabeça (com crista) | 1 | 40 | Poliedro fechado, 34 triângulos e 6 quads, 25 vértices | **Não.** Não tem loops em volta dos olhos nem da boca, e é quase toda triângulos. |
| Tronco | 1 | 70 | Esfera low poly escalonada | Não. Os membros só a atravessam. |
| Braços / pernas | 4 | 130 | Tubos de 6–7 lados com 4 anéis | Parcialmente. Não há anéis de articulação (cotovelo, joelho) e não estão ligados ao tronco. |
| Mãos | 10 | 232 | Palma icosfera + 3 dedos e polegar em tubos soltos | Não. São peças que se cruzam. |
| Pés | 8 | 304 | Esfera + 3 esferas de dedo | Não. |
| Cauda | 1 | 342 | Tubo de 6 lados, 53 anéis | Sim (é um tubo de quads), mas está solta do corpo. |
| Espinhos dorsais | 7 | 35 | Pirâmides soltas | Não precisam deformar, mas flutuam. |
| Olhos | 16 | 2.144 | Globo + aro + pupila + 2 brilhos + pálpebras planas, por olho | Os globos podem continuar rígidos (giram). As pálpebras precisam fazer parte do rosto. |
| Boca / narinas | 15 | 9.967 | Curvas e decalques projetados, um por expressão | **Não.** Não existe boca na malha. |
| Sobrancelhas | 2 | 40 | Tubos soltos | Não. |

**Consequências para os requisitos:**

1. **Deformação:** com um esqueleto, as peças soltas se separam ou se cruzam nas articulações. Não há loops de articulação, nem pálpebras, nem lábios na malha.
2. **Casca invertida:** cada peça solta geraria a própria casca, e o contorno apareceria em todas as interseções: dedo na palma, braço no tronco, perna no quadril. É exatamente o artefato que o requisito proíbe.
3. **Identidade:** a cabeça aprovada (P1, P2) e as proporções medidas são a referência geométrica a preservar.

**Conclusão:** só a cauda (um tubo de quads) e as medidas aprovadas podem ser aproveitadas. **O corpo, a cabeça e o rosto precisam ser reconstruídos como uma malha única e conectada.** Isso é viável, e a seção 3 explica como.

## 2. Teste de viabilidade técnica (feito em rascunho, fora do repositório)

| Teste | Resultado |
|---|---|
| Casca invertida no **Cycles** (Solidify com offset para fora + normais invertidas + material de contorno que fica transparente nas faces viradas para a câmera) | **Funciona.** Gera o contorno externo e linhas internas nas concavidades (órbitas, boca). |
| Casca invertida no **EEVEE** (backface culling no material) | **Funciona**, depois de instalar a renderização por software (Mesa/EGL) neste ambiente. É lenta (cerca de 17 s por quadro de teste, incluindo a compilação de shaders), mas viável. |
| Toon compatível com tempo real (Shader-to-RGB + ColorRamp) | Só existe no EEVEE, e o EEVEE agora está disponível. |

> **Observação de ambiente:** a instalação do Mesa vale só para esta sessão. Para sessões futuras, posso propor um script de setup do ambiente, que precisa da sua aprovação na hora.

## 3. Arquitetura proposta (versão 2, separada)

### 3.1 Princípio: facetas planas com loops coplanares

A identidade low poly vem de **planos grandes e chapados**. A deformação exige **quads e loops**. Para conciliar as duas coisas:

- **Cada faceta aprovada da cabeça vira um plano subdividido em quads coplanares.** Os loops de olhos, boca e articulações correm *dentro* desses planos. Em repouso, a normal de cada quad é a mesma da faceta original, então o sombreamento chapado e a silhueta não mudam.
- **As bordas entre facetas são marcadas como arestas vivas** (sharp + Edge Split), para o toon continuar recortando os planos. Nada de subdivisão nem de suavização.
- **Ao deformar**, os quads de um plano se dobram juntos. Como o sombreamento é chapado, o resultado continua facetado, como uma dobra de origami, sem virar superfície lisa.

### 3.2 Malha única do corpo (`Kumo_Body`)

Uma malha conectada e simétrica, construída em metade e espelhada:

| Região | Topologia proposta |
|---|---|
| Cabeça / crânio | Caixa facetada de quads que reproduz os planos da cabeça P1. A crista P2 vira um conjunto de faces com material próprio, sem decalque. |
| **Olhos** | 2–3 loops concêntricos por olho, formando uma órbita onde o globo encaixa. As **pálpebras superior e inferior são parte da malha** e fecham por esqueleto ou shape key. |
| **Focinho / boca / mandíbula** | Loop da boca com pelo menos 3 anéis concêntricos (lábio externo, lábio, borda interna), uma cavidade bucal curta e um loop na linha da mandíbula, para abrir. As narinas são duas pequenas reentrâncias na malha. |
| **Pescoço** | Não aparece (a referência não tem pescoço visível), mas recebe 2 loops escondidos sob o queixo para a cabeça poder girar sem rasgar. |
| **Ombros** | Loop de deltoide e transição contínua com o tronco. |
| **Cotovelos / joelhos** | Padrão de 3 anéis em pinça. |
| **Punhos / tornozelos** | 1–2 anéis de transição. |
| **Quadris** | Loop em volta da virilha para afastar as pernas. |
| **Mãos** | Palma de quads com dedos extrudados, sem peças soltas: 3 dedos + polegar opositor, com 2 anéis por articulação de dedo. |
| **Pés** | Planta de quads com 3 dedos frontais extrudados e calcanhar. |
| **Cauda** | Tubo de quads extrudado da base da coluna, **conectado ao corpo**. A espiral passa a ser uma **pose** (rest pose = espiral da referência) controlada por uma cadeia de ossos no futuro. As poses por vista da P9 vão para o rig. |
| **Espinhos dorsais** | Extrudados da própria malha ao longo da coluna. Nenhuma peça solta. |

**Separados por justificativa técnica (permitido pelo item 1):**

- **Globos oculares:** giram sobre o próprio centro, e uma malha soldada não pode rotacionar dentro da órbita. A íris, a pupila e os brilhos ficam em cada globo. A pupila passa a ser um deslocamento de textura/UV ou uma pequena malha filha do globo, sem objeto solto na frente.
- **Língua e interior da boca:** malha separada, escondida, parentada à mandíbula.

**Orçamento:** cerca de 1.500 a 3.000 triângulos no total, dentro da faixa low poly para personagens (500–3.000). Isso elimina os cerca de 11.000 triângulos de decalques atuais.

### 3.3 Contorno por casca invertida (`Kumo_Outline`)

- **Modificador Solidify** na própria `Kumo_Body`, posicionado **depois do Armature** na pilha. Assim o contorno acompanha qualquer deformação do esqueleto ou das shape keys. Offset para fora, normais invertidas e material de contorno no slot extra.
- **Material:** EEVEE com backface culling. Cycles com "Backfacing → transparente". Cor `#5B3A2E`.
- **Espessura ajustável:** propriedade personalizada `outline_thickness` no objeto, ligada por driver ao Solidify, mais um vertex group `outline_weight` para afinar onde convém (borda das pálpebras, lábios, entre os dedos) e evitar linhas internas indesejadas.
- **Espessura constante:**
  - Nas câmeras ortográficas da ficha, uma espessura em unidades de mundo já dá espessura constante na tela.
  - Para câmeras em perspectiva, um driver escala a espessura pela distância até a câmera ativa.
- **Globos oculares:** casca própria, mais fina, para o aro escuro do olho.
- **Tempo real:** a mesma técnica existe em Unity, Unreal e Godot (casca duplicada ou shader de vértice ao longo das normais). O plano documenta os parâmetros para recriar a casca no motor.
- **Freestyle:** sai da renderização principal. Pode continuar disponível como opção desligada, para comparação.

### 3.4 Cel shading

Material toon principal para EEVEE: Shader-to-RGB + ColorRamp em modo constante, com as mesmas 4 faixas e a mesma paleta. Mantenho uma versão equivalente para Cycles, a do método atual, para quando a GPU ou o EEVEE não estiverem disponíveis. As manchas de camuflagem passam a ser **pintadas por face** (atributo de cor por face ou material por face). Assim elas acompanham a deformação e saem iguais em motores de jogo, o que a textura procedural atual não garante.

## 4. Versionamento

| Item | Local |
|---|---|
| Base v1 (congelada) | `kumo-3d-toon/base/`, intocada |
| Versão atual (P1, P2, P8, P9) | `kumo-3d-toon/kumo_toon.blend` e `src/kumo_toon.py`, intocados |
| **Arquitetura v2 (nova)** | `kumo-3d-toon/v2-deformavel/` com `src/` (scripts), `kumo_v2.blend`, `renders/` e `relatorios/` |

Os scripts da v2 são novos e independentes. Ferramentas compartilhadas (`tools/kumo_inspect.py`, `tools/kumo_silhouette.py`) só recebem funções novas, sem mudar o comportamento atual.

## 5. Fases e portões de aprovação

Cada fase termina com renders ortográficos (frente, 3/4, perfil e costas), relatório de topologia, IoU de silhueta contra a referência **e contra a versão atual**, e um checklist Match/Close/Miss. A fase seguinte só começa com a sua aprovação.

| Fase | Entrega | Portão (critério de aceite) |
|---|---|---|
| **F1: cabeça deformável** | Cabeça em quads com os planos da P1, crista P2, órbitas com loops, pálpebras, boca com 3 anéis, mandíbula e narinas | Mesma silhueta da P1 (IoU da cabeça ≥ 0,95 contra a P1 na frente). Quads em todas as regiões que deformam. 0 n-gons, 0 não-manifold. Teste de piscar e de abrir a boca sem colapso. |
| **F2: corpo único** | Tronco + ombros + braços + pernas + quadris conectados à cabeça, com loops de articulação | IoU do corpo ≥ ao da versão atual em todas as vistas. Teste de dobra de cotovelo e joelho (90°) sem pinçamento. |
| **F3: mãos, pés, cauda, espinhos** | Extrusões na mesma malha | 3 dedos + polegar e 3 dedos nos pés. Cauda conectada, com a espiral em repouso. |
| **F4: olhos e expressões** | Globos rígidos com pupila; as 8 expressões refeitas como shape keys | As 8 expressões comparadas lado a lado com as atuais. |
| **F5: contorno por casca invertida** | Solidify + material + driver de espessura + vertex group | Contorno sem artefatos nas 4 vistas e nas expressões. Espessura ajustável. Contorno correto durante os testes de dobra. |
| **F6: material toon EEVEE** | Shader-to-RGB, 4 faixas, manchas por face | Cores da paleta. Comparação com a versão atual. |
| **F7: prontidão para rig** | Escala e rotação aplicadas, origem no chão, simetria verificada, esqueleto de teste (sem rig final) | Relatório de deformação em poses de teste. |

## 6. Riscos e decisões que preciso de você

| # | Risco ou decisão | Recomendação |
|---|---|---|
| R1 | Ao deformar, as facetas dobram e criam novas quebras de plano. | Aceitar como parte do estilo facetado. Concentrar os loops nas bordas de faceta já existentes, para as dobras caírem onde o desenho já tem aresta. |
| R2 | As vistas da referência são inconsistentes entre si (D1, D2). | Manter as decisões P8 e P9 (seguir a referência por vista), agora implementadas como poses do rig. |
| R3 | O EEVEE por software é lento aqui (cerca de 10–20 s por quadro). | Usar Cycles para iterar e EEVEE para validar o resultado de tempo real. |
| **D3** | **Pose de repouso** para o rig. | A pose da referência (braços para baixo, levemente afastados) como rest pose da ficha. Se preferir um A-pose padrão de rig (braços a cerca de 45°), a ficha usa uma pose do esqueleto. |
| **D4** | **Expressões:** shape keys, ossos faciais ou os dois. | Shape keys para pálpebras e boca (fiéis à forma desenhada), mais ossos para mandíbula e globos oculares. |
| **D5** | **Pupila:** malha filha do globo ou textura deslocada por UV. | Malha filha do globo: mantém o recorte nítido e funciona igual no Blender e nos motores. |

**Para começar preciso de:** aprovação do plano (ou ajustes), das decisões D3, D4 e D5, e autorização para iniciar a **F1** em `v2-deformavel/`.
