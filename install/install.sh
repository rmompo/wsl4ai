#!/usr/bin/env bash
# WSL4AI — bootstrap: prompts, user + sudo, wsl.conf, copy tool, Python (apt), pip --user, mount ddbb, symlink tool/ddbb, install database, local.env
# Must be placed and run from /tmp/wsl4ai/
# Must run as root: sudo bash /tmp/wsl4ai/install4.sh
set -euo pipefail
shopt -s extglob

WORK_DIR="/tmp/wsl4ai"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOL_SRC="${WORK_DIR}/tool"
DEFAULTS_FILE="${WORK_DIR}/defaults.env"
DEFAULTS_URL="https://raw.githubusercontent.com/rmompo/wsl4ai/main/install/defaults.env"
REPO_URL="https://github.com/rmompo/wsl4ai.git"

if [[ "${SCRIPT_DIR}" != "${WORK_DIR}" ]]; then
  echo "install4.sh: must be run from ${WORK_DIR} (current: ${SCRIPT_DIR})" >&2
  exit 1
fi

if [[ "${EUID:-0}" -ne 0 ]]; then
  echo "install4.sh: run as root (example: sudo bash ${WORK_DIR}/install4.sh)" >&2
  exit 1
fi

ensure_defaults_env() {
  if [[ -f "${DEFAULTS_FILE}" ]]; then
    return 0
  fi
  echo "install4.sh: ${DEFAULTS_FILE} not found; downloading from GitHub..." >&2
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "${DEFAULTS_URL}" -o "${DEFAULTS_FILE}"
  elif command -v wget >/dev/null 2>&1; then
    wget -qO "${DEFAULTS_FILE}" "${DEFAULTS_URL}"
  else
    echo "install4.sh: need curl or wget to fetch defaults.env." >&2
    exit 1
  fi
  if [[ ! -s "${DEFAULTS_FILE}" ]]; then
    echo "install4.sh: failed to download defaults.env (empty or missing)." >&2
    rm -f "${DEFAULTS_FILE}"
    exit 1
  fi
}

ensure_tool_dir() {
  if [[ -d "${TOOL_SRC}" ]]; then
    return 0
  fi
  echo "install4.sh: tool/ not found; downloading via git..." >&2

  if ! command -v git >/dev/null 2>&1; then
    echo "install4.sh: git not available yet; will be installed in apt step." >&2
    return 1
  fi

  git clone --depth=1 --branch main "${REPO_URL}" "${WORK_DIR}/tmp"

  if [[ ! -d "${WORK_DIR}/tmp/tool" ]]; then
    echo "install4.sh: tool/ not found inside cloned repository." >&2
    rm -rf "${WORK_DIR}/tmp"
    exit 1
  fi

  mv "${WORK_DIR}/tmp/tool" "${TOOL_SRC}"
  rm -rf "${WORK_DIR}/tmp"
  echo "install4.sh: tool/ downloaded at ${TOOL_SRC}"
}

ensure_trailing_slash() {
  local p="$1"
  [[ "${p}" == */ ]] || p="${p}/"
  printf '%s' "${p}"
}

# Convert C:/path/... to /mnt/c/path/...
win_path_to_wsl_mnt() {
  local wp="$1"
  wp="${wp//\\//}"
  wp="${wp%/}"
  if [[ "${wp}" =~ ^([A-Za-z]):[/](.*)$ ]]; then
    local letter="${BASH_REMATCH[1],,}"
    local rest="${BASH_REMATCH[2]}"
    printf '/mnt/%s/%s' "${letter}" "${rest}"
  else
    echo "install4.sh: expected Windows path like C:/... got: ${wp}" >&2
    return 1
  fi
}

prompt() {
  local name="$1"
  local def="$2"
  local line
  read -r -p "${name} [${def}]: " line || true
  if [[ -z "${line}" ]]; then
    echo "${def}"
  else
    echo "${line}"
  fi
}

valid_linux_username() {
  [[ "$1" =~ ^[a-z_][a-z0-9_-]{0,31}$ ]]
}

# ─── PHASE 1: ALL PROMPTS ────────────────────────────────────────────────────

ensure_defaults_env
# shellcheck disable=SC1090
set -a
# shellcheck source=/dev/null
source "${DEFAULTS_FILE}"
set +a

echo "WSL4AI install — collecting configuration before starting installation."
echo ""

read -r -p "WSL4AI_USER (Linux account to create; password will match this name): " WSL4AI_USER || true
if [[ -z "${WSL4AI_USER// }" ]]; then
  echo "install4.sh: WSL4AI_USER is required." >&2
  exit 1
fi
WSL4AI_USER="${WSL4AI_USER##+([[:space:]])}"
WSL4AI_USER="${WSL4AI_USER%%+([[:space:]])}"
WSL4AI_USER="${WSL4AI_USER,,}"
if ! valid_linux_username "${WSL4AI_USER}"; then
  echo "install4.sh: invalid username (use lowercase letters, digits, _, -; must start with letter or _)." >&2
  exit 1
