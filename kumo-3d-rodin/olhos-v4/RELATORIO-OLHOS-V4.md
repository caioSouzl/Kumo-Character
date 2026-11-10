# Kumo · olhos-v4: tom, canto interno e investigação do resíduo

**Data:** 2026-11-10 · **Estado:** **para avaliação do Caio.** Não está aprovado. A `olhos-v3` e o modelo principal não foram tocados (hashes conferem; a malha da cabeça é idêntica).

Mantido da v3: vínculo à pele, relevo de 8 mm e 4,4 mm (configuração experimental), pesos e malha da cabeça intactos, nenhuma folga reduzida e nenhuma pálpebra afastada.

## 1. Canto interno do olho esquerdo: **resolvido**

- O fio claro junto à marca escura do nariz entrou na área que a pálpebra cobre: 159 pixels de textura no olho E e nenhum no D.
- Ele só é coberto **quando a pálpebra fecha**. Com o olho aberto a pálpebra fica estacionada fora, então a aparência é a mesma.
- Marcas escuras do rosto (a do nariz) foram excluídas de propósito.
- A textura da cabeça não foi alterada.

Pranchas `09-v3-x-v4-frente` e `09-v3-x-v4-perfil_D` (esta mostra o olho esquerdo): a 75% e fechado, o fio aparece na v3 e não aparece na v4.

## 2. Tom da pálpebra: três variantes testadas (prancha `13-tom-variantes.png`)

| Variante | O que é | Resultado |
|---|---|---|
| A | Base lisa contínua com a pele em volta (como na v3) | Limpa, mas uniforme |
| B | Base + detalhe real da pele vizinha, em pedaços aleatórios com transição suave (sem espelhamento) | **Rejeitada.** A pele do Kumo é pintura cel-shading, com áreas lisas e bordas nítidas. Os pedaços trazem fragmentos dessas bordas e formam um padrão "riscado" artificial. |
| **C** | Base lisa + 40% só da frequência média do detalhe | **Escolhida como padrão da v4.** Variação leve e irregular, sem padrão visível. |

Medidas da variação de detalhe (desvio da textura de alta frequência):

| Olho | Pele em volta | Pálpebra v3 | Pálpebra v4 (antes da redução para 40%) |
|---|---|---|---|
| E | 0,0138 | 0,0004 | 0,0102 |
| D | 0,0076 | 0,0003 | 0,0055 |

O brilho médio continua igualado ao da pele em volta.

**Avaliação honesta:** a oval suave do olho fechado **continua visível** nas três variantes. Ela é o contorno da área onde terminam as formas grandes pintadas no rosto (as manchas verde-amareladas). Nenhum preenchimento automático continua essas formas de forma convincente. Uma solução definitiva provavelmente exige **pintar à mão** a textura da pálpebra fechada, num arquivo separado e reversível, sem tocar na textura da cabeça.

## 3. Resíduo de 0,46 mm: investigado, **não eliminado**

**O que foi feito:**
- Refino local da malha no canto da órbita esquerda: 3 níveis, 18 triângulos, conforme, sem rachaduras e sem mudar a forma.
- A amostragem já testava 15 pontos por triângulo.
- **Novo teste de interseção real superfície × superfície:** cada triângulo renderizado das camadas é cruzado com cada triângulo da pele.

**Resultado:**

| Medida | v3 | v4 |
|---|---|---|
| Profundidade máxima (pontos) | 0,46 mm | 0,46 mm |
| Pontos dentro da pele (olho E) | 9 | 9 (11–12 com a cabeça girada) |
| Triângulos visíveis cruzando a pele | não medido | **27–33 (fixos)** |

Distribuição dos triângulos visíveis que cruzam a pele (cabeça neutra):
- **Olho E:** pálpebra inferior 13, pálpebra superior 6, pupila 2, brilho 2, íris 1, globo 1.
- **Olho D:** íris 2, pupila 2, brilho 2.

Os valores são fixos em todos os estados: não mudam com piscada, olhar, rotação nem relevo.

**Diagnóstico:**
- Os cruzamentos estão todos na **borda das camadas**, numa dobra onde a pele da borda da órbita desce até encostar na superfície do olho. Ali o espaço vai a zero.
- Qualquer camada com espessura, por fina que seja a malha, encosta na pele nessa linha. Por isso o refino não resolveu: o problema não é resolução, é a camada **continuar para dentro da dobra**.
- A nova medição mostrou também 2 triângulos por camada no olho direito, que a v3 não detectava.

### Alternativas (não implementadas, aguardando sua decisão)

| Opção | O que faz | Impacto visual / anatômico |
|---|---|---|
| **A. Aparar as camadas na dobra** (recomendada) | Remove só os triângulos das camadas onde o espaço até a pele fica abaixo de cerca de 0,3 mm. As pálpebras e camadas terminam exatamente na linha da dobra, como uma pálpebra real termina na pele. | A pele da borda da órbita já cobre essa linha, então não deve aparecer. Risco: um fio da cor de baixo visível em ângulos rasantes; precisa ser conferido nas renders. Malha e pesos da cabeça intactos. |
| B. Aceitar como linha de contato | Classifica a dobra como contato (espessura zero), sem mudar nada | Nenhuma mudança visual, mas a interseção geométrica continua existindo, o que você não quer |
| C. Alterar a cabeça ou os pesos | Abrir a dobra na malha da cabeça | **Viola as restrições** (malha e pesos aprovados). Não recomendo. |

## Validação (mesma metodologia da v3, mais o teste de superfície)

- Estados: piscada simultânea, E e D (41 passos), semicerrar, olhar para os 4 lados, cabeça girada ±18° e ±25°, olhar lateral durante a rotação, inclinada e combinada (22 passos cada).
- Profundidade máxima: **0,46 mm em todos os casos**, sempre os mesmos pontos do canto da órbita esquerda.
- Olho aberto igual ao da v3:

| Vista | Diferença média na região dos olhos | Deslocamento do olho |
|---|---|---|
| Frente | 4,65 / 255 | 0,4 px |
| 3/4 | 1,75 | 0,45 px |
| Perfil, olho direito | 4,5 | 0,86 px |
| Perfil, olho esquerdo | 3,0 | 0,32 px |

- **Silhueta:** IoU de 0,99979 / 0,99985 / 1,0 / 0,99987 (≥ 0,9998 ✅).

## Pranchas (`renders/`)

| Arquivo | Conteúdo |
|---|---|
| `09-v3-x-v4-{frente,34,perfil_E,perfil_D}.png` | **v3 × v4** em aberto, semicerrado, 25%, 50%, 75% e fechado (os arquivos `perfil_E`/`perfil_D` mostram o olho direito/esquerdo) |
| `13-tom-variantes.png` | Variantes de tom A / B / C |
| `02`–`08`, `10` | Fechamento neutro, foco 50%, piscada individual, olhar, cabeça girada 18°/25°/−25°, olhar durante a rotação, fidelidade com rotação, GIF |
| Relevo | Igual ao da v3: `../olhos-v3/renders/11-relevo-alturas.png` e `12-relevo-final.png` |
