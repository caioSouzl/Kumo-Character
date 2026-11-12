# Ombros do Kumo 3D

Objetivo: o braço girar pelo ombro sem a pele se cruzar, sem mudar a aparência do Kumo parado.

## O que mudou (só no movimento)
1. **Ponto de giro do ombro mais alto** (sugestão do Caio): a junta do braço subiu de z 0,74 para 0,83, perto do topo do ombro. Antes ela ficava no meio da altura do braço e o giro parecia o de um cotovelo. Só o esqueleto mudou.
2. **Ombro automático**: acima de 30°, o osso do ombro (clavícula) leva 45% de erguer o braço e 65% de levá-lo à frente.
3. **Transição de pesos ombro↔braço suavizada** (30 passos), depois limitada a 4 ossos por vértice com soma 1 (regra de jogo; 387 vértices ajustados).
4. **8 shape keys corretivas** (`Ombro_Erguer90/120/150`, `Ombro_Frente90`, de cada lado), ligadas à rotação do `upper_arm` por drivers. Os drivers usam a base dual dos dois eixos, então erguer não liga a chave de frente.

## Medições (pares de triângulos cruzando ≥ 0,5 mm)
| Pose | Antes E / D | Agora E / D |
|---|---|---|
| erguer 90° | 10 / 32 | 0 / 0 |
| erguer 120° | — | 0 / 0 |
| erguer 150° | 79 / 91 | 0 / 4 |
| à frente 90° | 104 / 78 | 29 / 1 |

Tabela completa (de 45° a 150°, e para trás): `medicoes_ombros.json`.

**Ainda falta:** o braço **esquerdo à frente** mantém um vinco pequeno no peito (29 pares, até 9,7 mm de profundidade). Nem as corretivas nem os pesos resolveram isso; o braço esquerdo da malha está numa posição de repouso diferente do direito.

## Conferências
- O Kumo parado ficou igual ao atual: a maior diferença foi de 0,009 mm.
- O GLB e o FBX reimportados batem com o Blender nos 5 quadros de teste: até 0,055 mm. Os pesos das shape keys saem gravados na animação.
- Os 27 arquivos oficiais estão intactos (`hashes-antes.sha256`).

## Arquivos
- `kumo_v6_ombros.blend`: Kumo com olhos de jogo, mãos e ombros (ação `Teste_Exportacao`).
- `kumo_v6_jogo.glb` / `kumo_v6_jogo.fbx`: exportação completa para jogo.
- `ombros-antes-x-agora.png` e `fotos/`.
- `ferramentas/ombro_automatico.py`: para quem anima. Anime só o braço e rode o script dentro do Blender: ele passa a parte certa do giro para o ombro em todos os quadros com chave, sem mudar a direção final do braço. Testado contra as medições: diferença de até 0,0012 mm.
- `src/`:
  - `medir_ombros.py`, `pesos_ombro.py`, `onde.py`: medições.
  - `corrigir_ombros.py`: pipeline, configurado pelas variáveis `OMBRO_Z=0.83 OMBRO_K=0.45 OMBRO_KF=0.65 OMBRO_SUAVE=30`.
  - `exportar_ombros.py`, `fotos_ombros.py`, `teste_ombro_auto.py`.
