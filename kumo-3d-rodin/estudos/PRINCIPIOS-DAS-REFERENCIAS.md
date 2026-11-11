# Princípios técnicos das referências de estudo, aplicados ao Kumo

**Data:** 2026-11-11 · **Natureza:** leitura e síntese. Nenhum arquivo do modelo foi alterado. Os PDFs não estão neste repositório (direitos dos autores); os links ficam abaixo.

Regra usada: só entra aqui o que se aplica ao Kumo (personagem cartoon facetado, 3 dedos e polegar, destino Blender e depois glTF/FBX, deformação só por ossos e shape keys). Cada princípio tem fonte, relação com o que já medimos e consequência prática.

## O que foi lido e o que não foi possível ler

| Material | Acesso | O que foi lido de fato |
|---|---|---|
| Villar, *Learning Blender* (amostra Pearson) | PDF oficial de amostra | Sumário, índice remissivo e o capítulo 4 (visão geral do projeto). **A amostra não traz** os capítulos de modelagem da boca, das mãos, de rigging ou de shape keys; deles só tenho os títulos e o índice. |
| Silva, *Do desenvolvimento da modelagem 3D ao rigging de personagem no Blender* (TCC UFMG) | PDF completo | Inteiro. Trata de um robô de superfícies rígidas, então serve sobretudo para organizar o rig. |
| Antunes, *Boas práticas para a construção de rigs para personagens humanoides* (TCC UFMG, 2014) | PDF completo | Inteiro. É o mais útil para o Kumo. |
| Baran e Popović, *Automatic Rigging and Animation of 3D Characters* (MIT, SIGGRAPH 2007) | O link do DSpace não baixa por script (devolve uma página em HTML); usei o artigo de 8 páginas da página do autor no CSAIL do MIT | Seções de esqueleto, anexação de pele e limitações |
| Baran, *Using Rigging and Transfer to Animate 3D Characters* (tese de doutorado, MIT) | O DSpace devolveu HTML e não o PDF | **Não lida.** Fica pendente; se você baixar pelo navegador, eu leio. |
| Blender Studio, *Modeling Guide* | Página pública | Inteira |
| Blender Studio, *Stylized Character Workflow* e *Toon Character Workflow* | Cursos pagos | **Só as páginas públicas** (sumário dos capítulos). Não assisti os vídeos; nada abaixo afirma o que eles ensinam além dos títulos. |

## 1. Pesos de pele: a largura da transição depende da espessura

**Fonte:** Baran e Popović, seção 4. Para evitar dobras, a largura da transição entre dois ossos numa articulação deve ser aproximadamente proporcional à distância da articulação até a superfície, ou seja, ao raio do membro.

**Relação com o que medimos.** É exatamente o que a tentativa 4 encontrou por tentativa e erro:

| Articulação | Raio | Janela de peso | Resultado |
|---|---|---|---|
| Cotovelo | cerca de 0,055 | 0,035 | 6 a 29 cruzamentos a 90° |
| Cotovelo | cerca de 0,055 | 0,12 (cerca de 2× o raio) | 0 a 90° |
| Dedos | cerca de 0,027 | 0,03 (cerca de 1× o raio) | mão fechada sem travessia real |
| Punho | 0,046 | 0,05 (cerca de 1× o raio) | compressão 0,27 a ±45° |

**Teste feito agora para conferir a regra no punho.** Rodei o script da tentativa 4 em pasta temporária, sem gravar nada no projeto, variando só a janela do punho:

| Janela do punho | Proporção do raio | Compressão a +45° | Compressão lateral a 30° | Cruzamentos |
|---|---|---|---|---|
| 0,05 | 1,1× | 0,27 | 0,46 | 0 |
| 0,07 | 1,5× | 0,37 | 0,57 | 0 |
| 0,09 | 2× | **0,48** | **0,66** | 0 |
| (braço atual) | — | 0,62 | 0,65 | 0 |

A regra se confirma: com janela de 2× o raio, o punho iguala o braço atual de lado e chega perto dele a ±45°, sem cruzamentos. A tentativa 4 continua gravada como estava; isso fica como proposta para a próxima iteração.

**Consequência:** adotar como regra de construção do v6 que a janela de peso de cada articulação seja cerca de 2× o raio local, limitada para nunca alcançar a articulação seguinte.

## 2. Pesos automáticos por calor exigem um volume fechado

**Fonte:** Baran e Popović, seção 4. O método de calor, que é o "Pesos automáticos" do Blender, exige que a malha seja a fronteira de um volume conectado, e pesos só por proximidade grudam partes erradas (por exemplo, o tronco no braço).

**Relação com o Kumo.** O modelo atual foi pesado assim: daí os 5.523 vértices com soma de pesos diferente de 1 e as transições largas e irregulares da auditoria. Os pesos procedurais do v6 seguem as propriedades que o artigo pede: suaves, somando 1 e com a largura proporcional da seção 1.

**Consequência:** manter pesos calculados (ou pintados à mão) com verificação automática; usar pesos por calor só como ponto de partida, nunca como resultado final.

