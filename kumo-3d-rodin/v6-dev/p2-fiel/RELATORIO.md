# P2 fiel: olhos de verdade na cabeça atual do Kumo

**Pedido do Caio (2026-11-12):** "P2 ficou uma aberração, delete isso e tento com a versão fiel ao projeto".
- A tentativa com a cabeça F1.2 foi apagada. Ela continua só no histórico do git.
- Esta versão mantém a cabeça, a textura e o contorno do Kumo atual, e troca só os olhos pintados por olhos de verdade.

**Situação:** para a sua avaliação visual. A boca **ainda não foi feita** (veja o fim).

## O que mudou

1. **Olhos simétricos:**
   - A cabeça do Rodin está girada 8,5° em Z e é assimétrica: os olhos pintados diferem em posição e direção (`src/simetria.py`).
   - Os olhos novos são espelhados no plano de simetria da própria cabeça, na média dos dois pintados. Cada olho andou cerca de 5 cm.
   - A forma da cabeça não foi simetrizada.
2. **Órbita:**
   - Só as faces da janela do olho saíram da pele: 144 no olho esquerdo e 179 no direito. A borda virou uma elipse lisa sobre a pele original.
   - A borda desce numa parede curta marrom (#5B3A2E), que faz o aro do desenho.
   - A pele que encostava no globo foi afastada só o necessário: 111 vértices no olho esquerdo e 54 no direito, no máximo 8 mm.
3. **Globo:**
   - Esfera de raio 0,387, que gira pelo centro (ossos `eye.L` e `eye.R`).
   - A textura é gerada:
     - âmbar da paleta (#F4B642), mais claro no centro;
     - pupila preta vertical, nas proporções do olho pintado (deslocada para o nariz);
     - um brilho.
   - A frente do globo fica 2 a 3 cm à frente da pele, como o abaulamento do olho pintado.
4. **Pálpebras:**
   - Cascas esféricas em volta do globo: a de cima por fora da de baixo.
   - No repouso, ficam escondidas atrás da pele. Na piscada, giram em arco pelo centro do olho (ossos `palpebra_sup` e `palpebra_inf`, dos dois lados).
   - A cor é a da pele em volta. Uma linha marrom fina na borda da pálpebra de cima vira a linha do olho fechado.
5. **Textura:**
   - O olho pintado que sobrou fora da janela foi preenchido com a pele em volta (60.095 texels).
   - Isso foi feito numa cópia, `textures/kumo_v6_diffuse.png`; a textura original não mudou.
6. **Pele em volta dos olhos:** passou a ter peso só no osso da cabeça (773 vértices). Assim ela gira junto com os olhos.

## Testes

O método é o de sempre: pares de triângulos que se cruzam (reais = 0,5 mm ou mais), novos em relação ao repouso. Mais um teste: pálpebra furando a pele.

| Caso | Olhos × corpo | Olhos × olhos | Cabeça × ela mesma | Pálpebra fora da pele |
|---|---|---|---|---|
| Repouso (absoluto) | **0** | **0** | 10 reais (já existiam no modelo original) | **0** |
| Piscada a 25 / 50 / 75 / 100% | 0 | 0 | 0 | 0 |
| Piscada de um olho só (esquerdo, direito, 50%) | 0 | 0 | 0 | 0 |
| Olhar ±25° para os lados, 15° para cima | 0 | 0 | 0 | 0 |
| Olhar 15° para baixo (com e sem piscada) | 0 | 2 rasantes (0,3 mm, escondidos dentro da cabeça) | 0 | 0 |
| Olhar + piscada a 50% | 0 | 0 | 0 | 0 |
| Cabeça girada 30°, inclinada 20°, baixada 20° | 0 | 0 | 0 | 0 |
| Tudo junto (cabeça, olhar e piscada a 60%) | 0 | 0 | 0 | 0 |

**Outros números:**
- **Pesos:** até 4 ossos por vértice no corpo e 1 nos olhos; soma 1.
- **Desempenho:** 0,97 ms por atualização, contra 0,40 ms antes. A diferença são os 3.694 vértices dos olhos.

## Exportação para jogo (`kumo_v6_p2_jogo.glb` e `.fbx`)

- O conjunto tem corpo + `Kumo_Contorno` (refeito com a órbita nova) + `Kumo_Olhos`, com o rig de 54 ossos.
- Reimportados e comparados com o Blender em 6 quadros. O quadro 6 tem piscada, olhar e cabeça girada.

| Malha | Diferença máxima |
|---|---|
| Olhos (GLB e FBX) | 0,001 mm |
| Corpo | 0,11 mm |
| Contorno | 0,14 mm |

- A animação dos olhos de fato move a malha: 251 mm no quadro 6.
- O contorno de jogo continua igual ao do Blender (`contorno_corpo.png`).
- Os materiais dos olhos e das pálpebras são cor ou imagem simples, sem shader especial.

## Ainda em aberto

- **Boca:** não foi feita. A ideia é usar o mesmo método dos olhos: abrir a linha da boca na pele atual, fazer uma cavidade escura, uma mandíbula e as shape keys de boca aberta e sorriso. Isso fica para depois da sua avaliação dos olhos.
- O globo sai 2 a 3 cm da pele (o olho pintado também era abaulado).
- Os olhos ficam um pouco virados para fora: 49° no quadro da cabeça, a média dos pintados.
- A cabeça continua girada 8,5° e assimétrica, como no modelo atual.
- O brilho do olho gira junto com o olhar.

## Arquivos

- `kumo_v6_p2.blend`: o modelo com os olhos.
- `kumo_v6_p2_jogo.blend`, `.glb` e `.fbx`: o mesmo + contorno de jogo, exportado.
- `p2-corpo.png`: referência, Kumo atual e P2, nas 4 vistas.
- `p2-cabeca.png`: close da cabeça.
- `p2-expressoes.png`: piscadas, olhar e giro.
- `contorno_corpo.png`.
- `p2-medicoes.json`, `medicoes_contorno.json`, `olhos-simetricos.json`, `textures/` e `renders/`.
- `src/`:
  - `simetria.py` e `olhos_frame.py`: plano da cabeça e posição dos olhos;
  - `analise.py`;
  - `p2_fiel.py`: monta tudo e testa;
  - `base_atual.py`: renders do modelo atual;
  - `contorno_jogo_p2.py`: contorno de jogo e exportação.

Para refazer:
```bash
python src/p2_fiel.py ../maos-corretivas/kumo_v6_maos_jogo.blend olhos-simetricos.json <saída>
python src/contorno_jogo_p2.py <saída>/kumo_v6_p2.blend <saída2>
```
