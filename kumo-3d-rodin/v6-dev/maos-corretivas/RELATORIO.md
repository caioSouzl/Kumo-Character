# Mãos: correção da mão fechada, contorno e exportação para jogos

**Autorização do Caio (2026-11-11):** "Autorizo todas as reclamações". Isso cobre a shape key corretiva da mão fechada, a solução do contorno em jogo e a conferência do FBX. O P2 foi autorizado na mesma mensagem e começa depois desta etapa.

**Situação:** para a sua avaliação visual. Nada foi aprovado só por passar nos testes. O modelo oficial e a versão `bracos-originais-dedos` não foram alterados: este trabalho parte de uma cópia.

## 1. FBX dos braços com dedos (pendência anterior)

O FBX `bracos-originais-dedos/kumo_maos_dedos.fbx` foi reimportado e conferido. Os resultados estão em `fbx_reimportado.json`.

| Teste | Resultado |
|---|---|
| Ossos | 48, com os mesmos nomes |
| Vértices | 7.548, iguais ao Blender |
| Influências por vértice | no máximo 4; soma 1 em todos; nenhum vértice sem peso |
| Pele (mesma pose aplicada aos dois) | diferença máxima de 0,0004 mm |
| Animação do FBX contra o GLB, nos 4 quadros de teste | diferença máxima de 0,0014 mm |

## 2. Shape key corretiva da mão fechada

**Como funciona:**
1. Na pose da mão fechada (dedos a 70°), os pontos onde a mão atravessa a si mesma são empurrados para dentro da própria superfície.
2. O empurrão tem uma transição suave e afeta só alguns milímetros.
3. O resultado é gravado como forma corretiva (`Corretiva_MaoFechada.L` e `.R`).

**Quem liga a forma:** o próprio fechamento dos dedos, por um driver. Ela começa a agir com os dedos a 40° e chega a 100% aos 69°. Nas outras poses fica em 0, então não muda nada nelas.

| Lado | Vértices movidos | Ajuste máximo |
|---|---|---|
| Esquerdo | 82 | 2,5 mm |
| Direito | 86 | 13,7 mm no repouso / 12,1 mm na pose (a mão direita precisou de mais passos; nos renders não aparece deformação) |

**Testes, com o mesmo método de sempre (pares reais / profundidade máxima):**

| Pose | Esquerda antes → depois | Direita antes → depois |
|---|---|---|
| Mão fechada a 70° | 6 · 3,4 mm → **0** | 7 · 4,1 mm → **0** |
| Fechar a 30, 40, 50 e 60° | 0 → 0 | 0 → 0 |
| Repouso, punho, cotovelo 90°/100° | 0 → 0 | 0 → 0 |
| Mão aberta / polegar / alternados / palma | sem mudança (1–2 pares, ≤2,9 mm) | sem mudança (1–8 pares, ≤2,9 mm) |
| Cotovelo 90° + punho 45° + mão fechada | 209 · 15,8 mm → **13 · 4,8 mm** | 100 · 16,0 mm → **0** |

**Correção de um erro meu no teste da pose combinada:**
- Os números "209 e 100 cruzamentos" do relatório anterior estavam errados por causa do teste.
- O problema: com o punho dobrado, os dedos fechavam girando em torno do eixo da palma em repouso, e não da palma já dobrada.
- Com o eixo certo e ainda sem a forma corretiva, a pose dá 19 pares (4,8 mm) na esquerda e 6 (2,0 mm) na direita.
- Ou seja, aquilo não era o "antebraço curto"; a maior parte era defeito do teste.
- As outras poses não mudam, porque o punho fica parado nelas.

**Polegar por cima dos dedos: não deu certo.**
- A mão fechada com o polegar ao lado dos dedos continua funcionando.
- O polegar mede 0,05 m. Com a mão fechada, a segunda falange dos dedos fica a pelo menos 0,079 m da base do polegar, então ele não alcança.
- O máximo que ele faz é encostar na primeira falange do indicador, e aí afunda 8 a 14 mm.
- A tentativa de corrigir isso com uma forma divergiu: chegou a 19 mm e 380 pares (`busca_polegar.json` e `busca_polegar2.json`).
- Para o polegar dobrar por cima, ele precisaria ser mais comprido ou mais fino. Isso muda o estilo, então depende de você.

**Exportação:**
- O driver não vai para o motor de jogo como driver: o valor da forma é gravado quadro a quadro na animação (canal `weights` do glTF e animação de shape key no FBX). Na reimportação, os valores conferem com o Blender (1,0 / 0,267 / 0).
- Em jogo, quem anima a mão grava esse valor junto, ou um script liga o valor ao ângulo dos dedos.

