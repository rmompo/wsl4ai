#!/usr/bin/env bash
# WSL4AI — install v3.0 — bootstrap: prompts, user + sudo, wsl.conf, copy tool+conf, Python (apt), pip --user, bind-mount ddbb+projects, install database, local.env
# Must be placed and run from /tmp/wsl4ai/
# Must run as root: sudo bash /tmp/wsl4ai/install.sh
set -euo pipefail
shopt -s extglob

C_STEP='\e[1;36m'   # bold cyan  — step headers and info messages
C_PROMPT='\e[1;33m' # bold yellow — interactive prompts
C_OK='\e[1;32m'     # bold green  — final success message
C_R='\e[0m'         # reset

WORK_DIR="/tmp/wsl4ai"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOL_SRC="${WORK_DIR}/tool"
CONF_SRC="${WORK_DIR}/conf"
DEFAULTS_FILE="${WORK_DIR}/defaults.env"
DEFAULTS_URL="https://raw.githubusercontent.com/rmompo/wsl4ai/main/install/defaults.env"
REPO_URL="https://github.com/rmompo/wsl4ai.git"

if [[ "${SCRIPT_DIR}" != "${WORK_DIR}" ]]; then
  echo "install.sh: must be run from ${WORK_DIR} (current: ${SCRIPT_DIR})" >&2
  exit 1
fi

if [[ "${EUID:-0}" -ne 0 ]]; then
  echo "install.sh: run as root (example: sudo bash ${WORK_DIR}/install.sh)" >&2
  exit 1
fi

ensure_defaults_env() {
  if [[ -f "${DEFAULTS_FILE}" ]]; then
    return 0
  fi
  echo "install.sh: ${DEFAULTS_FILE} not found; downloading from GitHub..." >&2
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "${DEFAULTS_URL}" -o "${DEFAULTS_FILE}"
  elif command -v wget >/dev/null 2>&1; then
    wget -qO "${DEFAULTS_FILE}" "${DEFAULTS_URL}"
  else
    echo "install.sh: need curl or wget to fetch defaults.env." >&2
    exit 1
  fi
  if [[ ! -s "${DEFAULTS_FILE}" ]]; then
    echo "install.sh: failed to download defaults.env (empty or missing)." >&2
    rm -f "${DEFAULTS_FILE}"
    exit 1
  fi
}

ensure_tool_dir() {
  if [[ -d "${TOOL_SRC}" ]]; then
    return 0
  fi
  echo "install.sh: tool/ not found; downloading via git..." >&2

  if ! command -v git >/dev/null 2>&1; then
    echo "install.sh: git not available yet; will be installed in apt step." >&2
    return 1
  fi

  git clone --depth=1 --branch main "${REPO_URL}" "${WORK_DIR}/tmp"

  if [[ ! -d "${WORK_DIR}/tmp/tool" ]]; then
    echo "install.sh: tool/ not found inside cloned repository." >&2
    rm -rf "${WORK_DIR}/tmp"
    exit 1
  fi

  mv "${WORK_DIR}/tmp/tool" "${TOOL_SRC}"
  [[ -d "${WORK_DIR}/tmp/conf" ]] && mv "${WORK_DIR}/tmp/conf" "${CONF_SRC}"
  rm -rf "${WORK_DIR}/tmp"
  echo -e "${C_STEP}install.sh: tool/ downloaded at ${TOOL_SRC}${C_R}"
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
    echo "install.sh: expected Windows path like C:/... got: ${wp}" >&2
    return 1
  fi
}

