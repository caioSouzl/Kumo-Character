# Kumo · olhos-v5: teste da alternativa A e correção do vínculo

**Data:** 2026-11-11 · **Estado:** **para avaliação do Caio. Não está concluído:** as interseções não chegaram a zero sem defeito visual. A v4 e o modelo principal não foram tocados. Malha e pesos da cabeça estão intactos (hash idêntico) e o relevo continua em 8 mm e 4,4 mm. Cor da pálpebra: versão C.

## Arquivos

| Arquivo | O que é |
|---|---|
| `kumo_eyes_exp.blend` | **Principal (variante B):** v4 + correção do vínculo + ordem única das camadas, **sem aparo** |
| `kumo_eyes_exp_aparo.blend` | **Variante A:** a mesma base + aparo consistente na dobra da órbita. Guardada só para comparação. |
| `renders/14-aparo-A-x-B.png` | A × B com o olho fechado: cabeça neutra, girada ±25° e inclinada, nas 4 vistas |
| `renders/09-v4-x-v5-*.png` | v4 × v5 (B): aberto, semicerrado, 25%, 50%, 75% e fechado |
| `olhos-v5-varredura-log.txt` | Varredura completa da variante B (os resultados por passo) |

Para reconstruir a variante A: `KUMO_APARO=1 KUMO_TERMINAR=1 python src/kumo_eyes.py ../kumo_rigged.blend <pasta>`.

## 1. Defeito antigo encontrado e corrigido: o vínculo não era exato em repouso

Com a cabeça em repouso, o vínculo à pele **deslocava os pontos em até 3 mm**. A causa: a normal da pele deformada era lida por vértice (suave) e a de repouso por face (plana). O defeito vinha desde a v2.

Corrigido: as duas normais agora são lidas por vértice. Em repouso o deslocamento é de 0,00000001 m. Isso, sozinho, eliminou parte dos cruzamentos que as versões anteriores tinham.

## 2. Ordem das camadas

Antes, cada camada era empurrada e erguida separadamente, e a ordem entre elas se invertia em alguns pontos. Agora todas saem do globo na mesma direção, com a mesma compressão por vértice, e a ordem globo < íris < pupila < brilho < pálpebras é fixa. A sobreposição das pálpebras no fechamento ficou em 0,03, como na v4. Onde a pálpebra superior é transparente, ela acompanha o relevo da inferior, para as duas cascas não se cruzarem.

## 3. Alternativa A (aparo na dobra): **funciona na geometria, falha no visual**

- Remove de **todas** as camadas, juntas, os triângulos que cruzam a pele ou chegam a menos de 0,3 mm dela: 34 a 43 no olho E e 2 no D.
- Resultado geométrico: **0 triângulos cruzando a pele** e 0 pontos, com a cabeça neutra, girada e inclinada.
- **Resultado visual: reprovado.** O aparo abre pequenas janelas na pálpebra, e por elas aparece o olho laranja pintado na textura da cabeça. Isso vira **pontinhos laranja na pálpebra fechada** em todas as vistas, inclusive com a cabeça neutra (prancha 14, linhas "A"). É exatamente o fio/descontinuidade que você pediu para evitar.

## 4. Variante B (principal, sem aparo)

**Visual:** limpa. Não há pontinhos, frestas nem linha dupla; o fechamento é igual ao da v4 (pranchas 09, 06 e 14, linhas "B").

**Geometria** (mesma metodologia, mais o teste de superfície; 41 passos nos casos principais e 22 nos demais):

| Medida | v4 | v5 (B) |
|---|---|---|
| Pontos dentro da pele | 9–12 | **3–6** |
| Profundidade dos pontos | 0,46 mm | ≤ 0,29 mm (medido nas poses de teste) |
| Triângulos visíveis cruzando a pele | 27–33 | **13–22** |
| Cruzamentos entre camadas (as duas desenhadas no ponto) | não medido | 24–130 pares* |

\* Esse critério ainda não desconta a pálpebra fechada por cima. A maioria desses pares fica entre o globo, a íris, a pupila e o brilho com o olho fechado, momento em que estão cobertos. Nas renders não aparece nenhum defeito.

Todos os cruzamentos com a pele são fixos e ficam **na dobra** onde a pele da borda da órbita desce sobre o olho, principalmente no canto do olho esquerdo. Ali a pálpebra passa por baixo da pele, o que é anatomicamente o que uma pálpebra faz, mas geometricamente é uma interseção.

## 5. Fidelidade e silhueta (variante B)

| Vista | Diferença média na região dos olhos (olho aberto) | Deslocamento do olho |
|---|---|---|
| Frente | 4,46 / 255 | 0,4 px |
| 3/4 | 1,66 | 0,32 px |
| Perfil, olho direito | 4,32 | 0,67 px |
| Perfil, olho esquerdo | 2,87 | 0,22 px |

Silhueta do corpo: IoU de 0,99979 / 0,99984 / 1,0 / 0,99987 (≥ 0,9998 ✅).

## 6. Conclusão e caminhos possíveis

Zerar as interseções apagando geometria (A) cria buracos visíveis. Mantê-la (B) deixa o visual correto, mas a pálpebra continua encostando na dobra da órbita. Caminhos possíveis:

1. **Aparo "às escondidas":** remover só os triângulos que, testados por raios em várias direções de câmera, ficam **sempre** cobertos pela pele. É invisível por construção, mas talvez não zere tudo, porque parte da dobra é visível de algum ângulo.
2. **Pálpebra que "dobra" junto com a pele na dobra:** em vez de apagar, os vértices da camada seguem a própria superfície da pele (espessura zero) nos últimos milímetros. A camada vira um contato com a pele, sem atravessá-la e sem abrir janela. É a forma mais anatômica, e a mais trabalhosa.
3. **Aceitar a variante B** como base de integração, com a interseção na dobra documentada. Ela é invisível em todas as vistas testadas.
