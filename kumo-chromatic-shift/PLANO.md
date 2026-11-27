# Kumo: Chromatic Shift (protótipo da cabeça)

Status: **fase 2 (corpo inteiro) em protótipo, com as decisões do Caio aplicadas.** Nenhum arquivo de produção foi
alterado. Os scripts abrem o `kumo_v8_movimento.blend` e trabalham numa cópia em memória;
renders e o .blend de teste ficam nesta pasta.

## 1. Inspeção (o que o Kumo v8 tem hoje)

| Item | Achado | Consequência para o efeito |
|---|---|---|
| Pele | 1 material (`Kumo_Quad_Toon`): textura 2048² → Emission. Sem luz | A cor nova entra no lugar da textura; a finalização 2.5D dá a luz |
| Regiões de cor | Todas na mesma textura: verde (matiz ~120°), manchas verde-amareladas (~60–90°), barriga bege (pouca saturação) | Regiões separadas pela cor do pixel, sem pintar máscaras novas |
| Malha | 6 733 vértices, 6 668 faces, 94% suavizadas, uma peça só | Uma "faceta" visível é um grupo de faces quase planas, não uma face |
| Olhos | Objetos à parte: Globo, Íris, Aro, Anel (a pele verde em volta), Pálpebras, Tampa | Anel, Aro e Pálpebras precisam seguir a onda junto com a pele |
| Ossos | `head`, `jaw`, `neck`, `tail_01…26` como grupos de vértices | Região do protótipo = `head + jaw` |
| Contorno | Solidify invertido (`Kumo_Outline`) + objeto `Kumo_Contorno` | Intocado; continua estável durante a troca |

## 2. Como o protótipo funciona

Um parâmetro anima tudo: **`cs_progress`** (0 → 1), uma propriedade no objeto `Kumo`.
Mais dois auxiliares: `cs_activation` (olhos + faíscas na crista) e `cs_afterglow`
(faíscas residuais).

**Atributos gravados na malha (uma vez, na pose de repouso):**

- `cs_dist`: distância **pela superfície** (geodésica) a partir da testa. A onda
  contorna o focinho e desce pela espiral da cauda porque mede ao longo da malha,
  não em linha reta.
- `cs_facet_t`: quando a onda chega em cada faceta visual. A malha foi agrupada em
  **799 facetas** (faces vizinhas com até 22° de diferença entre si), média de 8
  faces cada. A faceta vira de cor inteira, como uma peça.
- `cs_facet_rand`: um número por faceta, para o pequeno atraso próprio (Facet Pulse) e
  para escolher quais facetas soltam faísca.

Como são atributos da malha, eles acompanham o rig: a onda fica estável em
qualquer animação (caminhada, corrida, pulo).

**Node group `KumoChromaticShift`** (entra a textura, sai a cor nova + o brilho):

| Zona | O que acontece |
|---|---|
| Ainda não alcançada | Textura original |
| Frente da onda | Faixa ciano fina, contínua, seguindo a superfície |
| Transição | Cada faceta vira com reflexo violeta e brilha no instante da virada |
| Transformada | Paleta nova; manchas viram o tom de destaque; barriga vira o tom de barriga |

**Proteção de cor:** só a família verde/amarela e a barriga mudam. O laranja do olho,
o vermelho da boca e o resto ficam como estão.

**Paletas** (escuro, médio, destaque, barriga), trocadas sem refazer material:
cibernético, vulcânico, fantasma, cristal. Qualquer cor pode ser editada no grupo.

**Renders:** `renders/cabeca_cibernetico.mp4` (2,5 s), `renders/sequencia.jpg`,
`renders/paletas.jpg` (meio e fim das 4 paletas), `renders/ruido_de_borda.jpg`.

## 2b. O que veio do tutorial de transição de cor (@genzanimates)

A técnica dele: dois materiais num Mix Shader; a máscara é um gradiente nas
coordenadas de um **Empty**, com **ruído misturado** antes de um ColorRamp de corte
seco, e uma **linha brilhante** na fronteira. Mover o Empty move a transição.

O que entrou no Kumo:

- **`Edge Noise`** (padrão 0.08): ruído gravado na pose de repouso empurra a frente
  da onda, deixando a faixa de energia irregular e elétrica. Fica estável quando o
  Kumo se mexe (no tutorial o ruído "escorrega" se o objeto deforma).
