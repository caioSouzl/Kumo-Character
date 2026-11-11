# Kumo v6: tabela de amplitudes articulares

**Data:** 2026-11-11 · **Situação:** proposta para a sua aprovação, antes do rig (P3). Nenhum limite foi aplicado a rig nenhum.

## Como a tabela foi feita

1. **Ações do Kumo:** a lista de ações previstas vem da auditoria (`../auditoria/01-DIAGNOSTICO.md`, seção D): andar, correr, virar e baixar a cabeça, inclinar o corpo, mover os braços, manipular objetos e mexer os dedos, expressar emoções, mover a cauda, movimentos rápidos e lentos.
2. **Três faixas por movimento:**
   - **Necessária:** o mínimo para executar as ações da lista. O rig tem que fazer isso limpo (sem cruzamentos, com volume e silhueta).
   - **Desejável:** dá margem de atuação e exagero cartoon. Deve funcionar, aceitando pequenas perdas.
   - **Extrema:** só para poses especiais. Não é requisito; se uma animação precisar, estudamos uma solução específica (decisão sua de 2026-11-11).
3. **Proporções do Kumo:** medidas no próprio modelo com `amplitudes/alcance.py` (resultado em `amplitudes/alcance.json`). A cabeça enorme e os braços curtos mudam o que faz sentido:

   | Alvo da mão | Distância do ombro | Alcançável? | Flexão do cotovelo necessária |
   |---|---|---|---|
   | Peito (frente, centro) | 0,37 m | sim | cerca de 49° |
   | Quadril esquerdo (mão na cintura) | 0,30 m | sim | cerca de **93°** |
   | Barriga (frente, centro) | 0,42 m | no limite, com flexão do ombro | — |
   | Ombro oposto | 0,46 m | não | — |
   | Boca ou focinho | 0,87 m | **não** | — |
   | Bochecha | 0,60 m | **não** | — |
   | Topo da cabeça | 1,24 m | **não** | — |

   O braço inteiro, com a mão, mede cerca de 0,49 m. **O Kumo não alcança o próprio rosto.** Gestos como levar a mão à boca ou coçar a cabeça, que exigem 130° ou mais de cotovelo num humano, não existem para ele com estas proporções.
4. **Valores humanos de referência:** amplitudes normais (AAOS) e funcionais do cotovelo e do punho (Morrey et al., 1981; Palmer et al., 1985), e ângulos da marcha e da corrida (Perry e Burnfield; Novacheck, 1998). **Cito esses números de memória e não conferi as fontes primárias nesta sessão.** Eles servem só de ponto de partida; o que manda é a coluna "ações que justificam".

Os ângulos estão em graus, a partir da pose de repouso (pose A).

## Membros superiores

| Articulação · movimento | Necessária | Desejável | Extrema | Ações que justificam |
|---|---|---|---|---|
| **Ombro** · flexão (braço à frente) | 0–90 | 0–135 | 180 | Balanço ao andar (cerca de 30), correr (cerca de 60), pegar objeto à frente (90); apontar alto e acenar (135) |
| Ombro · extensão (para trás) | 0–30 | 0–45 | 60 | Balanço ao andar e correr |
| Ombro · abdução (abrir para o lado) | 0–90 | 0–150 | 180 | Equilíbrio, gestos; acenar e comemorar com os braços para cima (150). Mesmo a 180° a mão não passa da altura do topo da cabeça. |
| Ombro · torção | ±45 | ±70 | ±90 | Orientar a mão para pegar objetos |
| **Cotovelo** · flexão | **0–100** | **0–115** | 130–145 | Mão na cintura (93° medidos), braço da corrida (cerca de 90), segurar objeto junto ao peito. **Nenhum alvo alcançável do próprio corpo exige mais de 115°.** |
| Cotovelo · hiperextensão | 0 | 5 | 10 | Exagero cartoon pontual |
| **Antebraço** · torção | ±60 | ±80 | ±90 | Girar a mão: maçaneta, mostrar a palma |
| **Punho** · flexão/extensão | ±45 | ±60 | ±80 | Apoiar a mão, gesticular, segurar |
| Punho · desvio lateral | ±20 | ±30 | ±40 | Acenar, ajuste fino de pegada |
| **Metacarpo** (curvar a palma) | 0–15 | 0–25 | 30 | Mão fechada, segurar objetos redondos |
| **Dedos** · base, flexão | 0–70 | 0–90 | 100 | Mão fechada (o teste usa 70) |
| Dedos · base, hiperextensão | 0 | 15 | 25 | Mão aberta expressiva, espanto |
| Dedos · base, abertura lateral | ±10 | ±15 | ±25 | Mão aberta (o teste usa 15) |
| Dedos · junta, flexão | 0–70 | 0–90 | 100 | Mão fechada, segurar |
| **Polegar** · base, oposição/flexão | 0–35 | 0–50 | 70 | Pinça com os dedos, mão fechada |
| Polegar · base, abertura | 0–20 | 0–35 | 50 | Mão aberta, "joinha" |
| Polegar · junta | 0–45 | 0–70 | 90 | Pinça, mão fechada |

