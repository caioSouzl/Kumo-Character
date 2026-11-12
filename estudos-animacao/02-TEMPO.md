# Estudo 2 · Tempo de animação (piscar, olhar, respirar, pular)

Pesquisa feita para a animação 2D do Kumo e transformada em regras que a ferramenta `animacao-2d/src/planilha.py` confere sozinha, quadro a quadro, a 24 quadros por segundo.

## Piscar
- **Piscada normal:** 2 quadros para fechar, 1 fechado e 3 para abrir. **Rápida:** 2 para fechar, sem ficar fechado, 3 para abrir. **Longa** (mudança de ideia): 3 para fechar, 2 fechado e 4 para abrir. Abrir é sempre mais lento que fechar. Fontes: Bloop Animation; Animation Mentor ("3 a 5 quadros para baixo, pausa breve, 2 a 4 para abrir").
- Fechar em 1 ou em 2 quadros é escolha de atuação, e pequenas mudanças na piscada mudam muito a atitude. Fonte: transcrição de *How to Animate a Perfect Blink*, Scribble Kibble 58, 00:01:04 e 00:01:37.
- Num desenho 2D comum, a pálpebra de baixo quase nunca se mexe, porque "fica estranho" (mesma transcrição, 00:02:59).
- **Quando piscar:** quase sempre numa virada de cabeça; numa mudança de pensamento; e depois de um olhar parado demorado, para manter o personagem vivo. Fonte: Bloop.

## Olhar
- Uma olhada rápida tem cerca de **3 quadros**: posição inicial, um intermediário e a final. Trocar o ponto de interesse leva de 3 a 4. Fonte: Bloop.
- Os olhos chegam antes da cabeça: o olhar começa alguns quadros antes do giro (princípio de sobreposição e arrasto aplicado ao rosto).

## Respirar (parado)
- Movimento pequeno, porque respiração grande parece pulo. A inspiração é mais lenta que a expiração, e cada parte do corpo reage com um leve atraso. Fontes: Keyframe; Gamedeveloper.com.

## Pular
- **Preparação** (agachar antes de subir): cerca de 2 a 4 quadros num jogo, para não parecer travado; mais quadros deixam o pulo mais pesado.
- **Esticar** ao subir: o pico vem nos primeiros 3 a 5 quadros.
- **Achatar na queda:** 1 a 2 quadros, cerca de 80 a 120 ms.
- **Arrasto:** coluna, pescoço e cabeça atrasados um ou dois quadros cada.
- Fontes: Game Developer (*12 principles in video games*); *Why 90-year-old animation theory still matters for pixel art*; MoCap Online (*Platformer animation*).

## O que a ferramenta achou
| Regra | Animação 1 | Animação 2 |
|---|---|---|
| Piscadas no tempo certo | 2 de 3 (a da queda abre rápido demais) | 5 de 5 |
| Piscar ao virar a cabeça | 0 de 3 viradas | 3 de 3 |
| Olhos antes da cabeça | não tem olhar separado | 3 de 3 (2 quadros antes) |
| Olhadas de 2 a 4 quadros | — | 3 de 3 (3 quadros) |
| Preparação do pulo | 4 quadros ✔ | 6 quadros ✔ |
| Pico do achatamento na queda | 4 quadros depois do contato ✘ | 2 quadros ✔ |
| O loop emenda | ✔ | ✔ |
| Cabe na tela | **corta a cabeça** nos quadros 89 a 92 | folga de 75 px |

As planilhas desenhadas estão em `animacao-2d/planilha-animacao-1.png` e `planilha-animacao-2.png`: um ponto por quadro, então o espaçamento entre os pontos mostra a velocidade.

## Vídeos
Não deu para transcrever vídeos do YouTube aqui: o site bloqueia downloads automáticos deste ambiente, e não forcei. Usei a transcrição pública do vídeo da Scribble Kibble e os textos acima.

## Links
- https://www.bloopanimation.com/blinking-animation/
- https://www.animationmentor.com/blog/tutorial-animate-blinks-eye-movement/
- https://www.theponyarchive.com/archive/youtube/UCwf7GkXUML0Whgdt6lvMFTw/How_to_Animate_a_Perfect_Blink_Scribble_Kibble_58-Crowne_Prince-20170428-youtube-3840x2160-snG8TOmGlNw.en.vtt
- https://www.keyframe.it.com/learn/animate-a-character
- https://gamedeveloper.com/design/tips-to-create-funny-and-juicy-character-animations-with-spine-basics
- https://www.gamedeveloper.com/production/the-12-principles-of-animation-in-video-games
- https://www.sprite-ai.art/guides/animation-principles
- https://mocaponline.com/blogs/mocap-news/platformer-animation-guide
