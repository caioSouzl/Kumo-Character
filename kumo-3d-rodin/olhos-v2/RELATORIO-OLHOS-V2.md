# Kumo · olhos-v2: resultados

**Data:** 2026-11-10 · **Estado:** **para avaliação do Caio.** Não está aprovado.

## Suas condições

| Condição | Situação |
|---|---|
| A versão atual (v1) intacta, experiências numa versão nova | ✅ Tudo em `olhos-v2/`; a v1 não foi alterada |
| Não alterar os pesos aprovados do rig | ✅ Nenhum peso foi tocado. O vínculo lê a deformação do rig aprovado através de uma cópia oculta. |
| Não afastar as pálpebras para esconder a penetração | ✅ A folga é a mesma da v1 e é fixa. Não existe mais "guarda" que empurre para fora. |
| Correção só nos objetos das pálpebras, sem sobrescrever a textura da cabeça | ✅ |
| Contorno pintado: solução localizada e reversível | ✅ Só a pálpebra fechada cobre o contorno. Com o olho aberto nada muda, e a reversão é trocar uma imagem no material. |
| Formato e silhueta dos olhos | ✅ Ver a tabela abaixo |
| Geometria da cabeça preservada | ✅ Malha idêntica (hash de vértices e faces) e mesmos modificadores |

## C: terceira abordagem (vínculo à pele deformada)

**Diagnóstico:** em volta dos olhos, a pele mistura os ossos `head` e `neck` (peso de pescoço até 0,05). Quando a cabeça gira, regiões vizinhas da pele se deslocam alguns milímetros umas em relação às outras. Na v1, cada vértice da pálpebra tinha um peso fixo enquanto deslizava sobre pele com pesos diferentes, e por isso desencontrava.

**Solução testada:** os objetos do olho deixaram de ter pesos próprios.
- Em cada quadro, cada vértice acha o ponto da pele em repouso logo abaixo dele e lê para onde o rig levou esse ponto.
- Ele se mantém à mesma altura, na normal já deformada.
- Assim acompanha a deformação local exata, respeitando os pesos aprovados da região facial.
- As pálpebras viraram cascas que copiam pele e globo. A borda percorre essa casca seguindo o arco de rotação em torno do centro do globo, então a curvatura em volta do globo foi preservada.

**Correção no teste da v1:** lá, o teste "cabeça girada" girava o osso no eixo local Z, o que neste rig **inclina** a cabeça em vez de virá-la. Na v2 os testes de virar usam o eixo do pescoço. A inclinação ficou como teste extra.

### Penetração: vértices visíveis dentro da cabeça

Contagem por vértice, com paridade de raios nos triângulos renderizados. Também conta qualquer camada que fique **abaixo do globo**.

| Caso | Passos | Dentro da cabeça | Profundidade máx. |
|---|---|---|---|
| Piscada simultânea, só E, só D (cabeça neutra) | 81 cada | **0** | 0 |
| Semicerrar; piscar olhando para os 4 lados | 42 cada | **0** | 0 |
| Piscada com a cabeça virada **+18° / −18°** | 42 cada | **0** | 0 |
| Piscada com a cabeça virada **+25°** | 81 | **0** | 0 |
| Piscada com a cabeça virada **−25°** | 42 | **0** | 0 |
| Olhar lateral + piscada, cabeça virada ±25° | 42 cada | **0** | 0 |
| Extra: cabeça inclinada 25°; erguida + virada + inclinada | 42 cada | **0** | 0 |

Vértices ocultos dentro da cabeça: 0 em todos os casos. Na v1 eram até 162.

**Única exceção medida:** 3 vértices estáticos (um do brilho E, um do brilho D e um da pupila D) ficam de 0,2 a 0,5 mm "abaixo" do globo. São os mesmos em todos os estados, porque essas camadas não se movem. Na inclinação extra soma-se 1 vértice da íris E. Nas renders não aparece nada.

**Deformação da cabeça:** zero. A diferença máxima da malha avaliada entre estados do olho é 0,0 m.

## Olho aberto (identidade)

| Vista | Diferença média na região dos olhos | Pixels com diferença > 48 | Deslocamento do olho |
|---|---|---|---|
| Frente | 4,5 / 255 | 2,1% | 0,4 px |
| 3/4 | 1,7 | 0,3% | 0,3 px |
| Perfil, olho direito | 4,4 | 1,9% | 0,7 px |
| Perfil, olho esquerdo | 2,9 | 0,9% | 0,2 px |

Distância entre os olhos (frente): 326,0 px no original e 326,6 px na v2. Silhueta do corpo: IoU de 0,99979 a 1,0. Com a cabeça virada (18°, 25° e −25°) a comparação com o original está na prancha `08`.

## Pranchas (`renders/`)

| Arquivo | Conteúdo |
|---|---|
| `01-aberto-comparacao.png` | Olho aberto: original × v2 × diferença |
| `02-fechamento-neutra.png` | Cabeça neutra, piscada 0/25/50/75/100%, quatro vistas |
| `03-foco-50.png` | 50% ampliado |
| `04-piscada-individual.png` | Esquerdo, direito, 50% de cada, semicerrar |
| `05-olhar.png` | Olhar em seis direções |
| `06-virada-18.png`, `06-virada-25.png` | Cabeça virada, piscada 0/25/50/75/100%, quatro vistas |
| `06-virada-menos25.png` | Virada para o outro lado |
| `07-olhar-durante-rotacao.png` | Olhar lateral com a cabeça virada 25° |
| `08-rotacao-original-x-v2.png` | Fidelidade com a cabeça virada |
| `09-palpebra-v1-x-v2.png` | Pálpebra fechada: v1 × v2 (pontos e contorno) |
| `10-piscada-animada.gif` | Pisca enquanto a cabeça vira de 0° a 25° |

## O que ainda vejo e quero que você avalie

1. **Tom da pálpebra fechada.** A pele lisa da pálpebra é um pouco mais escura e mais uniforme que a textura em volta. Na 3/4 e no perfil aparece como uma "mancha" suave no lugar do olho fechado. Dá para clarear ou trazer de volta parte da variação da textura, desde que sem os traços pintados.
2. **Resto de cor no canto interno do olho esquerdo:** pontinhos laranja junto ao canto do lado do nariz, a 75% e 100%, visíveis na frente e no perfil esquerdo. Está na fronteira da área coberta e precisa de mais um ajuste local.
3. **Borda da pálpebra sem espessura.** A borda agora é desenhada na superfície, com a linha de cílio, e não é uma lâmina com volume. No perfil, a pálpebra fechada não forma relevo. É a contrapartida de nunca atravessar a pele.
4. A cópia `Kumo_Olhos_PeleGloboRef` sobrou de um teste e não é usada.

## Decisões pedidas

- **(A)** O vínculo à pele (item C) atende como solução para a rotação da cabeça, sem tocar nos pesos?
- **(B)** A pele lisa e o contorno coberto atendem? Quer que eu ajuste o tom (item 1) e o canto do olho esquerdo (item 2)?
- **(C)** A borda sem espessura (item 3) é aceitável no estilo do Kumo, ou prefere uma pequena aba com volume só na borda? Ela seguiria a mesma lógica de vínculo.
