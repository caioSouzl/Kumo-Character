# P1 iteração 7: proporções e silhueta da mão (A7)

**Situação: para a sua aprovação visual.** Ela não é automática por passar nos testes. A iteração 6 e as anteriores estão intactas, assim como o modelo oficial (os hashes da auditoria conferem). Nenhum osso foi acrescentado.

O estilo A7 parte da proposta A da iteração 6; é o mesmo script, com `P1_MAO=A7`. Cotovelo, punho e juntas dos dedos mantêm os valores da iteração 5.

## Mudanças de forma

| Item | Proposta A (iteração 6) | A7 |
|---|---|---|
| Comprimento da palma | 0,100 | **0,125** (×1,25), com um anel a mais no meio da palma |
| Largura da palma | 0,80 da largura medida | **0,70** |
| Espessura do dedo | 0,90 | 0,86 (mantém uma fenda de cerca de 4 mm com a palma mais estreita) |
| Curvatura dos dedos em repouso | 0,80 | **1,10** (mais dobrados para a frente) |
| Polegar: comprimento e espessura | 0,80 / 1,05 | **0,60 / 0,95** |
| Polegar: posição | Faces altas da palma (anéis 1 e 2) | **Mais baixo, perto dos dedos** (anéis 2 e 3); sai menos para o lado e desce mais |
| Base do polegar | 7 anéis | **8 anéis**, com a base crescendo aos poucos |

## Os dois defeitos localizados da iteração 6

1. **Lasca na base do polegar (mão aberta).** O anel extra sozinho não resolveu. A causa real estava nos **pesos**: o script decidia por distância se cada vértice era do polegar ou do dedo 1. Com o polegar mais perto dos dedos, vértices do dedo 1 recebiam peso do polegar (até 0,45) e vice-versa, e a aresta esticava 3,2 vezes.
   - **Correção:** cada vértice agora pertence ao tubo que o criou (marca exata, sem palpite).
   - Esticamento máximo nessa região: **3,2 → 1,45**. A lasca não aparece mais nas imagens.
2. **Par de 0,87 mm a 65°.** Resolvido. O fechamento progressivo de 30° a 70° deu **zero pares em todos os ângulos**, inclusive contatos rasantes.

## Ajustes de pesos da mão (avaliados separadamente, com comparação)

| Ajuste | Iteração 6 | A7 | Comparação que justifica |
|---|---|---|---|
| Transição do polegar | 2,0× | **2,0×** (mantido) | 2,5× também zerava, mas não era necessário |
| Pivô do polegar | 0,006 | **0,006** (mantido) | Com 0,012, a mão fechada tinha 2 a 5 pares reais |
| Gradiente do metacarpo | −0,25 a 0,85 | **mantido** | Testei 0,15–0,70, 0,30–0,95, −0,50–1,00 e a faixa ao longo da palma; nenhum mudou o vinco, que não vinha daí |
| **Base dos dedos (nó)** | 1,5× | **2,0×** | Com o dedo mais fino (raio de 0,027 para 0,023), 1,5× deixava 3 pares reais no nó do dedo 3 (mão fechada); com 2,0×, zero. Em metros, a janela fica igual à aprovada (0,046 contra 0,040). |

Também testei a mão fechada **sem o metacarpo**: ficou com 1 par real, ou seja, o vinco vinha do nó do dedo 3, e não do osso. O metacarpo foi mantido como estrutural.

## Validação

| Teste | Proposta A (iteração 6) | A7 |
|---|---|---|
| Repouso | 0 | **0** |
| Mão aberta | 0 · compressão 0,61 · esticamento 3,1 (com lasca) | **0** · 0,62 · **2,1** (sem lasca) |
| Mão fechada | 0 reais, 6 rasantes · 0,12 | **0 pares de nenhum tipo** · 0,16 |
| Dedos a 45° | 0 · 0,37 | 0 · 0,30 |
| Polegar isolado | 0 · 0,29 | 0 · 0,51 |
| Dedos alternados | 0 · 0,12 | 0 · 0,17 |
| Palma curvada | 0 · 0,70 | 0 · 0,69 |
| Punho ±45° | 0 · 0,58 | 0 · 0,58 |
| Punho lateral ±30° | 0 · 0,72 | 0 · 0,73 |
| Fechamento de 30° a 70° | 1 real a 65° (0,87 mm) | **0 em todos** |
| Malha | 1.354 vértices | 1.418 vértices, 100% quads; até 4 influências, soma 1 |
| Desempenho | 0,13 ms | 0,11 ms |

**Deformações visíveis, sem cruzamento:**
- O esticamento máximo continua alto na mão fechada (3,8) e na palma curvada (3,5). São arestas pequenas na dobra palmar, e nas imagens aparecem como vincos, não como rasgos.
- A compressão da junta dos dedos na mão fechada (0,16) segue mais forte que na iteração 5 (0,33), consequência de dedos curtos e grossos.

## Proporções (vista de frente)

| Proporção | Referência | Iteração 6 A | **A7** |
|---|---|---|---|
| Largura da mão ÷ antebraço | 2,00 | 2,26 | **1,97** |
| Comprimento ÷ largura | 1,14 | 0,83 | **1,08** |
| Palma ÷ dedo | 1,38 | 1,13 | **1,36** |
| Polegar ÷ dedo | cerca de 0,7 | 1,00 | **0,75** |
| Comprimento ÷ espessura do dedo | 1,86 | 1,83 | 1,98 |

## Minha leitura visual (a decisão é sua)

- **Mais perto da referência:**
  - silhueta de frente mais longa e estreita;
  - dedos mais curvados para a frente, com os nós aparecendo no perfil;
  - polegar menor e mais baixo, perto dos dedos.
- **Ainda diverge:**
  - **Polegar:** lê como um botão redondo saindo para o lado. No desenho, é um lóbulo alongado que desce junto aos dedos. Testei o polegar descendo colado à palma (mais parecido com o desenho), mas ele atravessava a palma em repouso e ao fechar (16 a 54 pares reais). A versão entregue é o meio-termo sem cruzamentos.
  - **Palma:** com ela mais longa, a mão perde um pouco do volume "almofadado" da proposta A. Na vista de perspectiva, a palma parece mais plana.
  - **Dedos:** ficaram ligeiramente compridos para a espessura (1,98 contra 1,86).

## Imagens

- `p1i7-comparacao-vistas.png`: referência, modelo atual, iteração 6 A e A7, de frente, de lado, por cima (dorso) e em perspectiva.
- `p1i7-encaixe.png`: referência, iteração 6 A e A7 encaixadas no corpo.
- `p1i7-arame.png`: wireframe da iteração 6 A e da A7, em repouso e com a A7 fechada.
- `p1i7-movimentos.png`: repouso, aberta, fechada, dedos a 45°, polegar, dedos alternados e punho ±45°.

## Arquivos

- `src/p1_iter7.py`: `P1_MAO=A7`; `P1_EST='{json}'` sobrescreve chaves de estilo, como foi usado nas varreduras.
- `src/render_mao_atual.py`: renderiza a mão do modelo atual, só leitura.
- `A7/`: `.blend` (só o braço e o rig), medições e renders.
