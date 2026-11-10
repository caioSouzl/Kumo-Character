# Kumo — sistema ocular experimental (olhos-v1)

**Estado:** experimental, **aguardando avaliação do Caio**. Não é a versão oficial.
A versão aprovada (`../kumo_rigged.blend`, `../kumo_quad.blend`, GLBs, textura) não foi tocada: os hashes SHA-256 conferem antes e depois de cada execução.

Resultados e medições: [`RELATORIO-OLHOS-V1.md`](RELATORIO-OLHOS-V1.md).

## Arquivos

| Arquivo | O que é |
|---|---|
| `kumo_eyes_exp.blend` | Cópia do Kumo com o sistema ocular novo |
| `src/kumo_eyes.py` | Constrói tudo a partir de `../kumo_rigged.blend` (só leitura) |
| `src/validate_eyes.py` | Estados de teste, medição de penetração e renders (não grava .blend) |
| `src/compose_sheets.py` | Pranchas de comparação e métricas de fidelidade |
| `textures/olho_{L,R}_*.png` | Camadas do olho tiradas do olho pintado original |
| `olhos-v1-construcao.json` | Medidas de cada olho (centro, eixos, raio do globo, ângulos) |
| `olhos-v1-medicoes.json` | Varredura de penetração em todos os estados |
| `olhos-v1-fidelidade.json` | Semelhança do olho aberto, posição, distância e silhueta |
| `renders/` | Pranchas de avaliação; `renders/estados/` tem cada render individual |

Para refazer: `python src/kumo_eyes.py ../kumo_rigged.blend .`, depois `validate_eyes.py orig ../kumo_rigged.blend .`, `validate_eyes.py exp kumo_eyes_exp.blend .` e `compose_sheets.py .` (Blender 5.2 via módulo `bpy`).

## Como o olho foi reconstruído

A malha da cabeça continua exatamente igual (mesmo hash de vértices e faces, mesmos modificadores). O olho pintado na textura foi **medido e separado em camadas**, cada uma num objeto próprio que fica por cima da pele, com folgas de 0,5 a 2,4 mm. Com os olhos abertos, a soma das camadas reproduz o olho original pixel a pixel. Todas as camadas são recortadas pelo **contorno exato do olho pintado** (a "janela"), por isso nada pode vazar para fora do olho nem mudar o contorno.

Cada olho foi medido separadamente, porque o modelo do Rodin é assimétrico (o olho esquerdo é mais largo). Nada foi espelhado.

## Objetos novos (coleção `Kumo_Olhos_v1`)

`X` = `L` (olho esquerdo do Kumo, lado +X) ou `R` (olho direito).

| Objeto | Função | Preso a | Folga sobre a pele |
|---|---|---|---|
| `Kumo_EyeWindow_X` | Vazio que define o contorno do olho (a "janela") e o sistema de coordenadas das camadas fixas | osso `head` | — |
| `Kumo_Eye_X` | Globo/esclera: casca que copia a superfície do olho, com o creme e o âmbar originais | armadura (mesmos pesos da pele) | 1,0 mm |
| `Kumo_Iris_X` | Anel âmbar escuro em volta da pupila | osso `eye.X` + *Shrinkwrap* no globo | +0,5 mm |
| `Kumo_Pupil_X` | Pupila (formato original, inclusive o recorte) | osso `eye.X` + *Shrinkwrap* | +0,9 mm |
| `Kumo_Catchlight_X` | Brilho, **preso ao globo/córnea**: gira junto com o olhar | osso `eye.X` + *Shrinkwrap* | +1,3 mm |
| `Kumo_LidLow_X` | Pálpebra inferior (cor da pele em volta, linha de cílio fina) | armadura (pesos da pele) | +1,8 mm |
| `Kumo_LidUp_X` | Pálpebra superior (cor da pele, linha de cílio escura) | armadura (pesos da pele) | +2,4 mm |

As pálpebras antigas `Kumo_Lid_L/R` continuam na cena, **ocultas**, só para comparação.

Materiais novos: um por objeto, com o mesmo nome do objeto. São emissão pura, como o toon aprovado, com a mesma força 1,0. Nenhum material, textura ou configuração aprovada foi alterado. A única mudança de cena é `transparent_max_bounces` 8 → 24, necessária para as camadas recortadas, e foi feita só na cópia.

## Ossos novos (filhos de `head`, não deformam)

| Osso | Pivô | Uso |
|---|---|---|
| `eye.L`, `eye.R` | Centro do globo | Gira íris, pupila e brilho. Tem *Damped Track* para o alvo do mesmo lado. |
| `eye_target` | À frente do rosto | **Mover este osso dirige os dois olhos juntos** (para cima e para baixo, e para os lados). |
| `eye_target.L`, `eye_target.R` | À frente de cada olho | Ajuste fino de um olho só. |
| `lid_up.L/R`, `lid_low.L/R` | Centro do globo | Rotação = quanto a pálpebra fecha. São movidos pelos controles abaixo, mas também podem ser girados à mão. |

A pálpebra segue o arco exato de uma rotação em torno do centro do globo. Esse arco foi pré-calculado em **40 estágios (shape keys `Fecha_xxx`)**, cada um com todos os vértices sobre a superfície do olho. A rotação do osso escolhe o estágio. Entre dois estágios, o trajeto foi verificado em três pontos intermediários e corrigido onde passaria perto demais da pele (o degrau no topo da órbita). Por isso não há penetração também no meio dos estágios.

## Controles (propriedades no osso `head`, de 0 a 1)

| Propriedade | Efeito |
|---|---|
| `piscar` | Fecha os dois olhos (0 aberto, 1 fechado) |
| `piscar_E` | Fecha só o olho esquerdo do Kumo |
| `piscar_D` | Fecha só o olho direito do Kumo |
| `fechar_parcial_E`, `fechar_parcial_D` | Semicerrar (desconfiado, sonolento) |
| `acompanhar_olhar` | Quanto as pálpebras seguem o olhar vertical (padrão 0,5) |

Os controles se combinam pelo maior valor: com `piscar` = 0,3 e `piscar_E` = 0,8, o olho esquerdo fica 80% fechado. Todos os drivers são "expressões simples", que funcionam mesmo com a execução de scripts Python desligada no Blender.
