# Estudos de animação do Kumo · 01 · pesquisa (2026-11-12)

**Regra do Caio:** usar a referência com fidelidade e **não mudar nada no visual do Kumo**, no 3D nem no 2D.

## Olhos 3D exportáveis

| Fonte | O que diz | Uso no Kumo |
|---|---|---|
| [Vulkan glTF: morph targets](https://docs.vulkan.org/tutorial/latest/Advanced_glTF/Morph_Targets_Facial_Animation/01_introduction.html), [ingestão de shape keys](https://docs.vulkan.org/tutorial/latest/Advanced_glTF/Morph_Targets_Facial_Animation/02_shape_key_ingestion.html) | Morph targets são deslocamentos por vértice; o Blender grava os nomes em `extras.targetNames` | Piscada e olhar vão como shape keys, que exportam para qualquer motor |
| [Tuts+ Kila: rig com blend shapes](https://design.tutsplus.com/articles/game-character-creation-series-kila-chapter-8-rigging-with-blend-shapes--cg-32643) | Para piscar, faz uma cópia da cabeça neutra com o olho fechado | O mesmo princípio, mas só nas pálpebras |
| [Ready Player Me: animações faciais](https://docs.readyplayer.me/ready-player-me/integration-guides/unity/setup-for-xr-beta/facial-animations), [Convai: piscada](https://docs.convai.com/api-docs/plugins-and-integrations/unity-plugin/scripts-overview/convaiblinkinghandler) | Piscada = peso do morph sobe de 0 a 1 e volta; olho esquerdo e direito separados | `Piscar.L` e `Piscar.R` |
| [Unreal: rig de olhos](https://forums.unrealengine.com/t/eye-rigging-animation/52916) | Em jogos mobile, olhos costumam ser textura, e a piscada é uma sequência de quadros | Os olhos do Kumo são pintados na textura (como na v5); a solução tem que manter essa pintura |
| [abratabia: animação facial](https://abratabia.com/ai-talking-characters/facial-animation.php) (blog, conferir) | Cada sistema (piscar, olhar, boca) escreve só nas suas formas | Formas separadas para piscar e para olhar |

**Lacuna:** não achei material sobre formas intermediárias de piscada ou sobre decalques de olho. A solução será desenhada e medida aqui:
- piscada por formas intermediárias que seguem a superfície da pele;
- olhar por decalque da pupila, com a íris de base limpa.

## Ombros (braço erguido)

| Fonte | O que diz |
|---|---|
| [BlenderArtists: corretivas de ombro e coxa](https://blenderartists.org/t/any-info-on-how-corrective-shape-keys-are-done-for-shoulders-or-thighs/1412695), [ombro afundando](https://blenderartists.org/t/how-do-you-fix-a-shoulder-caving-in-on-itself/1381101) | O braço sozinho não passa de ~90°; acima disso quem gira é o ombro. Antes de criar formas, corrija os pesos (a influência do braço vai longe demais nas costas) |
| [Packt: corretivas](https://subscription.packtpub.com/book/game-development/9781849513203/1/ch01lvl1sec11/using-corrective-shape-keys) | Posar → criar a shape key → corrigir → driver na rotação do osso |
| [80.lv: ombro automático](https://80.lv/articles/check-out-this-automatic-shoulder-rig-set-up-with-blender), [Blender Studio: humano realista](https://studio.blender.org/training/realistic-human-research/chapter/clothing-shapes-rotation) | Ombro automático: a clavícula acompanha parte do giro do braço; as corretivas ficam só para o refinamento |
| — | **Motores de jogo não importam drivers.** A lógica é refeita no motor ou a pose fica gravada na animação (como já fazemos com a mão fechada) |

**Plano:**
1. Pesos do ombro primeiro.
2. Ombro que acompanha o braço (a clavícula/`shoulder` gira uma parte).
3. Corretivas ligadas ao giro do braço.

Tudo isso sem mudar o repouso.

## 2D por recorte (cutout)

| Fonte | O que diz |
|---|---|
| [Spine: como recortar a arte para animar](https://en.esotericsoftware.com/blog/How-to-cut-your-assets-for-animation) | **Desenhar as partes escondidas** de cada peça; cada parte móvel numa camada |
| [Live2D: preparação da ilustração](https://docs.live2d.com/en/cubism-editor-tutorials/psd/) | Separar o mínimo de partes necessárias para o movimento |
| [See-through (artigo)](https://www.emergentmind.com/papers/2602.03749), [teste do see-through](https://lilting.ch/en/articles/see-through-anime-layer-decomposition) | Decomposição automática em camadas com as partes escondidas completadas ("amodal completion"). É treinado em anime; o Kumo não é anime, então não confio para manter o visual |

**Plano:**
1. Recortar a arte da referência à mão (por script), peça por peça.
2. Completar só as áreas escondidas, com a cor e o traço vizinhos.
3. Conferir que a montagem em repouso fica **idêntica pixel a pixel** à arte original. Esse é o teste que prova que nada mudou.
