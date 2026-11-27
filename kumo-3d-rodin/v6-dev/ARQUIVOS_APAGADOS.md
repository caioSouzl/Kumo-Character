# Arquivos apagados na limpeza de 27/11

Foram apagadas só as **exportações antigas** (GLB e FBX) de versões já substituídas e as cópias de segurança automáticas do Blender (`.blend1`). Os `.blend` de cada versão continuam aqui; as exportações voltam a sair deles com os scripts de `src/` de cada pasta (comandos no `RELATORIO.md`). Os arquivos antigos também continuam no histórico do Git.

| Apagado | Refazer com |
|---|---|
| `boca/kumo_v6_jogo.glb/.fbx` | `boca/src/exportar_boca.py` |
| `ombros/kumo_v6_jogo.glb/.fbx` | `ombros/src/exportar_ombros.py` |
| `olhos-jogo/kumo_v6_jogo.glb/.fbx` | `olhos-jogo/src/` |
| `olhos-novos/jogo/kumo_v6_jogo.glb/.fbx`, `olhos-novos/central/kumo_central.glb` | `olhos-novos/src/exportar.py`, `exportar_central.py` |
| `olhos-novos/calota/jogo/kumo_v7_jogo.glb/.fbx`, `calota/central/kumo_central.glb` | `olhos-novos/src/exportar_calota.py` |
| todos os `*.blend1` e `__pycache__` | (o Blender recria) |

Ficam: os arquivos oficiais (`auditoria/hashes-antes.sha256`), os `.blend` de todas as versões e os arquivos atuais (`movimento/jogo`, `movimento/central`, `kumo-studio`).
