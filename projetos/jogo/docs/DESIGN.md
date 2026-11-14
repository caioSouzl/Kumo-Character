# Kumo Pizzaria: documento de design

Jogo de gerenciamento de pizzaria para lives interativas. O Kumo administra a
pizzaria por um expediente de 5 minutos, e os espectadores ajudam ou sabotam
com presentes da live.

## Decisões fechadas

| Tema | Decisão |
|---|---|
| Engine | Godot 4 (Android e PC) |
| Câmera | 2.5D, fixa, tela vertical 9:16 (1080 x 1920) |
| Movimento do Kumo | Automático; os presentes mudam o comportamento dele |
| Sabotagens | Cada uma tem efeito próprio; nem toda sabotagem faz perder o pedido |
| Presentes | Configuráveis em `config/gifts.json`, sem lista fixa no código |
| Live | Primeiro com o simulador; a live real entra por um conector separado |

## Ciclo

1. **Expediente (5 min).** O cliente entra, vai para a fila do balcão de pedidos e
   mostra de 1 a 3 pizzas no balão. O Kumo anota o pedido, prepara as pizzas,
   assa no forno, leva ao balcão de entrega e recebe o pagamento.
2. **Intervalo (20 s).** Resumo: clientes atendidos, pizzas produzidas, pedidos
   perdidos, pizzas roubadas, vendas, gorjetas e saldo acumulado. O Kumo
   comemora ou se desespera conforme o resultado.

## Fila de eventos

- A ordem de chegada dos presentes é respeitada.
- No máximo um evento a cada 3 s (`event_min_interval_sec`).
- Esses 3 s são o intervalo mínimo entre despachos. Um evento com animação longa
  (`"blocking": true`, por exemplo a capivara) segura a fila até terminar, para a
  animação não ser cortada. `max_block_sec` é a trava de segurança.
- Presentes agrupáveis (`"groupable": true`, como a Rosa) que chegam em sequência
  viram uma única animação, sem perder a quantidade contada.
- Durante o intervalo a fila espera; nada se perde.

## Eventos do MVP

| Presente | Categoria | Evento | Efeito |
|---|---|---|---|
| Rosa | Gorjeta | `tip` | Soma gorjeta ao caixa. O Kumo comemora. |
| Heart Me | Ajuda | `speed_boost` | O Kumo fica mais rápido por um tempo (acumula). |
| Capivara | Sabotagem | `capybara_raid` | A capivara persegue o Kumo e come uma pizza. O Kumo entra em pânico e precisa refazer a pizza, mas o pedido continua. |
| Rosquinha (exemplo) | Sabotagem | `impatience` | Todos os clientes perdem paciência. |

Para adicionar um presente, crie uma entrada em `config/gifts.json` apontando
para um desses eventos. Um evento novo precisa de um `case` em
`_on_event_started()` (`scripts/main.gd`).

## Clientes

- **Comum:** paciência maior.
- **Impaciente:** paciência menor, marcado com "!".
- A paciência cai pela metade da velocidade enquanto o pedido está sendo feito
  (`patience_while_cooking_mult`).
- Se a paciência acaba, o cliente vai embora bravo e o pedido conta como perdido.

## Dinheiro

- Vendas (pizzas entregues) e gorjetas (Rosas) ficam separadas no resumo.
- As duas vão para o saldo, salvo em `user://kumo_save.json` entre as lives.

## Próximos passos

1. Trocar a arte provisória pelos sprites do Kumo (`referencia de modelo/`).
2. Loja de melhorias no intervalo (forno, velocidade de preparo, decoração,
   proteção contra capivara), paga com o saldo.
3. Conectar a live real: uma ponte local que transforma os presentes em
   mensagens WebSocket (`live_connector` em `config/game.json`).
4. Sons e música.
5. Exportar para Android.
