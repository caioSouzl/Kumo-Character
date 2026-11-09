# Especificação oficial — Kumo 3D (2,5D cel-shaded)

Este é o registro dos elementos **aprovados**. Um item só entra aqui depois de aprovado. Para mudar um item já aprovado, é preciso primeiro apresentar a divergência e pedir aprovação; nada aqui é substituído direto.

## Fonte da verdade

| Item | Valor | Aprovado em |
|---|---|---|
| Referências oficiais | `referencia de modelo/kumo-referencia-01.png` (vistas de rotação) e `kumo-referencia-02.png` (detalhes) | 2026-11-08 (fornecidas pelo dono) |
| Técnica | Modelo 3D com cel-shading / toon shading (2,5D), para animação 3D e 2D | 2026-11-09 (pedido do dono) |
| Arquivo base | `kumo-3d-toon/base/kumo_toon_base_v1.blend` + `base/kumo_toon_base_v1.py`, congelados | 2026-11-09 ("mantenha esse arquivo base") |

## Elementos em avaliação (ainda não aprovados)

Os itens abaixo existem na base v1, mas ainda não foram aprovados individualmente. O diagnóstico de cada um está em [`DIAGNOSTICO-001.md`](DIAGNOSTICO-001.md).

| Elemento | Estado na base v1 | Pendência |
|---|---|---|
| Proporções (cabeça 1,00 H · tronco 0,59 H · pernas 0,37 H · total 1,96 H) | medidas na referência 01 | aprovação |
| Cabeça poliédrica | 57 faces, 29 visíveis de frente | P1 |
| Crista | decalques projetados | P2 |
| Ombro e nuca da cabeça | desvios S1 e S2 | P3 |
| Olhos | sobressaem no perfil (S3) | P4 |
| Mãos (3 dedos + polegar) | posição baixa (S4) | P5 |
| Pés (3 dedos) | calcanhar curto (S5) | P6 |
| Cauda em espiral | menor e mais baixa (S6), lado nas costas (D2) | P7, P9 |
| Câmera 3/4 | 45° | P8 (D1) |
| Paleta | `#1B5E3B` `#4CAF6B` `#C9D45B` `#EAD9B7` `#F4B642` `#5B3A2E` (da referência) | aprovação |
| Shader toon | 4 faixas chapadas, luz fixa (−0,55, −0,62, 0,58) | aprovação |
| Contorno | Freestyle `#5B3A2E`, espessura 3,0 | aprovação |
| Expressões (8) | pupilas, pálpebras planas, sobrancelhas, bocas | aprovação, P10 |

## Histórico de decisões

| Data | Decisão |
|---|---|
| 2026-11-09 | Base v1 congelada como ponto de partida para alterações futuras. |
| 2026-11-09 | Protocolo de trabalho: inspecionar → diagnosticar → propor → só alterar com autorização → render ortográfica e relatório após cada alteração. |