prompt() {
  local name="$1"
  local def="$2"
  local line
  read -r -p "$(echo -e "${C_PROMPT}${name} [${def}]:${C_R} ")" line || true
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

echo -e "${C_STEP}WSL4AI install — collecting configuration before starting installation.${C_R}"
echo ""

read -r -p "$(echo -e "${C_PROMPT}WSL4AI_USER (Linux account to create; password will match this name):${C_R} ")" WSL4AI_USER || true
if [[ -z "${WSL4AI_USER// }" ]]; then
  echo "install.sh: WSL4AI_USER is required." >&2
  exit 1
fi
WSL4AI_USER="${WSL4AI_USER##+([[:space:]])}"
WSL4AI_USER="${WSL4AI_USER%%+([[:space:]])}"
WSL4AI_USER="${WSL4AI_USER,,}"
if ! valid_linux_username "${WSL4AI_USER}"; then
  echo "install.sh: invalid username (use lowercase letters, digits, _, -; must start with letter or _)." >&2
  exit 1
fi
if id -u "${WSL4AI_USER}" &>/dev/null; then
  echo "install.sh: user '${WSL4AI_USER}' already exists." >&2
  exit 1
fi

WSL_PROJECTS_SUFFIX="${WSL_PROJECTS#${WSL_BASE}}"
WSL_PROJECTS_SUFFIX="${WSL_PROJECTS_SUFFIX:-projects/}"
WSL_BASE_DEFAULT="${WSL_BASE:-$(printf '/home/%s/wsl4ai/' "${WSL4AI_USER}")}"
WSL_BASE="$(ensure_trailing_slash "$(prompt "WSL_BASE" "${WSL_BASE_DEFAULT}")")"
WSL_CONF="${WSL_BASE}conf/"
WSL_DDBB="${WSL_CONF}ddbb/"
WSL_TOOL="${WSL_BASE}tool/"
WSL_PROJECTS="${WSL_BASE}${WSL_PROJECTS_SUFFIX}"
HOST_BASE="$(ensure_trailing_slash "$(prompt "HOST_BASE" "${HOST_BASE}")")"
HOST_PROJECTS="$(ensure_trailing_slash "$(prompt "HOST_PROJECTS" "${HOST_PROJECTS}")")"

echo ""
echo -e "${C_STEP}Configuration collected. Starting installation...${C_R}"
echo ""

# ─── PHASE 2: APT UPDATE / UPGRADE / INSTALL PACKAGES ───────────────────────

echo -e "${C_STEP}Step 1: apt update...${C_R}"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq

echo -e "${C_STEP}Step 2: apt upgrade...${C_R}"
apt-get upgrade -y

echo -e "${C_STEP}Step 3: installing required packages (git, python3, python3-pip)...${C_R}"
apt-get install -y git python3 python3-pip

if ! command -v python3 >/dev/null 2>&1; then
  echo "install.sh: python3 is not available after install; aborting." >&2
  exit 1
fi

# ─── PHASE 3: DOWNLOAD tool/ ─────────────────────────────────────────────────

ensure_tool_dir

# ─── PHASE 4: CREATE USER ────────────────────────────────────────────────────

echo -e "${C_STEP}Step 4: creating user ${WSL4AI_USER} (password = username) and sudo-capable group...${C_R}"
useradd -m -s /bin/bash "${WSL4AI_USER}"
echo "${WSL4AI_USER}:${WSL4AI_USER}" | chpasswd
if getent group sudo >/dev/null 2>&1; then
  usermod -aG sudo "${WSL4AI_USER}"
elif getent group wheel >/dev/null 2>&1; then
  usermod -aG wheel "${WSL4AI_USER}"
else
  echo "install.sh: warning: no 'sudo' or 'wheel' group found; grant ${WSL4AI_USER} sudo manually." >&2
fi

# ─── PHASE 5: WSL DEFAULT USER ───────────────────────────────────────────────

echo -e "${C_STEP}Step 5: setting default WSL login user in /etc/wsl.conf...${C_R}"
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
echo -e "${C_STEP}  (restart WSL from Windows if needed: wsl --shutdown)${C_R}"

# ─── PHASE 6: COPY tool/ ─────────────────────────────────────────────────────

echo -e "${C_STEP}Step 6: copying tool/ to ${WSL_TOOL}${C_R}"
mkdir -p "${WSL_TOOL}" "${WSL_PROJECTS}"
shopt -s dotglob nullglob
for _src in "${TOOL_SRC}"/*; do
  [[ -e "${_src}" ]] || continue
  case "$(basename "${_src}")" in
    .gitkeep) continue ;;
  esac
  cp -a "${_src}" "${WSL_TOOL}/"
done
chown -R "${WSL4AI_USER}:${WSL4AI_USER}" "${WSL_TOOL}" "${WSL_PROJECTS}"

REQ="${WSL_TOOL}requirements.txt"
if [[ ! -f "${REQ}" ]]; then
  echo "install.sh: missing ${REQ}" >&2
  exit 1
fi

# ─── PHASE 7: PIP INSTALL ────────────────────────────────────────────────────

echo -e "${C_STEP}Step 7: pip install --user — requirements from tool/ as ${WSL4AI_USER}...${C_R}"
sudo -u "${WSL4AI_USER}" -H env HOME="/home/${WSL4AI_USER}" REQ="${REQ}" bash -lc \
  'python3 -m pip install --user --upgrade pip --break-system-packages && python3 -m pip install --user --break-system-packages -r "$REQ"'

BASHRC="/home/${WSL4AI_USER}/.bashrc"
if [[ ! -f "${BASHRC}" ]]; then
  : >"${BASHRC}"
  chown "${WSL4AI_USER}:${WSL4AI_USER}" "${BASHRC}"
fi
if ! grep -qF '.local/bin' "${BASHRC}" 2>/dev/null; then
  printf '\n# WSL4AI: pip --user scripts\nexport PATH="${HOME}/.local/bin:${PATH}"\n' >>"${BASHRC}"
fi
if ! grep -qF '# WSL4AI: start in home' "${BASHRC}" 2>/dev/null; then
  printf '\n# WSL4AI: start in home\ncd ~\n' >>"${BASHRC}"
fi
if ! grep -qF '# WSL4AI: alias' "${BASHRC}" 2>/dev/null; then
  printf '\n# WSL4AI: alias\nalias wsl4ai="python3 %swsl4ai.py"\n' "${WSL_TOOL}" >>"${BASHRC}"
fi
if ! grep -qF '# WSL4AI: safety disableall' "${BASHRC}" 2>/dev/null; then
  printf '\n# WSL4AI: safety disableall\nwsl4ai use disableall --quiet\n' >>"${BASHRC}"
fi
if ! grep -qF '# WSL4AI: welcome' "${BASHRC}" 2>/dev/null; then
  printf '\n# WSL4AI: welcome\necho ""\necho "WSL4AI ready"\necho "  cli: wsl4ai <command>"\necho "  tui: wsl4ai tui"\necho ""\n' >>"${BASHRC}"
fi
chown "${WSL4AI_USER}:${WSL4AI_USER}" "${BASHRC}"

# ─── PHASE 8: MOUNT ddbb ─────────────────────────────────────────────────────

if [[ ! -d /mnt/c ]]; then
  echo "install.sh: /mnt/c not found — not running in WSL? Cannot mount ddbb from Windows path." >&2
  exit 1
fi

echo -e "${C_STEP}Step 8: bind-mount shared host directories (host → WSL)...${C_R}"
HOST_BASE_WSL="$(win_path_to_wsl_mnt "${HOST_BASE}")"
HOST_PROJECTS_WSL="$(win_path_to_wsl_mnt "${HOST_PROJECTS}")"

mkdir -p "${HOST_BASE_WSL}" "${WSL_DDBB}"
if command -v mountpoint >/dev/null 2>&1 && mountpoint -q "${WSL_DDBB}" 2>/dev/null; then
  echo "install.sh: ${WSL_DDBB} is already a mount point; skipping mount." >&2
else
  mount --bind "${HOST_BASE_WSL}" "${WSL_DDBB}"
fi
FSTAB_LINE_DDBB="${HOST_BASE_WSL} ${WSL_DDBB} none bind 0 0"
if ! grep -qF "${WSL_DDBB}" /etc/fstab 2>/dev/null; then
  {
    echo ""
    echo "# WSL4AI shared database directory (install.sh)"
    echo "${FSTAB_LINE_DDBB}"
  } >>/etc/fstab
fi

mkdir -p "${HOST_PROJECTS_WSL}" "${WSL_PROJECTS}"
if command -v mountpoint >/dev/null 2>&1 && mountpoint -q "${WSL_PROJECTS}" 2>/dev/null; then
  echo "install.sh: ${WSL_PROJECTS} is already a mount point; skipping mount." >&2
else
  mount --bind "${HOST_PROJECTS_WSL}" "${WSL_PROJECTS}"
fi
FSTAB_LINE_PROJECTS="${HOST_PROJECTS_WSL} ${WSL_PROJECTS} none bind 0 0"
if ! grep -qF "${WSL_PROJECTS}" /etc/fstab 2>/dev/null; then
  {
    echo ""
    echo "# WSL4AI shared projects directory (install.sh)"
    echo "${FSTAB_LINE_PROJECTS}"
  } >>/etc/fstab
fi

chown "${WSL4AI_USER}:${WSL4AI_USER}" "${WSL_BASE}"

# ─── PHASE 9: conf/ (ddbb, local.env, wsl4ai-update.py, config.json) ────────

mkdir -p "${WSL_CONF}" "${WSL_DDBB}"
chown -R "${WSL4AI_USER}:${WSL4AI_USER}" "${WSL_CONF}"

CONF_LOCAL="${WSL_CONF}local.env"
echo -e "${C_STEP}Step 9: writing local.env → ${CONF_LOCAL}...${C_R}"
{
  printf '%s\n' '# Generated by WSL4AI install.sh — edit or re-run install to change.'
  printf '%s\n' "# Created: $(date -Iseconds 2>/dev/null || date)"
  printf '%s\n' ''
  printf '%s\n' "WSL_BASE=${WSL_BASE}"
  printf '%s\n' "WSL_TOOL=${WSL_TOOL}"
  printf '%s\n' "WSL_PROJECTS=${WSL_PROJECTS}"
  printf '%s\n' "HOST_BASE=${HOST_BASE}"
  printf '%s\n' "HOST_PROJECTS=${HOST_PROJECTS}"
} >"${CONF_LOCAL}"

echo -e "${C_STEP}       copying wsl4ai-update.py → ${WSL_CONF}${C_R}"
cp -a "${CONF_SRC}/wsl4ai-update.py" "${WSL_CONF}wsl4ai-update.py"

if [[ ! -f "${WSL_CONF}config.json" ]]; then
  echo -e "${C_STEP}       copying config.json → ${WSL_CONF}${C_R}"
  cp -a "${CONF_SRC}/config.json" "${WSL_CONF}config.json"
fi

chown -R "${WSL4AI_USER}:${WSL4AI_USER}" "${WSL_CONF}"

# ─── PHASE 10: INSTALL DATABASE ─────────────────────────────────────────────

echo -e "${C_STEP}Step 10: wsl4ai install database (as ${WSL4AI_USER})...${C_R}"
sudo -u "${WSL4AI_USER}" -H env HOME="/home/${WSL4AI_USER}" WSL_TOOL="${WSL_TOOL}" bash -lc 'cd "$WSL_TOOL" && python3 wsl4ai.py install database'

echo ""
echo -e "${C_OK}Done: user ${WSL4AI_USER}; tool copied; conf copied (wsl4ai-update.py, config.json); Python (system); pip deps (--user); conf/ddbb mounted from HOST_BASE; SQLite DB created; password equals username.${C_R}"
echo ""
echo -e "${C_PROMPT}IMPORTANT: exit this WSL session and run the following command from Windows to apply all changes:${C_R}"
echo -e "${C_PROMPT}  wsl --shutdown${C_R}"