## 3. Contorno

**a) Lascas entre os dedos:**
- O contorno agora afina onde há outra superfície logo à frente: a fenda entre os dedos, ou a ponta dos dedos contra a palma.
- Isso foi medido no repouso e nas poses da mão.
- 373 vértices da mão afinaram. Na média, a casca da mão ficou com 66% da espessura, e o mínimo é 12%.
- **Resultado:** as lascas sumiram no repouso e com a mão aberta. Na mão fechada, vista de costas, ainda sobram algumas linhas finas na base dos dedos (`contorno_esq.png` e `contorno_dir.png`).

**b) Contorno em jogo (`Kumo_Contorno`):**
- É uma malha própria: a casca invertida do Solidify, com as faces viradas.
- Usa os mesmos pesos (até 4 ossos, soma 1), as mesmas shape keys e um material de cor única com backface culling.
- Funciona em qualquer motor sem shader especial. O corpo é exportado sem o Solidify.

| Teste | Resultado |
|---|---|
| Contorno de jogo contra o Solidify do Blender, em repouso | 0,014 mm |
| O mesmo, na mão fechada e na mão aberta | 99% dos pontos a menos de 2,8 mm |
| O mesmo, na pose combinada | 99% a menos de 7,2 mm (em pose, o Solidify recalcula as normais e a malha de jogo gira as normais de repouso, como qualquer motor) |
| Visual (`contorno_corpo.png`) | o contorno de jogo fica igual ao do Blender |

**Observação sobre os renders:** o Cycles não respeita o backface culling, então os renders do contorno de jogo usam o material de contorno do Blender, que imita o culling. O que vai exportado é `Kumo_Contorno_Jogo`.

## 4. Arquivos exportados para jogo (`kumo_v6_maos_jogo.glb` e `.fbx`)

| Teste | GLB | FBX |
|---|---|---|
| Malhas | Kumo + Kumo_Contorno | Kumo + Kumo_Contorno |
| Influências por vértice | no máximo 4; soma 1 | no máximo 4; soma 1 |
| Shape keys | as 2 corretivas, nas duas malhas | as 2 corretivas, nas duas malhas |
| Deformação contra o Blender (5 quadros de teste) | até 0,06 mm (corpo) e 0,08 mm (contorno) | até 0,06 mm e 0,08 mm |
| Tamanho | 4,4 MB | 1,8 MB |

A diferença subiu de 0,003 para 0,06 mm por causa das shape keys exportadas. Nessa escala, não aparece.

O "Icosphere" que aparece ao reimportar o GLB não faz parte do arquivo: o importador do Blender cria essa esfera só para desenhar os ossos.

**Desempenho:** 0,40 ms por atualização, com os drivers ligados.

## Ainda em aberto

- O polegar não dobra por cima dos dedos (veja acima). Para isso, seria preciso mudar o comprimento ou a grossura do polegar, o que depende de você.
- Mão aberta, polegar isolado e dedos alternados mantêm pequenos contatos (≤2,9 mm). Corrigir isso pediria uma forma corretiva para cada pose.
- A pose combinada, na mão esquerda, ainda tem 13 pares (4,8 mm).
- Na mão fechada vista de costas, ainda sobram algumas linhas do contorno.
- A mão continua com cor única, sem as manchas.
- Os olhos da v5 ficam para o P2.

## Arquivos

- `kumo_maos_corretivas.blend`: só as formas corretivas.
- `kumo_v6_maos_jogo.blend`, `.glb` e `.fbx`: formas corretivas + contorno afinado + `Kumo_Contorno`.
- `comparacao_mao_fechada.png` e `comparacao_fechar_50.png`: com e sem a forma corretiva.
- `contorno_esq.png`, `contorno_dir.png` e `contorno_corpo.png`: contorno antes, depois e de jogo.
- `medicoes.json`, `medicoes_contorno.json`, `fbx_reimportado.json`, `busca_polegar*.json` e `renders/`.
- `src/`:
  - `kumo_lib.py`: teste e poses;
  - `verifica_fbx.py`;
  - `busca_polegar*.py`;
  - `corretivas.py`;
  - `contorno_jogo.py`.

Para refazer: `python src/corretivas.py <kumo_maos_dedos.blend> <saída>` e depois `python src/contorno_jogo.py <saída>/kumo_maos_corretivas.blend <saída2>`.
