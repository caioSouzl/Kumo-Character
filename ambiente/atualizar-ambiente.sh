#!/bin/bash
# Atualiza o ambiente do Claude Code (setup script do ambiente na nuvem).
#
# Como funciona:
#   1. Ferramentas fixas (OpenMontage, Piper, yt-dlp, Blender, HyperFrames, Remotion).
#   2. Descoberta automática: todo repositório git em $BASE (padrão /home/user)
#      é instalado pelo que ele declara:
#        - package-lock.json  -> npm ci
#        - bun.lock           -> bun install --frozen-lockfile (se bun existir)
#        - requirements.txt   -> pip install -r
#        - .ambiente/setup.sh -> roda o script próprio do repositório (ganchos)
#   Repositório novo entra sozinho: basta clonar em $BASE. Para um passo
#   especial, crie .ambiente/setup.sh dentro dele. Nada precisa ser editado aqui.
#
# Variáveis:
#   BASE=/home/user            pasta onde estão os repositórios
#   PULAR="repo1 repo2"        repositórios a ignorar na descoberta
#   ATUALIZAR_DRY_RUN=1        só mostra o que faria, sem instalar
#
# Cada etapa é independente: se uma falhar, as outras continuam. O resumo no
# fim lista as que falharam. Sempre sai com código 0 para não travar a sessão.

BASE="${BASE:-/home/user}"
PULAR="${PULAR:-}"
FALHAS=()

run() {
  if [ -n "$ATUALIZAR_DRY_RUN" ]; then echo "    [dry-run] $*"; return 0; fi
  "$@"
}

# step NOME COMANDO... : roda e registra falha sem interromper o script
step() {
  local nome="$1"; shift
  echo "==> $nome"
  if ! run "$@"; then
    echo "AVISO: etapa falhou: $nome"
    FALHAS+=("$nome")
  fi
}

pulado() { case " $PULAR " in *" $1 "*) return 0 ;; esac; return 1; }

# ---------- 1. Ferramentas fixas ----------
step "requirements OpenMontage" bash -c 'pip install -q -r https://raw.githubusercontent.com/caioSouzl/OpenMontage/main/requirements.txt'
step "ferramentas locais" pip install -q faster-whisper piper-tts youtube-transcript-api mediapipe opencv-python "yt-dlp[default]"

# Voz Piper em português do Brasil
mkdir -p "$HOME/.piper/models"
if [ ! -f "$HOME/.piper/models/pt_BR-faber-medium.onnx" ]; then
  step "voz pt-BR" python -m piper.download_voices --download-dir "$HOME/.piper/models" pt_BR-faber-medium
fi

# yt-dlp usando o Node para o YouTube
mkdir -p "$HOME/.config/yt-dlp"
if ! grep -qs -- "--js-runtimes" "$HOME/.config/yt-dlp/config"; then
  run bash -c 'echo "--js-runtimes node" >> "$HOME/.config/yt-dlp/config"'
fi

# Blender 5.2.3 + monitor virtual (para o mcp-for-blender)
if ! command -v blender >/dev/null; then
  step "blender" bash -c 'curl -sSL -o /tmp/blender.tar.xz https://download.blender.org/release/Blender5.2/blender-5.2.3-linux-x64.tar.xz && tar -xJf /tmp/blender.tar.xz -C /opt && rm -f /tmp/blender.tar.xz && ln -sf /opt/blender-5.2.3-linux-x64/blender /usr/local/bin/blender'
fi
command -v xvfb-run >/dev/null || step "xvfb" bash -c 'apt-get update -qq && apt-get install -y -qq xvfb'

# HyperFrames
step "hyperframes" npx --yes hyperframes --version

# ---------- 2. Descoberta automática dos repositórios ----------
echo "==> Repositórios em $BASE"
for dir in "$BASE"/*/; do
  nome="$(basename "$dir")"
  [ -d "$dir/.git" ] || continue
  if pulado "$nome"; then echo "    $nome: ignorado (PULAR)"; continue; fi

  if [ -f "$dir/.ambiente/setup.sh" ]; then
    step "$nome (gancho próprio)" bash -c "cd '$dir' && bash .ambiente/setup.sh"
  fi
  if [ -f "$dir/package-lock.json" ]; then
    step "$nome (npm ci)" bash -c "cd '$dir' && npm ci --no-audit --no-fund"
  elif [ -f "$dir/bun.lock" ] && command -v bun >/dev/null; then
    step "$nome (bun)" bash -c "cd '$dir' && bun install --frozen-lockfile"
  fi
  if [ -f "$dir/requirements.txt" ]; then
    step "$nome (pip)" pip install -q -r "$dir/requirements.txt"
  fi
  echo "    $nome: verificado"
done

# Remotion do OpenMontage (ou do clone antigo)
for d in "$BASE/OpenMontage" "$BASE/openmontage"; do
  [ -d "$d/remotion-composer" ] && step "remotion" bash -c "cd '$d/remotion-composer' && npm ci --no-audit --no-fund" && break
done

# ---------- resumo ----------
echo "==> Configuração concluída"
if [ "${#FALHAS[@]}" -gt 0 ]; then
  echo "Etapas com falha:"
  printf '  - %s\n' "${FALHAS[@]}"
else
  echo "Nenhuma etapa falhou."
fi
exit 0
