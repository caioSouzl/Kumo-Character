# Kumo 3D — comparação de soluções, arquitetura recomendada e plano

**Data:** 2026-11-11 · **Estado:** **proposta para aprovação.** Nada aqui foi implementado, e nenhum modelo foi alterado.

Base: [`01-DIAGNOSTICO.md`](01-DIAGNOSTICO.md) (problemas C1–C5, A1–A6, M1–M5) e [`02-PESQUISA.md`](02-PESQUISA.md).

## 1. A conclusão que orienta tudo

Os problemas que vínhamos atacando um a um têm **a mesma causa: a malha base**. Ela é uma retopologia automática de um modelo gerado por IA, com estas características:

- não tem anéis de arestas nas articulações, nos olhos e na boca;
- é assimétrica;
- tem os olhos e a boca pintados, sem geometria;
- perdeu as facetas e a crista dorsal da referência.

O sistema ocular das versões v1 a v5 existe para contornar uma restrição que nós mesmos fixamos: não tocar na malha da cabeça. Com essa restrição, ele chegou perto do limite do possível. Sem ela, quase toda a sua complexidade deixa de ser necessária.

**Recomendação central:** construir uma **nova malha de animação do Kumo** numa área independente. A forma aprovada (o modelo atual) serve de autoridade de volume, e a referência original serve de autoridade de identidade. O modelo oficial atual fica intacto até a nova versão ser aprovada.

## 2. Comparação das soluções possíveis

### 2.1 Malha base

| Opção | O que é | Vantagens | Limitações | Veredito |
|---|---|---|---|---|
| **M-A. Manter a malha atual e remendar** | Continuar como hoje | Nenhuma mudança no modelo aprovado | C2 a C5 e A1 continuam sem solução; cada novo recurso exige um contorno | ❌ Não sustenta os objetivos |
| **M-B. Retopologia nova sobre a forma atual** | Malha nova, com anéis anatômicos, projetada sobre a superfície aprovada; textura transferida | Mantém volume e silhueta; resolve articulações, dedos, olhos e boca; permite facetas | Trabalho grande; a retopologia é feita por scripts (sem artista interativo), então precisa de protótipo | ✅ **Recomendada** |
| M-C. Cirurgia local na malha atual | Inserir anéis só nas articulações e refazer mãos e rosto | Menos trabalho inicial | Mistura duas topologias; UV fragmentado continua; a assimetria continua | 🟡 Plano B se a M-B falhar no protótipo |
| M-D. Voltar ao modelo procedural arquivado | `kumo-3d-toon` | Cabeça facetada mais fiel (F1.2) | Você encerrou essa linha; o corpo era mais simples | 🟡 Só como fonte de consulta para as facetas |

### 2.2 Sistema ocular

| Opção | O que é | Vantagens | Limitações | Veredito |
|---|---|---|---|---|
| **O-A. Manter a v5 (camadas + vínculo por nós)** | 12 cascas, borda em shader, relevo por nós | Olho aberto fiel; já existe; visual limpo | 3,5× o custo do rig; não exporta; contato na dobra não zera; pálpebra sem volume real | 🟡 **Fica como solução provisória** na malha atual |
| **O-B. Pálpebras reais na malha + superfície do olho com íris projetada** | Órbita e pálpebras com anéis concêntricos na cabeça nova; pálpebras movidas por ossos em arco (padrão Blender Studio e Rigify); íris, pupila e brilho num único material que segue o osso do olho | Pálpebra tem volume e deforma com a pele por construção; uma superfície por olho em vez de seis; exporta como ossos e shape keys; mantém o que a v1–v5 provou | Exige a malha nova (M-B); o olho aberto precisa ser revalidado contra a referência | ✅ **Recomendada** |
| O-C. Globo esférico real + Lattice | Esfera que gira, achatada por Lattice | Rotação limpa; olhar amplo | Lattice não exporta; mais uma camada de deformação | 🟡 Reserva, se a O-B limitar o olhar |
| O-D. Só Geometry Nodes | Pálpebras geradas por nós | Paramétrico | Mesmos custos da O-A | ❌ |

**O que as versões v1–v5 ensinaram e será mantido:**

1. Íris, pupila e brilho como projeção que segue o osso do olho: zero penetração e olho aberto fiel.
2. A borda da pálpebra percorre um arco de rotação em torno do centro do globo.
3. As pálpebras precisam herdar a deformação da pele. Na malha nova isso vem de graça, porque elas fazem parte da pele.
4. As camadas precisam de ordem única. Com uma superfície por olho, o problema desaparece.
5. Triangulação e normais devem ser lidas do mesmo jeito que o render.

