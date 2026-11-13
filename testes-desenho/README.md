# Testes: Kumo em versão desenho

**Objetivo:** conseguir recriar a aparência do Kumo desenhado (folha de modelo e referência 01) em várias posições e expressões, sem mudar o visual. Tudo nesta pasta é **teste**; nada aqui vira oficial sem a aprovação do Caio.

## Ferramentas
- `src/comparar.py`: **medidor de fidelidade**. Compara qualquer imagem do Kumo com as vistas aprovadas (frente, 3/4, perfil e costas). Alinha altura, pés e centro, e dá duas notas:
  - **silhueta:** 1,00 = contorno idêntico;
  - **cor:** diferença média dentro da figura, de 0 a 255 (0 = igual).
  Gera também uma imagem lado a lado.
- `src/vistas.py`: renderiza o Kumo 3D oficial em 8 ângulos, com fundo transparente.

## Teste 01: o Kumo 3D oficial renderizado como desenho
| Vista | Silhueta | Cor |
|---|---|---|
| Frente | 0,63 | 59 |
| 3/4 | 0,79 | 47 |
| Perfil | 0,85 | 46 |
| Costas | 0,86 | 38 |

**Conclusão:** o 3D **não serve sozinho** como versão desenho.
- **Pintura:** a textura do 3D (gerada no Rodin) é manchada e ruidosa, enquanto o desenho tem manchas de camuflagem limpas e chapadas.
- **Proporção:** de frente, a cabeça do desenho é bem mais larga que a do 3D (silhueta 0,63).

O 3D pode servir como **guia de pose e de ângulo**, mas não como fonte da aparência.

## Próximo teste (precisa de autorização)
Gerar desenhos novos com um modelo de imagem que aceita imagens de referência:
- a referência aprovada mostra a aparência;
- o render do 3D na pose desejada mostra a posição.

Cada resultado passa pelo `comparar.py` e pela aprovação do Caio.

## Teste 02: "Kumo 3D desenho" (cópia do 3D pintada com os desenhos)
`src/pintar_desenho.py` pinta uma **cópia** do Kumo 3D (o oficial não muda) projetando os desenhos aprovados de frente, de perfil (os dois lados) e de costas. A vista 3/4 **não entra** na pintura: serve para conferir um ângulo que o método nunca viu.

O que o projetor faz:
- **Peso por vista:** cada ponto da pele pega a cor da vista que o vê mais de frente.
- **Emendas:** a cor de fundo é misturada entre as vistas, e o detalhe vem da vista principal, para não marcar a emenda.
- **Contorno do desenho:** fica fora da pintura e é refeito em 3D, com linha nas bordas.
- **Olhos:** são os olhos 3D aprovados (v5), que piscam e olham. Os olhos desenhados não entram na pintura.
- **Pontos que nenhuma vista vê:** recebem a cor dos pontos vizinhos na superfície 3D.

`src/poses.py` gera 12 imagens em poses, ângulos e olhares diferentes (`teste-02-kumo-3d-desenho/folha-poses.png`).

| Vista | Teste 01 (3D cru) | Teste 02 |
|---|---|---|
| Frente | 0,63 · cor 59 | 0,61 · cor 54 |
| 3/4 (nunca vista pelo método) | 0,79 · cor 47 | 0,78 · cor 44 |
| Perfil | 0,85 · cor 46 | 0,85 · cor 34 |
| Costas | 0,86 · cor 38 | 0,84 · cor 22 |

A nota de cor de frente piora porque o olho 3D não tem exatamente o formato do olho desenhado. A silhueta de frente continua baixa por causa da cauda, que no desenho de frente está enrolada para o lado.

**Ainda falta:**
1. A cabeça do desenho é mais larga de frente.
2. Nas áreas inclinadas aparecem pequenas manchas desfocadas.
3. Braços muito erguidos ficam escondidos atrás da cabeça. Isso é proporção do Kumo, mas as poses "acenar" e "comemorar" precisam de outros ângulos.
4. Com olhar na diagonal ainda aparecem pontinhos na pupila.
5. Faltam boca e sobrancelhas para expressões além do olho.

**Achado no caminho:** o 3D de jogo tinha buracos na pupila com o olhar no meio do caminho. Foi corrigido no oficial (`kumo-3d-rodin/v6-dev/ombros/RELATORIO.md`).
