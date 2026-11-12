# Kumo-Character

<img width="1312" height="1199" alt="file_000000005708820e944c37cf94f69d20" src="https://github.com/user-attachments/assets/d0f51b6e-f96f-42a9-aa88-fb9f1811f2f7" />

<img width="1312" height="1199" alt="file_00000000a470820e827afdd644f82450" src="https://github.com/user-attachments/assets/7001e626-60af-4257-b32f-7f6addd025f1" />

## Kumo Pizzaria (protótipo)

Jogo para lives: o Kumo cuida de uma pizzaria por 5 minutos e os espectadores
ajudam ou atrapalham com presentes. Design completo em [`docs/DESIGN.md`](docs/DESIGN.md).

### Como rodar

1. Instale o [Godot 4.4](https://godotengine.org/download) (ou mais novo).
2. No Godot, clique em **Importar** e escolha o `project.godot` desta pasta.
3. Aperte **F5**.

A tela é vertical (9:16). A arte ainda é provisória, desenhada em código.

### Testar os presentes sem live

| Tecla | Presente |
|---|---|
| `1` | Capivara |
| `2` | Rosquinha (exemplo) |
| `3` | Heart Me |
| `4` | Rosa |
| `Shift` + número | o mesmo presente x10 |
| `F1` ou botão **SIM** | mostra/esconde o painel do simulador |

As teclas seguem a ordem alfabética dos ids em `config/gifts.json`. Esconda o
painel antes de transmitir.

### Mudar regras e presentes

- `config/game.json`: duração do expediente e do intervalo, intervalo entre
  eventos, tempos de preparo, preço, clientes e paciência.
- `config/gifts.json`: qual presente dispara qual evento, e com que força.
  `tiktok_names` são os nomes que o conector da live envia.

### Ligar a live

O TikTok não tem API pública oficial para presentes em tempo real. O jogo
escuta um WebSocket local e espera mensagens assim:

```json
{"gift": "Rose", "user": "fulano", "count": 5}
```

Qualquer ponte (por exemplo uma baseada em `tiktok-live-connector`) que envie
esse formato funciona. Ative em `config/game.json` → `live_connector.enabled`.

### Estrutura

```
config/            regras e presentes (JSON)
scenes/main.tscn   cena principal
scripts/main.gd    fluxo do expediente, Kumo e eventos
scripts/autoload/  configuração, fila de eventos, conector da live
scripts/world/     Kumo, clientes, capivara, balcões, cenário
scripts/ui/        HUD, resultados, simulador de presentes
```