### 2.3 Rig

| Opção | Vantagens | Limitações | Veredito |
|---|---|---|---|
| R-A. Rig atual feito por script | Já existe | Só FK; sem controles | ❌ |
| **R-B. Rigify** | Oficial, embutido no 5.2.3; IK/FK, controles, dedos, cauda, olhos (`face.skin_eye`), mandíbula; regenerável | A geração sem interface precisa de protótipo | ✅ **Recomendada** |
| R-C. CloudRig | Padrão do Blender Studio; mais recursos | Instalação externa | 🟡 Evolução futura |

## 3. Arquitetura recomendada ("Kumo v6")

Respostas às dez perguntas do briefing:

| # | Pergunta | Decisão |
|---|---|---|
| 1 | O que faz parte da malha principal? | Cabeça com órbitas, **pálpebras** e linha da boca; tronco; braços; mãos com 3 dedos + polegar; pernas; pés; cauda; crista do topo e dorsal |
| 2 | O que é objeto independente? | **Uma superfície por olho** (esclera, íris, pupila e brilho num material). O contorno continua sendo modificador da malha principal. |
| 3 | O que usa modificadores? | Armadura (deformação); contorno *inverted hull* (o já aprovado); triangulação só na exportação. Suavização corretiva é opcional e só para render no Blender. |
| 4 | O que usa Geometry Nodes? | **Nada na cadeia de deformação do personagem.** Os nós ficam para ferramentas de construção e teste. Motivos: custo de 3,5×, não exportam, e a API mudou na série 5.x. |
| 5 | O que usa ossos? | Corpo inteiro (Rigify: coluna, cabeça, braços e pernas com IK/FK, dedos, cauda); olhos (um osso por olho + alvo de olhar); pálpebras (cadeias superior e inferior); mandíbula |
| 6 | O que usa shape keys? | Forma exata do olho fechado; expressões (sorriso, tristeza, surpresa); corretivas de cotovelo, joelho e ombro **somente onde os testes mostrarem necessidade** |
| 7 | Deformadores auxiliares? | Nenhum por padrão. Lattice só se a opção O-C for necessária. |
| 8 | Como organizar dependências? | Um só sentido: controles → ossos de mecanismo → ossos de deformação → malha. Drivers só leem propriedades de controle. |
| 9 | Como evitar conflitos? | Um único sistema de deformação por região; nomes padronizados (`DEF-`, `MCH-`, controles); coleções de ossos; testes automáticos a cada mudança |
| 10 | Como manter editável? | Tudo gerado por scripts a partir de uma especificação (metarig + configuração), regenerável a qualquer momento; documentação por componente |

**Sombreamento e identidade:**
- Arestas vivas explícitas nas fronteiras das facetas da cabeça.
- Textura transferida para um UV novo, com poucas costuras, o que permite pintura localizada.
- Cores conferidas contra a paleta da referência por teste automático.

**Pesos:** no máximo 4 influências por vértice e soma igual a 1, verificados por teste.

## 4. Sistema de validação automática

| Teste | Método | Situação |
|---|---|---|
| Integridade da malha | Não-manifold, degeneradas, duplicados, normais, volume | ✅ Existe (`src/auditoria_modelo.py`) |
| Autointerseção em repouso e em pose | Pares de triângulos que se cruzam | ✅ Existe |
| Articulações (24 poses) | Autointerseção nova, volume, esticamento e compressão de arestas, render de evidência | ✅ Existe |
| Simetria | Distância ao vértice espelhado | ✅ Existe |
| Pesos | Influências por vértice, soma, ossos sem vértices | ✅ Existe |
| UV e textura | Costuras, cobertura, densidade de texel | ✅ Existe |
| Desempenho | Milissegundos por atualização | ✅ Existe |
| Olhos: penetração por pontos e por triângulos, ordem das camadas | Herdado de `olhos-v5/src/validate_eyes.py` | ✅ Existe, a unificar |
| Silhueta | IoU contra o modelo aprovado, 4 vistas | ✅ Existe, a unificar |
| Proporção | Altura em cabeças (alvo 3,5), largura da cabeça, posição dos olhos | 🔲 A criar |
| Identidade | Sobreposição com a referência por vista; paleta | 🔲 A criar |
| Expressões do rosto | Cada shape key e combinação: interseção e render | 🔲 A criar |
| Animação contínua | Ciclos de caminhada e corrida amostrados quadro a quadro | 🔲 A criar |
| Exportação | glTF e FBX reimportados e comparados | 🔲 A criar |