## 3. A deformação linear por ossos tem limites conhecidos

**Fonte:** Baran e Popović, seção 1. A deformação linear por ossos (LBS) é a mais usada por ser simples e rápida, apesar das falhas de qualidade conhecidas.

**Relação com o Kumo.** O cotovelo a 130° (antebraço contra o bíceps) é um desses limites. A regra v6 (ossos e shape keys, exportável) aceita esse limite de propósito.

**Consequência:** reforça a sua decisão pendente, com três caminhos:
- limitar a dobra do cotovelo;
- aceitar área e profundidade como critério em dobras extremas;
- tratar 130° depois com ossos ou shapes corretivos.

## 4. A pose de modelagem e de rig deve ser relaxada

**Fontes:** Antunes 2.1; Blender Studio *Modeling Guide*.

- **Antunes:** desaconselha a pose T, porque os ombros ficam encolhidos. Prefere uma pose natural, com as articulações nem muito dobradas nem muito esticadas. Pede também resolução suficiente nas articulações.
- **Blender Studio:** escultura em pose T, com pose de herói opcional.
- As duas fontes divergem quanto à pose T, mas concordam que **testes de deformação** fazem parte da entrega do modelo.

**Relação com o Kumo.** O Kumo já está em pose A. O P1 nasce com 8° de dobra no cotovelo, o que também define o plano do IK (ver a seção 6). **Decisão: manter a pose A**, seguindo o argumento do ombro.

## 5. O esqueleto simula a amplitude do movimento, não a anatomia

**Fonte:** Antunes 2.2, que cita Ritchie, Callery e Biri.

| Princípio | Situação no Kumo | O que fazer |
|---|---|---|
| Ossos centrados nos "tubos" dos membros e dedos, na divisão entre segmentos | ✅ P1 (ossos na linha central dos anéis) | Manter |
| Coluna no **centro** do tronco, não junto às costas, para não comprimir a frente ao curvar | A verificar: o `spine` atual está em y = −0,04 | Medir o centro do tronco na altura de cada osso na etapa P3 |
| Clavícula perto do centro do tronco, um pouco abaixo do ombro | A verificar: o `shoulder.L` atual começa em (0,06; −0,04; 0,80) | Conferir na P3, com o teste de encolher os ombros |
| Osso de **metacarpo** para curvar a palma e fechar a mão de forma expressiva | ❌ O P1 não tem | **Decisão sua:** é osso de deformação estrutural, não corretivo. Proponho um metacarpo para o dedo lateral (dedo 3), testado na mão fechada. |
| Eixo principal = torção; eixo secundário = flexão, igual em toda a cadeia | P1: rolagem alinhada à normal da palma; falta conferir a consistência | Conferir na P3 (o Rigify faz isso ao gerar) |
| Ordem de rotação: eixo de menor amplitude no meio (punho: desvio lateral); torção no eixo interno | O rig atual é só quatérnios e FK | Configurar no rig de controle (P3) |

## 6. Controles do rig

**Fontes:** Antunes 2.3 a 2.8; Silva (estrutura do Rigify).

- **IK do braço e da perna:** o alvo de polo fica **no plano** formado pelos ossos. A dobra inicial (8° no P1) define esse plano e evita que o cotovelo gire ao ligar o IK.
- **Fechar a mão:** controle de 0 a 100 que gira as falanges, com um **offset** (um nível intermediário na hierarquia) para o animador ainda poder ajustar cada falange.
- **Troca IK/FK:** feita com duas cadeias extras dirigindo a cadeia de deformação, com a troca de um quadro para o outro e os controles do modo inativo escondidos.
- **Isolar rotação:** cabeça, braço e quadril podem seguir o tronco ou o controle raiz.
- **Rolamento do pé:** por ações dirigidas (Action constraints no Blender).
- **Camadas:** ossos de deformação (DEF), mecanismo (MCH), organização (ORG) e controle; o animador nunca mexe nos ossos DEF. É a organização do Rigify, usada como modelo por Silva.

**Consequência:** isso confirma a arquitetura R-B (Rigify) da auditoria. O Rigify já entrega IK/FK, polos, alternância de espaço, controle de fechar a mão e rolamento do pé. O P3 deve **gerar e testar** esses controles, não reinventá-los à mão.

## 7. Entrega do modelo e topologia

**Fontes:** Blender Studio *Modeling Guide*; sumários dos cursos *Stylized* e *Toon*.

- **O que se entrega junto com o modelo:**
  - topologia final de quads distribuídos por igual;
  - UV planejada junto com a topologia;
  - shape keys auxiliares: **olhos fechados e boca aberta**;
  - pose de herói;
  - limpeza: transformações aplicadas, malha fechada, nomes e materiais provisórios.
