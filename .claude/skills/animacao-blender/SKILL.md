---
name: animacao-blender
description: Processo de criação, rig e animação 3D estilizada no Blender para o Kumo. Animação (blocking em degraus, poses-chave, intermediários, em 2s com trechos em 1s, correção de câmera, smear); rig (deformadores, mecânicos e controladores, pintura de peso, IK, rig de rosto, boca e língua); criação de personagem a partir de modelo gerado (modelo base, retopologia em loops); modelagem com imagens de frente e de lado cruzadas; olhos estilizados (pupila 2D por decal presa a ossos, íris que afunda para dentro). Use ao criar ou revisar animação, rig ou modelo 3D do Kumo ou de outro personagem do projeto, e ao exportar para o jogo. Também o básico do Blender (modelagem, modificadores, materiais por nós, pintura de textura, Geometry Nodes, animação no Graph Editor, compositor e render).
---

# Animação 3D estilizada no Blender (Kumo)

Fonte do processo: vídeo "my full animation process" de @no_the_robot (TikTok, 7 min 37 s), transcrito e estudado em 17/11. As regras do projeto ficam no fim.

## As etapas, nesta ordem

### 1. Blocking (poses em degraus)
- Poucas poses que contam a ação inteira. Num salto: sai do chão, ponto mais alto, pousa, fica de pé.
- Trabalhe em **degraus**: a pose segura até a próxima chave, sem o computador interpolar. No Blender: Graph Editor → clique direito nas chaves → Interpolation Mode → **Constant**. Por script: `em_2s.degraus(acao)`.
- Motivo: você vê as poses de verdade antes de qualquer interpolação. Para o visual "em 2s", é preciso "lutar contra o computador": nada de interpolação suave automática.

### 2. Poses-chave
- As mesmas poses do blocking, agora fortes: **silhueta clara** e **pose assimétrica**.
- Teste da silhueta: a pose precisa ser legível mesmo toda preta. Um braço na frente do corpo some; desloque-o para fora do contorno.
- Em movimento rápido, a clareza vale mais que o detalhe. Exemplo: braços junto ao corpo na saída e abertos no ponto mais alto, para ler "ele se lançou".

### 3. Intermediários (in-betweens)
- Continue em degraus, com uma pose nova **a cada 2 quadros**.
- **Subdivida**, não vá em linha reta: com chaves em 1 e 9, faça primeiro a 5 (o meio), depois a 7, depois a 3. Ir 1 → 3 → 5 → 7 tentando acertar a 9 é mais difícil.
- **Confira os arcos** com Motion Paths no quadril (o centro de gravidade): Object Properties → Motion Paths → intervalo → Calculate. Por script: `em_2s.trajetoria(rig, 'hips', ini, fim)`. Cada intermediário novo muda o arco; ele precisa ficar uma curva limpa.

### 4. "Push pass" (tempo)
- O espaçamento já está certo; agora se ajusta o **tempo**.
- Para destacar um movimento muito rápido, esse trecho passa a ser animado **em 1s** (pose em todo quadro), no meio da animação em 2s. O contraste é o que chama atenção.
- No Blender: cursor de tempo no quadro de destino, tecla S e escalar as chaves no eixo X, para aproximá-las. Por script: `em_2s.em_2s(acao, ini, fim, em_1s=[(a, b)])`.
- Onde usar: saída de um salto, um giro, um floreio no pouso, um golpe. Esses pontos se descobrem animando; não precisam estar planejados.

### 5. Câmera em movimento ("camera hold")
- Em 2s com a câmera se movendo, a pose fica parada no quadro repetido, mas **escorrega na tela**. A animação treme; é algo que se sente mais do que se vê.
- Correção: no quadro repetido, mover a raiz para o personagem ficar **no mesmo ponto da tela** em que estava no quadro da pose. Vale principalmente nos quadros em que a câmera mais se move (subida e pouso).
- O autor faz isso à mão, marcando o ponto na tela com o dedo, e pede no vídeo um jeito melhor. O projeto tem um jeito exato: `em_2s.segurar_na_camera(cena, rig, 'hips', cam, ini, fim, em_1s=[...])`. No teste, o escorregão caiu de 0,024 da largura da tela para 0.

### 6. Acabamento (polish)
- Movimento secundário: cabeça, mãos, cauda, detalhes.
- **Smear / linha de ação**: nos quadros em 1s, um traço desenhado (Grease Pencil) que leva o olho de uma pose à outra. Substitui o desfoque de movimento.
- Fazer **só no fim**: quem mexe na animação depois teria de refazer os smears.

### 7. Depois da animação
Luz, render e som.

## Rig e criação de personagem
Para rig (camadas de ossos, pintura de peso, IK, rosto, boca, língua) e para criar um personagem a partir de um modelo gerado, leia `referencias/rig-e-personagem.md`. Cada parte diz o que o Kumo já tem e o que vale trazer.

Para **modelar a partir de uma imagem de frente e uma de lado** e para **olhos estilizados** (pupila por decal com rig, íris para dentro), leia `referencias/modelagem-e-olhos.md`. Fontes: um vídeo do Caio (@dreamstudio32) e dois do TikTok (@pol.gc e @mokunachoi).

