# Ferramentas de inspeção — Kumo 3D

Estas ferramentas só leem: nunca alteram o modelo. Rode sempre sobre uma **cópia** do `.blend`. Cada uma gera JSON (para agentes) e Markdown (para pessoas), no padrão do CLI-Anything.

## `kumo_inspect.py` — topologia e geometria

```bash
cp kumo_toon.blend /tmp/k.blend
python kumo_inspect.py /tmp/k.blend --json ../docs/inspecao/malha.json --md ../docs/inspecao/malha.md [--object Kumo_Head]
```

Precisa de `bpy` (`pip install bpy==5.2.3`) ou do Blender: `blender -b -P kumo_inspect.py -- /tmp/k.blend ...`.

Por objeto, mostra:
- quantos vértices, arestas e faces existem, e o formato das faces;
- faces planas e suavizadas;
- se a malha é fechada e para onde apontam as normais (pelo volume com sinal);
- problemas: arestas não-manifold, de borda ou soltas, vértices soltos ou duplicados, faces de área zero e enrolamento inconsistente.

No objeto de detalhe (por padrão a cabeça), lista cada face com formato, área, centro, normal, inclinação (+ para cima), azimute (0° = frente), região, material e faces vizinhas.

## `kumo_silhouette.py` — fidelidade à referência

```bash
python3 kumo_silhouette.py --renders ../renders --ref ../../character-model-sheet/assets --out ../docs/inspecao
```

Requer Pillow. Para cada vista (frente, 3/4, perfil e costas):
- calcula o IoU entre a silhueta da render e a do recorte da referência, as duas em unidades de H e alinhadas pelo chão e pelo centro da cabeça;
- gera o perfil de largura a cada 0,05 H, com as diferenças;
- gera uma sobreposição: vermelho = só a referência, azul = só o modelo, cinza = os dois.