fi
if id -u "${WSL4AI_USER}" &>/dev/null; then
  echo "install4.sh: user '${WSL4AI_USER}' already exists." >&2
  exit 1
fi

read -r -p "Set '${WSL4AI_USER}' as default WSL user (/etc/wsl.conf)? [Y/n]: " _def_wsl || true
WSL4AI_SET_DEFAULT_USER="yes"
if [[ "${_def_wsl}" =~ ^[Nn]([Oo])?$ ]]; then
  WSL4AI_SET_DEFAULT_USER="no"
fi

WSL_BASE_DEFAULT="$(printf '/home/%s/wsl4ai/' "${WSL4AI_USER}")"
WSL_BASE="$(ensure_trailing_slash "$(prompt "WSL_BASE" "${WSL_BASE_DEFAULT}")")"
WSL_DDBB="${WSL_BASE}ddbb/"
WSL_TOOL="${WSL_BASE}tool/"
WSL_PROJECTS="${WSL_BASE}projects/"
HOST_DDBB="$(ensure_trailing_slash "$(prompt "HOST_DDBB" "${HOST_DDBB}")")"
HOST_PROJECTS="$(ensure_trailing_slash "$(prompt "HOST_PROJECTS" "${HOST_PROJECTS}")")"

echo ""
echo "Configuration collected. Starting installation..."
echo ""

# ─── PHASE 2: APT UPDATE / UPGRADE / INSTALL PACKAGES ───────────────────────

echo "Step 1: apt update..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq

echo "Step 2: apt upgrade..."
apt-get upgrade -y

echo "Step 3: installing required packages (git, python3, python3-pip)..."
apt-get install -y git python3 python3-pip

if ! command -v python3 >/dev/null 2>&1; then
  echo "install4.sh: python3 is not available after install; aborting." >&2
  exit 1
fi

# ─── PHASE 3: DOWNLOAD tool/ ─────────────────────────────────────────────────

ensure_tool_dir

# ─── PHASE 4: CREATE USER ────────────────────────────────────────────────────

echo "Step 4: creating user ${WSL4AI_USER} (password = username) and sudo-capable group..."
useradd -m -s /bin/bash "${WSL4AI_USER}"
echo "${WSL4AI_USER}:${WSL4AI_USER}" | chpasswd
if getent group sudo >/dev/null 2>&1; then
  usermod -aG sudo "${WSL4AI_USER}"
elif getent group wheel >/dev/null 2>&1; then
  usermod -aG wheel "${WSL4AI_USER}"
else
  echo "install4.sh: warning: no 'sudo' or 'wheel' group found; grant ${WSL4AI_USER} sudo manually." >&2
fi

# ─── PHASE 5: WSL DEFAULT USER ───────────────────────────────────────────────

if [[ "${WSL4AI_SET_DEFAULT_USER}" == "yes" ]]; then
  echo "Step 5: setting default WSL login user in /etc/wsl.conf..."
  mkdir -p /etc
  if [[ ! -f /etc/wsl.conf ]]; then
    printf '[user]\ndefault=%s\n' "${WSL4AI_USER}" >/etc/wsl.conf
  elif grep -q '^\[user\]' /etc/wsl.conf 2>/dev/null; then
    if grep -q '^default=' /etc/wsl.conf 2>/dev/null; then
      sed -i "s/^default=.*/default=${WSL4AI_USER}/" /etc/wsl.conf
    else
      sed -i "/^\[user\]/a default=${WSL4AI_USER}" /etc/wsl.conf
    fi
  else
    printf '\n[user]\ndefault=%s\n' "${WSL4AI_USER}" >>/etc/wsl.conf
  fi
  echo "  (restart WSL from Windows if needed: wsl --shutdown)"
else
  echo "Step 5: skipped (default WSL user not requested)."
fi

# ─── PHASE 6: COPY tool/ ─────────────────────────────────────────────────────