- **Origem por Empty:** `bake_attributes(origin=objeto)` faz a onda nascer no ponto
  da pele mais perto do Empty: a cor pode começar na mão que toca um produto, no pé
  que pisa numa plataforma etc. A distância continua sendo medida pela superfície.

O que **não** entrou: a máscara em linha reta pelo espaço (a nossa segue a superfície)
e a troca de material inteiro (a nossa troca só a cor e mantém a finalização toon).

## 3. Ajustes que o protótipo pediu

1. **Pálpebras e o anel verde em volta do olho** são objetos separados. Eles herdam a
   onda da face de pele mais próxima (`bake_followers`).
2. **Íris laranja** ficava ciano no remapeamento; a proteção por matiz resolveu.
3. **Queixo**: o peso dele é dividido entre `head` e `jaw`; a região usa a soma.

## 4. Plano para o corpo inteiro (fase 2, depois da sua aprovação)

1. `bake_attributes(region="body")`: a mesma onda, da testa até a ponta da cauda
   (a espiral sai sozinha da distância pela superfície).
2. Tempo: ativação 0,4 s → cabeça 0,6 s → tronco e braços 0,6 s → pernas e cauda
   0,6 s ≈ **2,2 s**, dentro da faixa de 1,5–2,5 s.
3. Teste com Caminhar, Correr e Pular para confirmar a estabilidade.
4. **Onde instalar.** Recomendo **não** mexer no `kumo_v8_movimento.blend`: criar um
   arquivo de vídeo que puxa o Kumo por link e recebe o efeito. Os atributos e o node
   group ficam só nele. A alternativa (gravar no arquivo de produção) também é não
   destrutiva, mas mistura o rig do jogo com coisas de vídeo.
5. Jogo (Godot): o efeito é de render no Blender. Levar para o jogo é um port de
   shader à parte (os atributos exportam como cor de vértice / UV extra).

## 5. Decisões do Caio (27/11)

1. **Barriga não muda.** `Belly Shift` = 0: a barriga fica bege e não recebe nem o
   reflexo violeta nem a faixa de energia.
2. **Íris e aro laranja mudam de cor.** `Eye Mode` = 1 nos materiais do olho: o laranja
   vira o tom da paleta; pupila preta e branco ficam. Íris e aro de cada olho viram
   juntos, no tempo do anel do mesmo olho (senão a faixa riscava o olho e um olho
   mudava antes do outro).
3. **Facetas piscando bastam** como faíscas residuais (sem partículas).

## 6. Fase 2: corpo inteiro (protótipo, ainda fora da produção)

- `--region body`: a onda vai da testa até a ponta da cauda.
- **Boca:** a abertura separava os lábios e a mandíbula ficava verde por último.
  Pontes curtas (4 cm) entre pontos próximos, **só dentro de cabeça e mandíbula**,
  deixam a onda atravessar a boca. Sem essa restrição, a ponte ligava o queixo ao
  peito (a cabeça do Kumo encosta nos ombros) e a onda pulava o pescoço.
- **Estabilidade:** com a onda parada no meio, a fronteira não se move nos quadros
  0, 6, 12 e 18 da caminhada.
- **Tempo:** ativação ~0,4 s → onda ~1,6 s → faíscas ~0,4 s.

- **Cauda:** com a câmera girada 90° (`--cam-angle 90`) a espiral aparece; ela é a
  última a virar, da base até a ponta enrolada.

Renders da fase 2: `renders/corpo_cibernetico.mp4` (3 s), `renders/corpo_sequencia.jpg`,
`renders/corpo_paletas.jpg`.

Instalar no arquivo de produção continua dependendo da sua aprovação.

## 7. Decisões antigas (respondidas acima)

- A barriga também muda de cor (hoje muda para o tom "barriga" da paleta) ou fica bege?
- Os olhos devem refletir a nova cor (o aro laranja assumir o destaque da paleta) ou
  ficam laranja como identidade do Kumo?
- Faíscas residuais: as facetas que piscam bastam ou você quer partículas de verdade
  saindo do corpo?

## Arquivos

- `chromatic_shift.py`: o sistema (atributos, node group, instalação, paletas)
- `prototipo.py`: abre o Kumo, aplica efeito + finalização, renderiza
- `renders/`: sequência, paletas e animação do protótipo

```bash
blender kumo_v8_movimento.blend -b --python kumo-chromatic-shift/prototipo.py -- \
    --out <pasta> --textures <pasta kumo-3d-rodin> --stills      # ou --anim
```
