# Modelos 3D (Hyper3D)

Coloque aqui os modelos exportados do Hyper3D em `.glb`:

| Arquivo | O que é | Altura/tamanho no jogo |
|---|---|---|
| `zodia.glb` | o robô ZodIA | 1,9 m (`models.zodia_height`) |
| `kumo.glb` | o Kumo | 1,0 m (`models.kumo_height`) |
| `ambiente.glb` | campinho com árvore, flores e pedras | raio 5,2 m (`models.environment_radius`) |

O jogo acha os arquivos sozinho, ajusta a escala e apoia no chão. Se um
arquivo não existir, usa o modelo provisório. Nomes e tamanhos ficam em
`config/game.json` → `models`.

O rosto do ZodIA (a tela com as expressões) é desenhado pelo jogo por cima
da cabeça. Com o modelo novo, ajuste `models.zodia_face.offset` (posição) e
`size` até a tela encaixar.
