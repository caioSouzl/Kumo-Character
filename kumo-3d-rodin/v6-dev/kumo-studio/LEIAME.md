# Estúdio do Kumo

Página para posar e animar o Kumo no navegador. Versão online (privada, só você abre): https://claude.ai/artifact/4HsPwrSdRPfztG2NH96TdE

- O modelo é `kumo.glb`, uma cópia de `maos-corretivas/kumo_v6_maos_jogo.glb`: a aparência oficial, com as mãos de 3 dedos e polegar, a correção da mão fechada e o contorno de jogo.
- Os olhos são os pintados do modelo oficial.

## Abrir no seu computador

Os navegadores não deixam a página ler `kumo.glb` direto do disco, então rode um servidor local nesta pasta:

```bash
cd kumo-3d-rodin/v6-dev/kumo-studio
python3 -m http.server 8000
```

Depois, abra http://localhost:8000 no navegador. A página precisa de internet só para baixar a biblioteca 3D (three.js) e as fontes.

## O que dá para fazer

- **Pose:**
  - clique num ponto âmbar sobre uma articulação e gire pelos anéis coloridos, ou escolha a articulação na lista e use os controles Dobrar, Torcer e Inclinar;
  - poses prontas: Repouso, Acenar, Comemorar, Apontar, Mãos fechadas e Mãos abertas;
  - a cauda tem os controles Enrolar e Abanar.
- **Mãos e dedos:**
  - Fechar, cada dedo, Polegar e Abrir, nas duas mãos;
  - a correção da mão fechada liga sozinha, como no Blender.
- **Animação:**
  - grave quadros-chave na linha do tempo (botão **Gravar quadro** ou tecla `K`) e toque com `Espaço`;
  - há três exemplos prontos;
  - o rascunho fica salvo no navegador.
- **Blender:**
  - **Copiar pose** e **Copiar animação** geram um JSON;
  - o script `aplicar_no_blender.py` aplica esse JSON no rig do Blender, com os mesmos nomes e eixos de osso;
  - a animação vira a ação `Estudio_Kumo` a 24 fps.

## Conferido

- O carregamento e as poses prontas foram testados sem erros no navegador.
- A pose "Acenar + mãos fechadas" foi copiada da página e aplicada no `kumo_v6_maos_jogo.blend` com o script, e o resultado é igual.