Três regras de lá que valem sempre:
- **Frente e lado bastam:** com as duas imagens cruzadas atrás do modelo, a frente dá largura e altura e o lado dá profundidade. Modele em ortográfica com raio X (`Alt+Z`), alternando as duas vistas.
- **Pivô do olho por dentro:** um osso que gira no próprio olho não move a pupila. A base fica no centro da esfera do olho (ou do rosto), e a ponta na superfície.
- **Íris para dentro:** normais invertidas na íris e Backface Culling. Funciona no EEVEE e no Godot, mas não no Cycles.

Para o **básico do Blender** (modelagem, modificadores, materiais por nós, pintura de textura, Geometry Nodes, Graph Editor, compositor e render), leia `referencias/curso-basico.md`. Fonte: a playlist do Caio, estudada em 26/11.

Duas regras de lá que valem sempre:
- **Escala aplicada:** escala diferente de 1 faz modificadores, Geometry Nodes e exportação errarem. Aplique com `Ctrl+A` → Scale.
- **Loop perfeito:** a primeira e a última chave precisam do mesmo valor e da mesma inclinação.

Três regras de rig que valem sempre:
- **Pesos são relativos:** um osso com peso baixo sozinho move o vértice por inteiro. Defeito de deformação quase sempre é outro osso puxando junto.
- **Só deformadores e shape keys vão para o jogo:** constraints, bendy bones e spline IK precisam ser assados antes de exportar.
- **Pé no chão pede IK:** andar, correr e pular sem IK nos pés faz o pé escorregar.

## Ferramentas (`scripts/em_2s.py`)
Testadas no Blender 5.2 com a ação `Lingua_Lancar` do Kumo:

| Função | O que faz |
|---|---|
| `degraus(acao)` | Todas as chaves viram Constant |
| `em_2s(acao, ini, fim, em_1s=[(a, b)])` | Refaz as chaves: pose a cada 2 quadros, e a cada quadro nos trechos `em_1s` |
| `segurar_na_camera(cena, rig, osso, cam, ini, fim, em_1s)` | Corrige o tremor da câmera em movimento (chaves na posição do objeto do rig) |
| `trajetoria(rig, osso, ini, fim)` | Liga o Motion Path do osso |
| `curvas(acao)` | Lista as fcurves; o Blender 4.4+ guarda as curvas em camadas e slots |

Para modelagem e olhos (testadas no Blender 5.2.3, `scripts/testes/teste_olhos.py`):

| Função | O que faz |
|---|---|
| `referencias_cruzadas.montar(frente, lado, altura)` | Põe as imagens de frente e de lado em planos cruzados, cada uma visível só na sua vista |
| `referencias_cruzadas.conferir(f, s)` | Diferença dos pés e do topo entre as duas imagens, em metros |
| `olhos.decal(obj, nome, imagem, centro, tamanho)` | Empty e material da pupila 2D projetada |
| `olhos.faces_no_raio` / `olhos.atribuir_faces` | Escolhe as faces do olho e põe nelas o material |
| `olhos.rig_olhar(rig, olhos, foco, profundidade)` | Ossos dos olhos com Damped Track num alvo, com os Empties presos |
| `olhos.iris_para_dentro(globo, grupo)` | Inverte as normais da íris e liga o Backface Culling |

`em_2s` muda as chaves da ação. Trabalhe numa **cópia** da ação (`acao.copy()`) e guarde a original suave.

## Regras do projeto Kumo
- **Aparência:** nenhuma animação muda a aparência do Kumo parado. Os arquivos oficiais não são alterados (`kumo-3d-rodin/auditoria/hashes-antes.sha256`).
- **Modelo atual:** `kumo-3d-rodin/v6-dev/boca/kumo_v6_boca.blend` (olhos, mãos, ombros, boca e língua).
- **Ombro:** depois de animar os braços, rode `kumo-3d-rodin/v6-dev/ombros/ferramentas/ombro_automatico.py`.
- **Cabeça grande, braços curtos:**
  - a cabeça chega atrasada e o tronco compensa o peso;
  - gestos ficam ao lado ou à frente do corpo, nunca atravessando a cabeça;
  - braço erguido acima de ~120° some atrás da cabeça na vista de frente.
- **Olhos:** piscada normal de 2 quadros fechando, 1 fechado e 3 abrindo; os olhos se movem 2 quadros antes da cabeça. Regras e conferidor em `animacao-2d/src/planilha.py` e `estudos-animacao/02-TEMPO.md`.
- **Língua:** mira, dispara em 2 quadros e volta em 12 (`kumo-3d-rodin/v6-dev/boca/RELATORIO.md`).
- **Jogo (Godot):**
  - Só ossos e shape keys; no máximo 4 ossos por vértice.
  - Exportação conferida por reimportação (`boca/src/exportar_boca.py`).
  - Uma animação em degraus exporta como chaves em degraus. Confira no Godot se a interpolação da faixa está em "Nearest", para manter o visual em 2s.
- **Conferência visual:** renderize uma tira de quadros e olhe antes de dizer que ficou pronto; a aprovação final é do Caio.
