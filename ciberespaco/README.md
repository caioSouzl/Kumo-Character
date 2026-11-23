# Ciberespaço (protótipo)

Jogo para lives (9:16, 3D leve): o ZodIA, assistente de IA, tenta terminar
seus projetos holográficos, e o Kumo, movido pelos presentes da live,
atrapalha. Design completo em [`docs/DESIGN.md`](docs/DESIGN.md).

### Como rodar

1. Instale o [Godot 4.4](https://godotengine.org/download) (ou mais novo).
2. No Godot, clique em **Importar** e escolha o `project.godot` desta pasta
   (`ciberespaco/`).
3. Aperte **F5**.

Os modelos ainda são provisórios. Para usar os do Hyper3D, veja
[`assets/models/README.md`](assets/models/README.md).

### Testar sem live

| Tecla | O que faz |
|---|---|
| `1` | Rosquinha: ZodIA rodopia |
| `2` | Finger Heart: Kumo esbarra no projeto |
| `3` | Galáxia: Kumo derruba o projeto |
| `4` | GG: acorda o Kumo |
| `5` | Heart Me: ZodIA mais rápido |
| `6` | Perfume: ZodIA tropeça e cai |
| `7` | Rosa: recarrega a bateria |
| `L` | curtidas (recarregam a bateria); `Shift` + `L` = x5 |
| `Shift` + número | o mesmo presente x10 |
| `F1` ou botão **SIM** | mostra/esconde o simulador |

As teclas seguem a ordem alfabética dos ids em `config/gifts.json`. Esconda o
painel antes de transmitir.

### Mudar regras, presentes e projetos

- `config/game.json`: tempo de cada projeto (120 s), quando o Kumo acorda
  (60 s), bateria e curtidas, câmera, modelos.
- `config/gifts.json`: qual presente dispara qual evento, pontos do ranking e
  estilo do agradecimento. `tiktok_names` são os nomes que o conector envia.
- `config/projects.json`: os objetos que o ZodIA constrói, peça por peça.

### Ligar a live

Igual ao Kumo Pizzaria: o jogo escuta um WebSocket local
(`config/game.json` → `live_connector`) e espera:

```json
{"gift": "Rose", "user": "fulano", "count": 5}
{"like": 15, "user": "fulano"}
```

### Estrutura

```
config/            regras, presentes e projetos (JSON)
scenes/main.tscn   cena principal
scripts/main.gd    fluxo: projetos, bateria, Kumo e eventos
scripts/autoload/  configuração, fila de eventos, conector da live
scripts/world/     ZodIA (e rosto), Kumo, campinho, projeto holográfico, câmera
scripts/ui/        HUD, avisos, agradecimentos, ranking, simulador
shaders/           holograma e chão de circuitos
assets/models/     .glb do Hyper3D (opcional)
```
