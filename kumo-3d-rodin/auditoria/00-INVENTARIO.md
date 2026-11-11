# Kumo 3D — inventário de arquivos e versões

**Data:** 2026-11-11 · **Natureza:** levantamento, sem alterações. Os hashes SHA-256 de 27 arquivos estão em [`hashes-antes.sha256`](hashes-antes.sha256). Para conferir, rode `sha256sum -c kumo-3d-rodin/auditoria/hashes-antes.sha256` na raiz do repositório.

## 1. Autoridade visual (referência)

| Arquivo | Papel |
|---|---|
| `referencia de modelo/kumo-referencia-01.png` | **Referência principal:** construção geométrica, 4 vistas, proporção de 3,5 cabeças, paleta |
| `referencia de modelo/kumo-referencia-02.png` | Segunda prancha da referência |
| `referencia de modelo/kumo-referencia-03-analise-geometrica.png` | Análise geométrica |
| `referencia de modelo/externas/2026-11-09/enviada-1..4` | Imagens enviadas ao Rodin |
| `referencia de modelo/externas/rodin-fc410dfd/` | Saída original do Rodin (cópia de segurança dos GLBs) |

## 2. Modelo principal (linha Rodin) — `kumo-3d-rodin/`

| Arquivo | O que é | Estado |
|---|---|---|
| `base_basic_pbr.glb`, `base_basic_shaded.glb` | Malha original do Rodin (triângulos) | Original, intocado |
| `kumo_rodin.blend` | Rodin importado, escalado, com toon e contorno | Histórico |
| `kumo_quad.blend` + `textures/kumo_quad_diffuse.png` | Retopologia automática (QuadriFlow, 7.396 quads) + textura assada (2048 px) | Base da malha atual |
| **`kumo_rigged.blend`** | **Modelo oficial atual:** malha quad + rig de 30 ossos + pose A + pálpebras antigas (`Kumo_Lid_L/R`) | **Versão estável do corpo** |
| `export/kumo_quad.glb`, `kumo_rigged.glb`, `kumo_rigged.fbx` | Exportações | **Desatualizadas:** não têm nenhum sistema ocular novo |
| `inspecao/` | Inspeção de topologia e diagnóstico ocular (somente leitura) | Válida, reaproveitada nesta auditoria |
| `olhos-v1/` … `olhos-v5/` | Cinco versões experimentais do sistema ocular, cada uma com `.blend`, scripts, texturas, pranchas e relatório | Experimentais; **nenhuma aprovada como final** |
| `auditoria/` | Esta auditoria | Nova |

### Versão mais estável de cada componente

| Componente | Versão mais estável | Observação |
|---|---|---|
| Forma e silhueta | `kumo_rigged.blend` (malha `Kumo`) | Idêntica em todas as versões de olhos (hash de vértices `04fb4708…`) |
| Textura | `textures/kumo_quad_diffuse.png` | Nunca alterada |
| Rig do corpo | `kumo_rigged.blend` (`Kumo_Rig`, 30 ossos) | Só esqueleto de deformação (ver diagnóstico) |
| Contorno (inverted hull) | `kumo_rigged.blend` | Aprovado; recorte na região dos olhos |
| Sistema ocular | `olhos-v5/kumo_eyes_exp.blend` (variante B) | Melhor resultado visual e geométrico até agora; ainda com contato na dobra da órbita |
| Variante ocular com aparo | `olhos-v5/kumo_eyes_exp_aparo.blend` | Reprovada no visual; guardada só para comparação |

## 3. Linhas arquivadas

| Pasta | O que é | Estado |
|---|---|---|
| `kumo-3d-toon/` | Modelo procedural cel-shaded (base v1, cabeça v2 F1/F1.2/P3) e ferramentas de silhueta e inspeção | Arquivado por decisão sua (`ARQUIVADO.md`). **Contém a cabeça facetada mais fiel à referência** (F1.2, aprovada na época). |
| `character-model-sheet/` | Folha de modelo 2D feita com recortes da referência | Concluída |

## 4. Dependências entre arquivos

```
referência 01 ──▶ Rodin (IA) ──▶ base_basic_pbr.glb
                                   │ QuadriFlow + bake
                                   ▼
                        kumo_quad.blend + kumo_quad_diffuse.png
                                   │ rig automático (bone heat) + pose A
                                   ▼
                           kumo_rigged.blend  ◀── modelo oficial
                                   │ leitura
                                   ▼
        olhos-v1 → v2 → v3 → v4 → v5  (cada um reconstrói do zero a partir do kumo_rigged.blend)
```

- Todos os `olhos-vN/kumo_eyes_exp.blend` dependem de `../textures/kumo_quad_diffuse.png` por caminho relativo.
- As texturas dos olhos ficam em `olhos-vN/textures/`. As tabelas de borda da pálpebra (v2 em diante) estão embutidas no `.blend`.
- As exportações em `export/` não dependem de nada, mas refletem só o estado de `kumo_rigged.blend`.

## 5. Volume do repositório

| Pasta | Tamanho |
|---|---|
| `kumo-3d-rodin/` | 465 MB (cinco versões de olhos com cerca de 9 MB de `.blend` e 30 a 75 MB de renders cada) |
| `kumo-3d-toon/` | 75 MB |
| `referencia de modelo/` | 29 MB |
| `character-model-sheet/` | 9 MB |

## 6. Ambiente técnico verificado

- **Blender 5.2.3 LTS** (módulo `bpy` em ambiente virtual), renderização Cycles em CPU.
- **Rigify 0.6.10** presente. Os operadores de metarig e geração estão registrados. Tipos disponíveis: `face.skin_eye`, `face.skin_jaw`, `limbs.arm/leg/super_finger`, `spines.basic_tail/super_spine/super_head`, `skin.basic_chain/stretchy_chain`.
- Exportadores glTF e FBX presentes.
- Modificadores confirmados: Corrective Smooth, Surface Deform, Data Transfer, Shrinkwrap, Lattice, Mesh Deform, Geometry Nodes, Weighted Normal.
- Operadores confirmados com teste que falha se não existirem: limitar influências, normalizar pesos, simetrizar, QuadriFlow, bake.