Cada teste grava estado inicial, estado final, método, resultado, limitações e evidência visual, como já faz o JSON desta auditoria. A proposta é reunir tudo numa pasta única de testes, com um comando que roda a bateria inteira.

## 5. Plano por etapas

Cada fase termina com uma entrega para sua avaliação. Nenhuma fase começa sem a aprovação da anterior.

| Fase | Conteúdo | Entrega |
|---|---|---|
| 1. Auditoria | Concluída | Estes documentos |
| 2. Pesquisa | Concluída (com as lacunas declaradas) | `02-PESQUISA.md` |
| 3. Projeto técnico | Este documento | Aguardando sua decisão |
| **4. Protótipos** | **P1:** retopologia de um braço com mão e dedos sobre a forma atual, medida com as mesmas poses da auditoria. **P2:** cabeça com órbita, pálpebras reais e superfície de olho única, com piscada, olhar e rotação. **P3:** geração de rig Rigify sem interface, a partir de metarig ajustado. **P4:** facetas com arestas vivas contra a referência. **P5:** transferência de textura para UV novo. | Pranchas e métricas de cada protótipo, lado a lado com o atual |
| 5. Implementação | Malha completa, rig, olhos, materiais, na área `v6-dev/` | Versões numeradas |
| 6. Validação | Bateria completa de testes | Relatório |
| 7. Otimização | Desempenho, limpeza de dados órfãos, organização de coleções | Relatório |
| 8. Documentação | Manual de uso do rig e de manutenção | Documentos |

## 6. Complexidade e riscos

| Item | Complexidade | Risco principal | Mitigação |
|---|---|---|---|
| Retopologia por script (M-B) | **Alta** | Sem artista interativo, a qualidade dos anéis depende de algoritmo | Protótipo P1 antes de assumir; plano B é a cirurgia local (M-C) |
| Cabeça com órbitas e pálpebras | **Alta** | Mudar a aparência do olho aberto | P2 medido contra a referência e contra a v5; sem aprovação, a v5 continua |
| Simetria | Média | A forma atual é assimétrica; simetrizar muda a silhueta | Decisão sua, região por região |
| Facetas e crista dorsal | Média | Interpretar a referência além do que ela mostra | Protótipo P4 com sobreposição; usar a cabeça F1.2 arquivada como consulta |
| Rigify sem interface | Média | A ativação emitiu erro de preferências no teste | P3; se falhar, rig próprio com a mesma estrutura de controles |
| Transferência de textura | Média | Perda de nitidez no rebake | P5 com comparação de pixels |
| Prazo | — | Cada ciclo de construção e validação leva de 1 a 2 horas de máquina | Protótipos pequenos e isolados |

## 7. Alterações que exigem sua autorização

1. Criar a área de desenvolvimento `kumo-3d-rodin/v6-dev/` (só arquivos novos).
2. Construir uma **malha nova** em paralelo. Isso não altera o modelo oficial, mas muda a estratégia.
3. Abrir **órbitas e criar pálpebras** na cabeça nova (reverte a decisão "não modificar a cabeça", só na versão nova).
4. **Simetrizar** olhos, braços ou a cabeça inteira.
5. **Restaurar a crista dorsal** e as facetas conforme a referência.
6. Dar **geometria à boca** e criar mandíbula.
7. **Substituir o rig** por um rig gerado (Rigify).
8. **Refazer o UV** e reassar a textura.
9. Ajustar **cores** em direção à paleta da referência.
10. Apagar dados órfãos e reorganizar versões antigas. Nada será apagado sem pedido seu.

## 8. Decisões que preciso de você para começar a Fase 4

1. **Destino do Kumo:** animação renderizada no Blender, motor de jogo, ou os dois? Isso define se a exportação é requisito.
2. **Estratégia:** autoriza a malha nova em paralelo (M-B), mantendo o modelo atual intacto?
3. **Simetria:** os olhos e o corpo devem ficar simétricos como na referência?
4. **Boca:** o Kumo vai falar ou mudar a expressão da boca?
5. **Por onde começar:** recomendo os protótipos P1 (braço e mão) e P2 (cabeça e olhos), porque são os dois maiores riscos.