- **Teste antes da topologia final:** o curso *Stylized* faz uma **retopologia rápida para testar expressões antes da retopologia limpa**. É o que o v6 faz com protótipos (P1, P2) antes da reconstrução: o método está alinhado.
- **Cabeça facetada:** no curso *Stylized*, a cabeça e o corpo são esculpidos primeiro em **planos** ("planar head") e só depois suavizados.
  - Para o Kumo, os planos **são** o estilo final da referência. A etapa de suavizar não se aplica.
  - Isso reforça a P4: facetas como arestas vivas e sombreamento plano, não como textura.
- **Boca:** o curso *Stylized* modela a parte interna da cabeça (dentes, gengiva e língua) antes das expressões. O *Toon* faz a boca por **shape keys**.
  - Shape keys viram "morph targets" no glTF, então respeitam a regra v6.
  - Isso apoia o plano para a boca (C3 da auditoria): linha da boca e cavidade na malha, mais shape keys.
- **Cartoon com contorno:** o *Toon* usa sombreamento toon e contorno por faces traseiras, a mesma técnica do contorno já aprovado no Kumo.

## 8. Ordem e pré-produção

**Fontes:** Villar, cap. 4; Antunes 2.1.

- Planejar antes: listar os movimentos que o personagem precisa fazer e buscar referência real dos movimentos (filmar a ação).
- Ordem do livro: olhos → rosto → tronco e braços → pernas → mãos → … → UV → textura → materiais → rig → shape keys faciais → animação.
- No rig, o livro trata **espelhamento** de ossos e pesos e convenções de nomes.

**Relação com o Kumo:**
- **Lista de movimentos:** a auditoria já tem a lista de ações (andar, correr, virar a cabeça, manipular objetos, expressões). Falta transformá-la em **intervalos de ângulo por articulação**. Isso decide, por exemplo, se o cotovelo precisa de 130°.
- **Olhos primeiro:** confirma a ordem prevista (P2 cabeça e olhos antes da reconstrução completa).
- **Espelhamento:** responde ao C1 (só 0,3% de simetria). Modelar e pesar **um lado** e espelhar, como o P1 já faz para o braço esquerdo.

## O que não copiar

- **Pose T:** fica a pose A (seção 4).
- **Detalhe anatômico humano:** 3 metacarpos, 5 dedos e 3 falanges não fazem sentido. O Kumo tem 3 dedos com 2 segmentos e polegar; a regra é cobrir o movimento necessário, não a anatomia (seção 5).
- **Técnicas específicas do Maya** (Connection Editor, utility nodes): no Blender, o equivalente são drivers e constraints.
- **Rig mecânico de peças rígidas** (o TCC de Silva): o Kumo é orgânico, então só a organização em camadas se aplica.
- **Encaixe automático de esqueleto** (Pinocchio): o Kumo já tem o esqueleto posicionado à mão; do artigo, só a regra dos pesos interessa.

## Propostas que saem deste estudo (nenhuma aplicada; todas dependem de você)

1. **P1, próxima rodada:** janela de peso de 2× o raio em todas as articulações. O punho já foi testado (seção 1) e falta aplicar ao cotovelo e aos dedos.
2. **Metacarpo do dedo lateral:** proposta da seção 5, a decidir.
3. **Tabela de amplitudes por articulação**, feita a partir da lista de ações. Ela define o cotovelo a 130° de forma objetiva.
4. **P3 com Rigify:** gerar o rig e conferir o polo no plano, a ordem de rotação, a posição da coluna e da clavícula, e as camadas DEF/MCH/ORG/controle.
5. **Shape keys auxiliares** (olhos fechados, boca aberta) entram na entrega do P2.

## Fontes

- Villar, O. *Learning Blender*, amostra oficial: <https://ptgmedia.pearsoncmg.com/images/9780133886177/samplepages/9780133886177.pdf>
- Silva, T. C. *Do desenvolvimento da modelagem 3D ao rigging de personagem no Blender*, TCC, EBA/UFMG: <https://bibliobelas.eba.ufmg.br/tccs/index.php/caad/article/download/432/439/848>
- Antunes, D. P. *Boas práticas para a construção de rigs para personagens humanoides na técnica 3D digital*, TCC, EBA/UFMG, 2014: <https://bibliobelas.eba.ufmg.br/tccs/index.php/caad/article/download/929/902/1780>
- Baran, I.; Popović, J. *Automatic Rigging and Animation of 3D Characters*, ACM SIGGRAPH 2007: <https://people.csail.mit.edu/ibaran/papers/2007-SIGGRAPH-Pinocchio.pdf> (registro no MIT: <https://dspace.mit.edu/entities/publication/02216671-1424-4552-a2d3-74cec29e2062>)
- Baran, I. *Using Rigging and Transfer to Animate 3D Characters*, tese, MIT, **não lida**: <https://dspace.mit.edu/entities/publication/06388f92-49e8-4237-b291-237b0299391e>
- Blender Studio, *Modeling Guide*: <https://studio.blender.org/tools/artist-guide/asset-creation/modeling>
- Blender Studio, *Stylized Character Workflow* (sumário público): <https://studio.blender.org/training/stylized-character-workflow/>
- Blender Studio, *Toon Character Workflow* (sumário público): <https://studio.blender.org/training/toon-character-workflow/>
