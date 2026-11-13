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
