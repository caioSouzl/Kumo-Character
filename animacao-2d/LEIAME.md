# Kumo · animação 2D (5 segundos)

**Vídeo:** `kumo-animacao-5s.mp4` (1080 × 1350, em pé para o celular, 24 quadros por segundo, 120 quadros). Começa e termina na mesma pose, então dá para repetir em loop.

**Arte:** é a ilustração original da referência, sem redesenho. Usei a vista de frente recortada em `character-model-sheet/assets/view-front.png`. A única coisa desenhada por cima é a pálpebra na piscada, com o verde da pele em volta do olho e a linha de contorno escura da arte.

## O que acontece

| Tempo | Movimento |
|---|---|
| 0–5 s | Respiração leve e cauda balançando |
| 0,35 s | Piscada |
| 0,7–1,4 s | Inclina a cabeça para um lado, curioso |
| 1,9–2,6 s | Inclina para o outro lado |
| 2,15 s | Piscada |
| 2,9–3,3 s | A cabeça volta ao centro |
| 3,3–4,55 s | Pulinho feliz: agacha, sobe esticado, cai e amortece (squash & stretch), com a sombra encolhendo no ar |
| 4,35 s | Piscada na aterrissagem |

## Como foi feito

Técnica de recorte (cutout), em `src/animar.py`:
- a cabeça é uma peça separada, que gira pelo pescoço;
- a cauda gira em torno da base, com mais movimento na ponta;
- o corpo inteiro respira e pula, apoiado nos pés.

Para refazer: `python3 src/animar.py <pasta>` gera os quadros. Depois:
`ffmpeg -framerate 24 -i <pasta>/quadros/q%04d.png -c:v libx264 -pix_fmt yuv420p -crf 18 kumo-animacao-5s.mp4`

`kumo-animacao-quadros.png` mostra 10 quadros do vídeo, para conferir.
