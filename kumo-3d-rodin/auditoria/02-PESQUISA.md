# Kumo 3D — pesquisa técnica externa

**Data:** 2026-11-11 · **Método:** busca na web com prioridade para documentação oficial do Blender, Blender Studio e discussões técnicas reproduzíveis. Cada item traz a fonte, o método, vantagens, limitações e a decisão para o Kumo.

**Sobre a confiabilidade:**
- Páginas oficiais (docs.blender.org, developer.blender.org, studio.blender.org) são a base.
- Fóruns e blogs entram só como apoio.
- Várias aulas do Blender Studio são pagas: li títulos e resumos, não o conteúdo completo.
- Onde não achei fonte verificável, digo isso.

## 1. Sistema ocular

### 1.1 Ossos de pálpebra girando em torno do centro do olho (Blender Studio)

- **Fonte:** curso *Facial Rigging* do Blender Studio, capítulo "Eyes": [eyelids deformation bones](https://studio.blender.org/training/facial-rigging/eyelids-deformation-bones/), [eyelids local controls](https://studio.blender.org/training/facial-rigging/eyelids-local-controls/), [capítulo de olhos](https://studio.blender.org/training/facial-rigging/chapter/eyes/). O curso exige Blender 5.0 ou mais novo.
- **Método:**
  - Uma malha em fita (*eyelid ribbon mesh*) define a borda da pálpebra.
  - Ossos de mecanismo partem do centro do olho e apontam (Damped Track) para controles na borda.
  - Ossos de deformação seguem esses ossos.
  - O curso inclui piscada automática e pálpebra que acompanha o olhar.
- **Observação do próprio curso:** ossos que só esticam não mantêm a deformação esférica e causam interseção em globos esféricos. Para olhos não esféricos, a montagem com esticamento pode servir.
- **Vantagens:** é o padrão de produção; a pálpebra é geometria real da cabeça e se deforma junto com a pele; exporta como ossos.
- **Limitações:** exige anéis de arestas concêntricos em volta do olho, que a malha atual não tem.
- **Decisão:** **adotar como alvo** na malha nova. Como os olhos do Kumo são ovais e rasos, e não esféricos, o arco precisa seguir a superfície do olho, não uma esfera.

### 1.2 Rigify `face.skin_eye` e cadeias `skin.*`

- **Fonte:** manual do Blender, [Rigify › Face](https://docs.blender.org/manual/en/dev/addons/rigging/rigify/rig_types/face.html) e [Rigify › Skin](https://docs.blender.org/manual/en/latest/addons/rigging/rigify/rig_types/skin.html); discussão de projeto em [T89808](https://developer.blender.org/T89808).
- **Método:**
  - `face.skin_eye` é o controlador pai das pálpebras e da rotação do olho.
  - Ele exige duas cadeias filhas (superior `.T` e inferior `.B`).
  - As cadeias são montadas para seguir a superfície do olho e torcer conforme a normal dela.
  - Tem opções de destacar a pálpebra e de quanto ela acompanha o olho em X e Z.
- **Vantagens:** oficial, documentado e presente no Blender 5.2.3 instalado (Rigify 0.6.10).
- **Limitações:** pressupõe globo aproximadamente esférico e topologia de pálpebra em anéis; a geração em modo sem interface precisa ser testada.
- **Decisão:** **candidato principal** para as pálpebras da malha nova, a validar em protótipo.

### 1.3 Olhos não esféricos com Lattice

- **Fonte:** BlenRig no Blender Studio ([treinamento](https://studio.blender.org/training/blenrig/57180cf0c379cf04929a408a), [repositório arquivado](https://projects.blender.org/archive/blenrig/src/commit/bdbf5669d586ab7f5a36c2d7b492e53897ffaa16)); página de rigging do [Sprite Fright](https://studio.blender.org/projects/sprite-fright/rigging/), que lista "Eye scaling" e "Preventing teeth clipping with Shrinkwrap".
- **Método:** o globo é uma esfera real que gira; um Lattice deforma globo e pálpebras juntos para a forma estilizada (oval, achatada).
- **Vantagens:** a rotação é matematicamente limpa e o achatamento vem depois.
- **Limitações:** o Lattice não exporta para motores de jogo; é mais uma camada de deformação.
- **Decisão:** alternativa de reserva se a projeção de íris (1.5) não bastar.

### 1.4 Pálpebras por Geometry Nodes

- **Fonte:** [BlenderNation, "Geometry Node Eyelids for Stylized Cartoon Eyes"](https://www.blendernation.com/2023/02/07/geometry-node-eyelids-for-stylized-cartoon-eyes-in-blender/); produto comercial [Simple Toon Eyes](https://blendermarket.com/products/simple-toon-eyes-w-geometry-node-eyelids/docs).
- **Método:** pálpebras geradas por nós sobre o olho, sem Lattice nem shape keys.
- **Vantagens:** paramétrico e rápido de ajustar.
- **Limitações:** não exporta; depende de versão de nós. É a mesma família do que fizemos nas v2–v5, com os mesmos custos (ver Diagnóstico, A4).
- **Decisão:** **não adotar** na cadeia de deformação definitiva.

### 1.5 Íris e pupila como textura ou projeção ("olho 2D")

- **Fonte:** **não encontrei** fonte oficial verificável nesta pesquisa. As buscas sobre Guilty Gear, Wind Waker e Breath of the Wild não retornaram documentação sobre olhos.
- **Evidência própria:** nas versões v1 a v5 a íris, a pupila e o brilho são projeções que seguem o osso do olho, com **zero penetração em todos os testes** e o olho aberto reproduzido com diferença média abaixo de 5/255.
- **Decisão:** **manter o princípio**, que já está validado no nosso projeto, simplificado para uma superfície e um material por olho em vez de quatro cascas.

## 2. Topologia e retopologia

### 2.1 Anéis de arestas em articulações

- **Fonte:** wiki do Polycount, [Limb Topology](http://wiki.polycount.com/wiki/Limb_Topology), citada em [Low poly characters and edge loops](https://polycount.com/discussion/102765/low-poly-characters-and-edge-loops) e [Low Polygon Joints](https://polycount.com/discussion/61079/low-polygon-joints-what-is-the-best-way). A busca retornou as discussões que apontam para a página, não o texto da página.
- **Método:**
  - Três anéis por articulação (tutorial de Ben Mathis): um no eixo e um de cada lado, pesados quase 100% em cada osso.
  - Anéis em ângulo quando o eixo está no centro.
  - Dois anéis por articulação de dedo.
  - Posição do osso e pesos importam tanto quanto os anéis.
- **Decisão:** **adotar** como regra de construção e como critério de teste de cotovelos, joelhos, ombros, punhos e dedos.

### 2.2 Limites da retopologia automática

- **Fonte:** discussões de desenvolvimento do Blender sobre o QuadriFlow ([feedback](https://devtalk.blender.org/t/quadriflow-feedback/9605), [melhorias](https://devtalk.blender.org/t/quadriflow-improvements/10616)); [CG-Wire, "Why Retopology Matters for Animation Pipelines"](https://blog.cg-wire.com/retopology-animation-blender-guide).
- **Achado:** remalhadores automáticos seguem a curvatura, produzem espirais e quebram anéis. O QuadriFlow evita polos às custas do fluxo de arestas. A prática corrente é usar o resultado automático como base e refazer à mão articulações e rosto.
- **Limitação:** são fontes de fórum e blog, e em parte antigas.
- **Decisão:** confirma o diagnóstico. A base atual serve como **autoridade de forma**, não como malha de animação.

## 3. Skinning e deformação

| Tema | Fonte | O que diz | Decisão para o Kumo |
|---|---|---|---|
| Preservar volume | [Manual: Armature Modifier](https://docs.blender.org/manual/en/4.2/modeling/modifiers/deform/armature.html) | Usa quatérnios para a malha não encolher nas articulações; tem descontinuidade a 180° | Testar por região no protótipo (hoje está desligado) |
| Suavização corretiva | [Manual: Smooth Corrective](https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/corrective_smooth.html) | Reduz distorções suavizando a deformação; aceita grupo de vértices; "Bind Coordinates" é exigido se houver modificadores construtivos antes | Opcional, só para render no Blender (não exporta) |
| Surface Deform | [Manual: Surface Deform](https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/surface_deform.html) | Vincula uma malha à superfície de outra; o alvo não pode ter faces côncavas nem vértices sobrepostos; quanto mais longe do alvo, mais artefatos | Não usar para as pálpebras (o vínculo fica velho quando a pálpebra desliza). Serve para acessórios fixos. |
| Limite de influências | [Tutorial Vulkan: Blender workflow](https://docs.vulkan.org/tutorial/latest/Advanced_glTF/Tooling_Production_Pipeline/02_blender_workflow.html); [relato UE](https://forums.unrealengine.com/t/interchange-gltf-importer-truncates-skeletal-mesh-bone-influences-to-4-per-vertex/2745391) | Pesos não normalizados fazem os vértices encolher ou inflar; "Limit Total = 4" e renormalizar antes de exportar; a Unreal descarta influências além de 4 | **Adotar:** máximo de 4 e soma 1, verificados por teste automático |

## 4. Sombreamento facetado e estilo toon

- **Fonte:** manual 5.2, [Smooth By Angle](https://docs.blender.org/manual/en/latest/modeling/modifiers/normals/smooth_by_angle.html) e [Shading](https://docs.blender.org/manual/en/latest/scene_layout/object/editing/shading.html); [notas da versão 4.1](https://developer.blender.org/docs/release_notes/4.1/modeling/).
- **Método:** desde a 4.1 o "Auto Smooth" virou um modificador/grupo de nós que marca arestas vivas pelo ângulo. Arestas vivas também podem ser marcadas à mão (atributo `sharp_edge`).
- **Decisão:** marcar **arestas vivas explícitas** nas fronteiras das facetas, de forma determinística, em vez de depender de ângulo. O ângulo muda quando a malha deforma, e a faceta "pisca".
- **Estilo toon, como apoio:** apresentação da Arc System Works sobre o [controle de linha do Guilty Gear](https://docswell.com/s/ASW_Academy/5LVY67-GG-Toonline-Eng) e [PDF de Junya Motomura](https://www.ggxrd.com/Motomura_Junya_GuiltyGearXrd.pdf). Usam *inverted hull* com espessura controlada por cor de vértice e normais editadas para controlar a sombra. Valida o nosso contorno e sugere controlar a espessura por cor de vértice.

## 5. Rig de produção

- **Rigify:** oficial, embutido no Blender. Metarig → rig gerado com IK/FK, controles e formas ([manual](https://docs.blender.org/manual/en/4.2/addons/rigging/rigify/rig_features.html)). Confirmado na instalação.
- **CloudRig:** ferramenta do Blender Studio, extensão do Rigify ([introdução](https://studio.blender.org/tools/addons/cloudrig/introduction), [tipos de componente](https://studio.blender.org/tools/addons/cloudrig/cloudrig-types), [pipeline de rigging](https://studio.blender.org/tools/pipeline-overview/asset-creation/rigging)). O rig de controle é regenerável a partir do metarig. Precisa ser instalado à parte.
- **Decisão:** **Rigify** para o corpo, por ser embutido, documentado e sem dependência externa. O CloudRig fica como evolução possível.

## 6. Compatibilidade com o Blender 5.2 (verificada na instalação)

| Item | Verificação | Resultado |
|---|---|---|
| API de propriedades (5.0) | [Notas da 5.0, Python API](https://developer.blender.org/docs/release_notes/5.0/python_api/) | Propriedades de `bpy.props` não ficam mais acessíveis como dicionário |
| Entradas de modificador de nós | Teste direto | `modifier["Socket_N"] = valor` **não funciona** na 5.2. O valor fica em `modifier.properties.inputs.Socket_N.value`. Usamos driver num nó de valor dentro do grupo. |
| Imagens EXR | Teste direto | Gravar e reler EXR pelo módulo `bpy` devolveu zeros. Usamos PNG de 16 bits. |
| Existência de operadores | Teste direto | `hasattr(bpy.ops.x, "y")` é **sempre verdadeiro**. O teste correto é `bpy.ops.x.y.get_rna_type()`. |
| Triangulação | [API: MeshLoopTriangle](https://docs.blender.org/api/current/bpy.types.MeshLoopTriangle.html), [BVHTree](https://docs.blender.org/api/current/mathutils.bvhtree.html) | `BVHTree.FromPolygons` triangula quads de forma diferente do render; usar `loop_triangles` (lição da v1 e v3) |
| Rigify | Teste direto | Módulo 0.6.10, operadores de metarig e geração registrados; a ativação pelo `addon_utils` emite um erro de preferências no modo sem interface (a investigar no protótipo) |
| Modificadores e operadores citados na arquitetura | Teste direto | Todos presentes (lista no Inventário, seção 6) |

## 7. Lacunas da pesquisa

- Não li o conteúdo pago das aulas do Blender Studio, só títulos e resumos.
- Não encontrei documentação pública verificável sobre olhos por textura em jogos estilizados.
- Não obtive o texto da wiki do Polycount, só as discussões que a citam.
- Não pesquisei anatomia real de camaleão, porque o Kumo é um design estilizado e a referência é a autoridade.
