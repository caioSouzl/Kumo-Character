# Kumo v6 — decisões e regras do desenvolvimento paralelo

**Data:** 2026-11-11 · Área de desenvolvimento independente. **O modelo oficial (`../kumo_rigged.blend`) e as versões `olhos-v1`…`v5` não são alterados.** Nenhuma substituição e nenhuma reconstrução completa antes da aprovação dos protótipos.

## Decisões do Caio

| # | Decisão |
|---|---|
| D1 | Construção paralela autorizada, condicionada à aprovação dos protótipos |
| D2 | **Destino: ambos, Blender primeiro.** Produção no Blender; exportação para Unity, Unreal ou Godot garantida |
| D3 | Fidelidade: recuperar a cabeça facetada, as cristas, os **olhos simétricos**, os dedos e as proporções da referência |
| D4 | O aprendizado das versões olhos-v1…v5 deve ser aproveitado, mesmo que a implementação mude |
| D5 | Cada etapa deve trazer imagens comparativas (com a referência e com o modelo atual), testes de deformação e medições de desempenho |

## Regras técnicas que decorrem do destino (D2)

1. A deformação do personagem usa **somente ossos e shape keys**. Lattice, Geometry Nodes, Surface Deform e suavização corretiva ficam fora da cadeia de deformação.
2. No máximo **4 influências** por vértice, com soma de pesos igual a 1 (verificado por teste).
3. Materiais com um equivalente simples em motor de jogo. O contorno *inverted hull* continua; no motor ele vira shader de contorno.
4. Exportação para glTF e FBX reimportada e comparada é um teste obrigatório.

## Critérios de aprovação de cada protótipo

- Comparação visual com a referência (vistas da prancha) e com o modelo atual.
- Mesmas poses de articulação da auditoria, medidas com o mesmo método.
- Desempenho medido (milissegundos por atualização).
- Itens ainda em aberto declarados como tal.

## Autorizações de 2026-11-11 (2ª sessão)

| # | Decisão |
|---|---|
| D6 | "Autorizo todas as reclamações": shape key corretiva da mão fechada, solução do contorno em jogo e início do P2 (cabeça, olhos e boca). Trabalho em `maos-corretivas/`. |
| D7 | (2026-11-12) "P2 ficou uma aberração, delete isso e tento com a versão fiel ao projeto": a tentativa com a cabeça F1.2 foi apagada; o P2 segue em `p2-fiel/`, sobre a cabeça atual do Kumo. |
| D8 | (2026-11-12) **Regra permanente do Caio: "Não quero mais mudanças na aparência do Kumo… o Kumo deve manter a aparência."** O P2 fiel (olhos novos) foi reprovado no visual. Daqui em diante, só entram mudanças que não alterem a aparência (pesos, rig, ossos, exportação, testes). Qualquer coisa que mude forma, cor, olhos, boca ou mãos precisa de pedido explícito. |