echo "Step 6: copying tool/ to ${WSL_TOOL}"
mkdir -p "${WSL_TOOL}" "${WSL_PROJECTS}"
shopt -s dotglob nullglob
for _src in "${TOOL_SRC}"/*; do
  [[ -e "${_src}" ]] || continue
  [[ "$(basename "${_src}")" == "ddbb" ]] && continue
  cp -a "${_src}" "${WSL_TOOL}/"
done
chown -R "${WSL4AI_USER}:${WSL4AI_USER}" "${WSL_TOOL}" "${WSL_PROJECTS}"

REQ="${WSL_TOOL}requirements.txt"
if [[ ! -f "${REQ}" ]]; then
  echo "install4.sh: missing ${REQ}" >&2
  exit 1
fi

# ─── PHASE 7: PIP INSTALL ────────────────────────────────────────────────────

echo "Step 7: pip install --user — requirements from tool/ as ${WSL4AI_USER}..."
sudo -u "${WSL4AI_USER}" -H env HOME="/home/${WSL4AI_USER}" REQ="${REQ}" bash -lc \
  'python3 -m pip install --user --upgrade pip --break-system-packages && python3 -m pip install --user --break-system-packages -r "$REQ"'

BASHRC="/home/${WSL4AI_USER}/.bashrc"
if [[ ! -f "${BASHRC}" ]]; then
  : >"${BASHRC}"
  chown "${WSL4AI_USER}:${WSL4AI_USER}" "${BASHRC}"
fi
if ! grep -qF '.local/bin' "${BASHRC}" 2>/dev/null; then
  printf '\n# WSL4AI: pip --user scripts\nexport PATH="${HOME}/.local/bin:${PATH}"\n' >>"${BASHRC}"
  chown "${WSL4AI_USER}:${WSL4AI_USER}" "${BASHRC}"
fi

# ─── PHASE 8: MOUNT ddbb ─────────────────────────────────────────────────────

if [[ ! -d /mnt/c ]]; then
  echo "install4.sh: /mnt/c not found — not running in WSL? Cannot mount ddbb from Windows path." >&2
  exit 1
fi

echo "Step 8: bind-mount shared ddbb (host → WSL)..."
HOST_DDBB_WSL="$(win_path_to_wsl_mnt "${HOST_DDBB}")"
mkdir -p "${HOST_DDBB_WSL}"
mkdir -p "${WSL_DDBB}"
if command -v mountpoint >/dev/null 2>&1 && mountpoint -q "${WSL_DDBB}" 2>/dev/null; then
  echo "install4.sh: ${WSL_DDBB} is already a mount point; skipping mount." >&2
else
  mount --bind "${HOST_DDBB_WSL}" "${WSL_DDBB}"
fi
FSTAB_LINE="${HOST_DDBB_WSL} ${WSL_DDBB} none bind 0 0"
if ! grep -qF "${WSL_DDBB}" /etc/fstab 2>/dev/null; then
  {
    echo ""
    echo "# WSL4AI shared database directory (install4.sh)"
    echo "${FSTAB_LINE}"
  } >>/etc/fstab
fi

chown "${WSL4AI_USER}:${WSL4AI_USER}" "${WSL_BASE}"

# ─── PHASE 9: SYMLINK ddbb ───────────────────────────────────────────────────

echo "Step 9: symlink ${WSL_TOOL}ddbb → shared ${WSL_DDBB} (wsl4ai.py expects tool/ddbb/)..."
if [[ -e "${WSL_TOOL}ddbb" ]] && [[ ! -L "${WSL_TOOL}ddbb" ]]; then
  rm -rf "${WSL_TOOL}ddbb"
fi
ln -sfn "${WSL_DDBB}" "${WSL_TOOL}ddbb"
chown -h "${WSL4AI_USER}:${WSL4AI_USER}" "${WSL_TOOL}ddbb" 2>/dev/null || true

# ─── PHASE 10: local.env ─────────────────────────────────────────────────────

OUT_DIR="/home/${WSL4AI_USER}/wsl4ai"
OUT_FILE="${OUT_DIR}/local.env"
TOOL_LOCAL="${WSL_TOOL}local.env"
mkdir -p "${OUT_DIR}"
chown "${WSL4AI_USER}:${WSL4AI_USER}" "${OUT_DIR}"

echo "Step 10: writing local.env → ${TOOL_LOCAL} and ${OUT_FILE}..."
{
  printf '%s\n' '# Generated by WSL4AI install4.sh — edit or re-run install to change.'
  printf '%s\n' "# Created: $(date -Iseconds 2>/dev/null || date)"
  printf '%s\n' ''
  printf '%s\n' "WSL4AI_USER=${WSL4AI_USER}"
  printf '%s\n' "WSL4AI_SET_DEFAULT_USER=${WSL4AI_SET_DEFAULT_USER}"
  printf '%s\n' "WSL_BASE=${WSL_BASE}"
  printf '%s\n' "WSL_DDBB=${WSL_DDBB}"
  printf '%s\n' "WSL_TOOL=${WSL_TOOL}"
  printf '%s\n' "WSL_PROJECTS=${WSL_PROJECTS}"
  printf '%s\n' "HOST_DDBB=${HOST_DDBB}"
  printf '%s\n' "HOST_PROJECTS=${HOST_PROJECTS}"
  printf '%s\n' "HOST_DDBB_WSL=${HOST_DDBB_WSL}"
} >"${TOOL_LOCAL}"
cp -a "${TOOL_LOCAL}" "${OUT_FILE}"
chown "${WSL4AI_USER}:${WSL4AI_USER}" "${TOOL_LOCAL}" "${OUT_FILE}"

# ─── PHASE 11: INSTALL DATABASE ──────────────────────────────────────────────

echo "Step 11: wsl4ai install database (as ${WSL4AI_USER})..."
sudo -u "${WSL4AI_USER}" -H env HOME="/home/${WSL4AI_USER}" WSL_TOOL="${WSL_TOOL}" bash -lc 'cd "$WSL_TOOL" && python3 wsl4ai.py install database'

echo ""
echo "Done: user ${WSL4AI_USER}; tool copied; Python (system); pip deps (--user); ddbb mounted; SQLite DB created; password equals username."
