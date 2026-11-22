# Olhos novos do Kumo (arte do Caio, 22/11)

**Pedido do Caio:**
- "Faça os novos olhos do Kumo", com as camadas que ele desenhou: globo, contorno, membrana nictitante, íris e pupila.
- O brilho fica de fora: ele entra depois, nas animações e nas imagens de postagem.
- Adendo: "Quero que faça igual aos vídeos que te mandei, para não ter conflito com as camadas na hora do movimento."

**Ajuste do Caio (22/11, depois da primeira versão: "Ficou ótimo"):**
- íris e pupila trocadas pela imagem nova `arte/iris-pupila.png`: a íris tem o mesmo tamanho, e a pupila ficou menor (172 × 316 px na arte, contra 206 × 375), então aparece mais anel âmbar;
- membrana nictitante na cor **#E4A633**.

As fotos e a exportação abaixo já são da versão ajustada.

**Resultado:** os olhos novos usam a técnica do vídeo do decal (@pol.gc). Cada olho é **uma superfície só, com um material só**, então não há camadas para brigar no movimento.

Imagens:
- `renders/folha_frente.png`: frente em 8 estados (aberto, olhar para os 4 lados, meia piscada, piscada, um olho);
- `renders/folha_34_lado.png`: 3/4 e lado;
- `renders/kumo-olhos-novos-corpo.png`: corpo inteiro, ao lado da arte.

## Como ficou

| Peça | Como é feita |
|---|---|
| Superfície do olho (`KumoOlho.L/.R`) | As faces da pele em volta do olho, separadas num objeto próprio. Mesma forma, mesmos pesos e mesma borda da pele: nada fica empilhado |
| Branco do globo | No material, dentro da abertura |
| Íris e pupila | **Decal:** a sua arte é projetada a partir de um Empty (`Decal_Olho.L/.R`) preso ao osso `olho.L/.R` |
| Membrana e contorno | No mesmo material, por cima da íris. A íris passa por baixo do aro quando o Kumo olha para o lado |
| Ordem dentro do material | pele → branco → íris e pupila → membrana → contorno |
| Abertura | A elipse da abertura de antes. Recua só onde a cabeça se dobra para o lado (até 11% no olho esquerdo e 16% no direito), para a arte não esticar |
| Pele em volta | Uma faixa logo fora da borda recebe a cor da pele vizinha, para apagar a sombra do olho antigo pintada na textura |

## Rig do olhar (como no vídeo)

- **Osso de cada olho (`olho.L/.R`):** gira a partir de um ponto 0,35 m para dentro da cabeça, com **Damped Track** num alvo à frente (`MCH_alvo_olho.L/.R`). O decal vai na ponta do osso e desliza pela superfície.
- **Controle:** os alvos andam com o controle de sempre, `controle_olhar`. ±1 vale ±11°, o mesmo alcance de antes. Nada muda na Central nem nas animações que já usam esse controle.
- **Sentido do olhar:** conferido contra o olho antigo. A diferença de direção fica entre 0° e 20°, e o deslocamento é de 67 mm, contra 53 a 71 mm antes.
- **Piscada:** as mesmas pálpebras e shape keys de antes, no `controle_olhos`.

## Exportação para o jogo (`jogo/`)

- **Arquivos:** `kumo_v6_jogo.glb` (12 MB) e `.fbx` (4,5 MB).
  - Cada olho sai com a aparência em repouso gravada numa textura (`olho_L_jogo.png` e `olho_R_jogo.png`), num material de emissão, como os olhos de jogo anteriores.
- **Reimportação:** GLB e FBX reimportados, com diferença de **0,0 mm** em todas as peças (corpo, boca, língua, pálpebras e olhos).
- **Limite:**
  - O decal usa a coordenada de um objeto, que o glTF e o FBX não levam.
  - No jogo, por enquanto, o olho fica parado olhando para a frente; a piscada funciona.
  - Para o olhar se mexer no Godot, falta um shader que receba a posição dos ossos `olho.L/.R`. Os ossos já vão no arquivo.

## Tentativas que não ficaram

1. **Globo esférico girando dentro de um buraco na pele** (`src/tentativa_globo_esferico.py`, `renders/tentativa1_*`).
   - A região dos olhos do Kumo é quase plana: uma esfera ajustada a ela erra 6 mm em média e até 46 mm.
   - Para girar sem atravessar a pele, a esfera precisou ficar de 3 a 8 cm afundada.
   - Visto de frente, aparecia a parede de dentro da cabeça.
2. **Decal sem os ajustes** (`renders/tentativa2_decal_sem_ajustes.png`): três defeitos, todos corrigidos.
   - O contorno engrossava no canto de cima, onde a cabeça se dobra.
   - O modificador do contorno do Kumo (Solidify), que só funciona em malha fechada, desenhava uma faixa escura na borda da superfície aberta.
   - A faixa de pele limpa pegava um traço escuro antigo.

## O que fica igual

- **Arquivos oficiais:** `kumo_rigged.blend`, as texturas e `olhos-v1..v5`, conferidos com `auditoria/hashes-antes.sha256`.
- **Arquivo de partida:** `../boca/kumo_v6_boca.blend` não é alterado; o resultado vai para `kumo_v6_olhos_novos.blend`.

## Arquivos

| Arquivo | O que é |
|---|---|
| `kumo_v6_olhos_novos.blend` | Kumo com os olhos novos (decal, rig do olhar, pálpebras) |
| `jogo/kumo_v6_olhos_novos_jogo.blend`, `jogo/kumo_v6_jogo.glb`, `jogo/kumo_v6_jogo.fbx` | Versão de jogo e exportações |
| `arte/` | A arte enviada pelo Caio |
| `texturas/` | Fundo, aro e máscara de cada olho (no espaço da projeção) e a imagem do decal |
| `src/olhos_novos.py`, `src/exportar.py`, `src/fotos.py` | Construção, exportação com conferência e fotos |
| `src/olhar_antigo.py` | Régua do olhar antigo, para conferir o sentido do olhar novo |
| `medicoes_olhos_novos.json`, `jogo/medicoes_exportacao.json` | Medições |

Para refazer, a partir de `v6-dev/`:

```
blender --background boca/kumo_v6_boca.blend --python olhos-novos/src/olhos_novos.py -- olhos-novos/arte olhos-novos
blender --background olhos-novos/kumo_v6_olhos_novos.blend --python olhos-novos/src/exportar.py -- olhos-novos/jogo
```