## Membros inferiores

| Articulação · movimento | Necessária | Desejável | Extrema | Ações que justificam |
|---|---|---|---|---|
| **Quadril** · flexão (coxa à frente) | 0–35 | 0–90 | 120 | Andar (cerca de 30); correr, subir degrau e **sentar** (90); agachar fundo (120) |
| Quadril · extensão | 0–15 | 0–25 | 35 | Final da passada, correr |
| Quadril · abdução | 0–20 | 0–45 | 60 | Passo lateral, base larga, equilíbrio |
| Quadril · torção | ±15 | ±35 | ±45 | Virar o corpo andando, pé para fora |
| **Joelho** · flexão | 0–65 | 0–100 | 120–135 | Andar (cerca de 60), correr e sentar (90 a 100); agachar (extremo) |
| **Tornozelo** · dorsiflexão (ponta para cima) | 0–10 | 0–20 | 30 | Andar, subir rampa |
| Tornozelo · flexão plantar | 0–20 | 0–40 | 50 | Impulso da passada, ficar na ponta dos pés, pular |
| Tornozelo · inversão/eversão | ±10 | ±15 | ±25 | Chão irregular |
| **Dedos do pé** · extensão | 0–30 | 0–45 | 60 | Rolamento do pé no fim da passada. Hoje o pé é um bloco (auditoria, Baixos); precisa de articulação ou de osso de rolamento. |

## Tronco, pescoço, cabeça e cauda

| Articulação · movimento | Necessária | Desejável | Extrema | Ações que justificam |
|---|---|---|---|---|
| **Coluna** · flexão (curvar à frente) | 0–30 | 0–45 | 60 | Inclinar, olhar para baixo, pegar algo |
| Coluna · extensão | 0–15 | 0–30 | 40 | Espreguiçar, surpresa |
| Coluna · inclinação lateral | ±15 | ±30 | ±40 | Peso de um lado, curiosidade |
| Coluna · torção | ±20 | ±45 | ±60 | Contrarrotação ao andar (cerca de 10), olhar para trás |
| **Pescoço + cabeça** · virar | ±45 | ±70 | ±90 | Olhar em volta. Na auditoria, 70° no modelo atual já dá 9 pares. |
| Pescoço + cabeça · baixar | 0–20 | 0–30 | 45 | Olhar para baixo. O queixo bate no peito cedo (auditoria: 43 pares a 30° no modelo atual), então a cabeça deve girar no próprio pivô, e não dobrar o pescoço. |
| Pescoço + cabeça · erguer | 0–20 | 0–40 | 60 | Olhar para cima |
| Pescoço + cabeça · inclinar de lado | ±15 | ±30 | ±40 | Curiosidade: gesto essencial em cartoon |
| **Cauda** · abanar (lateral, distribuído) | ±30 no total | ±60 | ±90 | Equilíbrio na corrida, emoção |
| Cauda · enrolar/desenrolar | ±10 por segmento | ±20 por segmento | desenrolar toda | Emoção: enrolar mais = encolhido; desenrolar = alerta. Desenrolar a espiral inteira é decisão de design. |
| Cauda · erguer/baixar (base) | ±15 | ±30 | ±45 | Postura, emoção |
| **Olhos** (para o P2) | ±25 horizontal, ±15 vertical | ±35 / ±20 | ±45 / ±30 | Olhar sem virar a cabeça. O v5 alcançava só ±11. |

Fora da tabela, para o P2: mandíbula e boca (fala), pálpebras e sobrancelhas. Dependem de definir como o Kumo fala, o que ainda está em aberto.

## Cotovelo: conclusão

- **Necessária: 0–100°.** O valor que a medição exige é 93° (mão na cintura); 100° dá margem.
- **Desejável: até 115°.**
- **130° deixa de ser critério.** Não há alvo alcançável que exija esse ângulo; fica registrado como extremo.

Resultado do P1 iteração 5 (`p1-iter5/RELATORIO.md`) dentro dessas faixas:
- **até 100°:** zero cruzamentos (o atual tem 29 reais a 100°);
- **a 115°:** há contato antebraço–bíceps (65 pares reais contra 46 do atual), mas com área 2,5 vezes menor e profundidade 2,2 vezes menor. É limitação documentada da faixa desejável.
