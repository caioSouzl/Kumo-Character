# Modelos 3D (Hyper3D)

| Arquivo | O que é | Situação |
|---|---|---|
| `zodia.glb` | ZodIA ativo, com esqueleto e 5 animações (`check_in`, `cheer`, `indicate`, `salute`, `stir`) | pronto (Hyper3D, versão leve: ~20 mil triângulos) |
| `ambiente.glb` | árvore com terrário de vidro + brinquedos: `bola`, `bloco`, `carrinho`, `argolas`, `balanco` | pronto (Hyper3D WorldGen, ~50 mil triângulos) |
| `kumo.glb` | o Kumo | falta; o jogo usa um lagartinho provisório na paleta oficial |

Os originais do Hyper3D foram reduzidos no Blender para rodar leve: só a
versão ativa do ZodIA, sem os olhos fixos (o jogo desenha as expressões na
tela), e texturas menores. O chão, a grama, as flores, as pedras e os
circuitos são feitos pelo próprio jogo (o chão do WorldGen vem em
"gaussian splatting", que o Godot não lê).

Ajustes em `config/game.json` → `models`:
- `zodia_rig`: osso da cabeça e posição da tela-rosto, osso da mão (laser) e
  qual animação usar em cada momento (`build`, `cheer`, `wave`...).
- `kumo_nest`: onde o Kumo dorme (dentro do globo da árvore).
- `kumo_height`: altura do Kumo quando o `kumo.glb` chegar.
