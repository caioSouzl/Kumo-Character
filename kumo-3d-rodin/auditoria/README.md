# Kumo 3D — auditoria completa e projeto técnico

**Data:** 2026-11-11 · **Natureza:** auditoria, pesquisa e proposta. **Nenhum modelo foi alterado.** Os hashes de 27 arquivos estão em `hashes-antes.sha256`.

| Documento | Conteúdo |
|---|---|
| [`00-INVENTARIO.md`](00-INVENTARIO.md) | Arquivos, versões, dependências, versão mais estável de cada componente, ambiente técnico |
| [`01-DIAGNOSTICO.md`](01-DIAGNOSTICO.md) | Diagnóstico geral, problemas por gravidade, identidade contra a referência, prontidão do rig, hipóteses e limitações |
| [`02-PESQUISA.md`](02-PESQUISA.md) | Pesquisa externa com fontes, vantagens, limitações e decisão para cada técnica; compatibilidade com o Blender 5.2 |
| [`03-ARQUITETURA-E-PLANO.md`](03-ARQUITETURA-E-PLANO.md) | Comparação de soluções, arquitetura recomendada, sistema de testes, plano por fases, riscos e autorizações |

| Dados e ferramentas | |
|---|---|
| `src/auditoria_modelo.py` | Ferramenta de auditoria (somente leitura): integridade, simetria, UV, rig, pesos, 24 poses de articulação, desempenho |
| `auditoria-dados.json` | Resultados brutos, com método e limitações de cada teste |
| `poses-articulacao.png`, `poses/` | Evidência visual dos testes de articulação |

Para repetir: `python src/auditoria_modelo.py ../kumo_rigged.blend .` (Blender 5.2 via módulo `bpy`).
