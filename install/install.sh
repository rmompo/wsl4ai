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
REPO_DIR="${WORK_DIR}/repo"
TOOL_SRC="${REPO_DIR}/tool"
CONF_SRC="${REPO_DIR}/conf"
DEFAULTS_FILE="${REPO_DIR}/install/defaults.env"
STARTUP_FILE="${REPO_DIR}/install/.startup-wsl4ai.sh"
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

_download() {
  local url="$1" dest="$2"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "${url}" -o "${dest}"
  elif command -v wget >/dev/null 2>&1; then
    wget -qO "${dest}" "${url}"
  else
    echo "install.sh: need curl or wget to download files." >&2
    exit 1
  fi
}

ensure_repo() {
  if [[ -d "${REPO_DIR}/tool" ]]; then
    return 0
  fi
  if ! command -v git >/dev/null 2>&1; then
    return 1
  fi
  echo -e "${C_STEP}install.sh: cloning repository to ${REPO_DIR}...${C_R}"
  git clone --depth=1 --branch main "${REPO_URL}" "${REPO_DIR}"
  if [[ ! -d "${REPO_DIR}/tool" ]]; then
    echo "install.sh: tool/ not found inside cloned repository." >&2
    exit 1
  fi
  echo -e "${C_STEP}install.sh: repository ready at ${REPO_DIR}${C_R}"
}

ensure_defaults_env() {
  # Use repo if already cloned; otherwise download only defaults.env as fallback
  if [[ -f "${DEFAULTS_FILE}" ]]; then
    return 0
  fi
  local fallback="${WORK_DIR}/defaults.env"
  DEFAULTS_FILE="${fallback}"
  if [[ -f "${fallback}" ]]; then
    return 0
  fi
  echo "install.sh: defaults.env not found; downloading from GitHub..." >&2
  _download "${DEFAULTS_URL}" "${fallback}"
  if [[ ! -s "${fallback}" ]]; then
    echo "install.sh: failed to download defaults.env (empty or missing)." >&2
    rm -f "${fallback}"
    exit 1
  fi
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

ensure_repo
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

_USER_HOME="/home/${WSL4AI_USER}"
WSL_DDBB="${WSL_DDBB//${HOME}/${_USER_HOME}}"
WSL_PROJECTS="${WSL_PROJECTS//${HOME}/${_USER_HOME}}"
WSL_DDBB="$(ensure_trailing_slash "$(prompt "WSL_DDBB" "${WSL_DDBB:-${_USER_HOME}/wsl4ai/conf/ddbb}")")"
WSL_PROJECTS="$(ensure_trailing_slash "$(prompt "WSL_PROJECTS" "${WSL_PROJECTS:-${_USER_HOME}/wsl4ai/proyectos}")")"
HOST_DDBB="$(ensure_trailing_slash "$(prompt "HOST_DDBB" "${HOST_DDBB}")")"
HOST_PROJECTS="$(ensure_trailing_slash "$(prompt "HOST_PROJECTS" "${HOST_PROJECTS}")")"
INSTALL_BASE="$(dirname "$(dirname "${WSL_DDBB%/}")")"
INSTALL_CONF="${INSTALL_BASE}/conf/"
INSTALL_TOOL="${INSTALL_BASE}/tool/"

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

# ─── PHASE 3: CLONE REPOSITORY ──────────────────────────────────────────────

ensure_repo
if [[ ! -d "${REPO_DIR}/tool" ]]; then
  echo "install.sh: repository not available after apt install; aborting." >&2
  exit 1
fi

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

echo -e "${C_STEP}Step 6: copying tool/ to ${INSTALL_TOOL}${C_R}"
sudo -u "${WSL4AI_USER}" -H mkdir -p "${INSTALL_TOOL}"
shopt -s dotglob nullglob
for _src in "${TOOL_SRC}"/*; do
  [[ -e "${_src}" ]] || continue
  case "$(basename "${_src}")" in
    .gitkeep) continue ;;
  esac
  cp -a "${_src}" "${INSTALL_TOOL}/"
  chown -R "${WSL4AI_USER}:${WSL4AI_USER}" "${INSTALL_TOOL}/$(basename "${_src}")"
done

REQ="${INSTALL_TOOL}requirements.txt"
if [[ ! -f "${REQ}" ]]; then
  echo "install.sh: missing ${REQ}" >&2
  exit 1
fi

# ─── PHASE 6b: COPY extras/ ─────────────────────────────────────────────────

EXTRAS_SRC="${REPO_DIR}/extras"
INSTALL_EXTRAS="${INSTALL_BASE}/extras/"
if [[ -d "${EXTRAS_SRC}" ]]; then
  echo -e "${C_STEP}Step 6b: copying extras/ to ${INSTALL_EXTRAS}${C_R}"
  sudo -u "${WSL4AI_USER}" -H mkdir -p "${INSTALL_EXTRAS}"
  cp -a "${EXTRAS_SRC}/." "${INSTALL_EXTRAS}"
  chown -R "${WSL4AI_USER}:${WSL4AI_USER}" "${INSTALL_EXTRAS}"
fi

# ─── PHASE 7: PIP INSTALL ────────────────────────────────────────────────────

echo -e "${C_STEP}Step 7: pip install --user — requirements from tool/ as ${WSL4AI_USER}...${C_R}"
sudo -u "${WSL4AI_USER}" -H env HOME="${_USER_HOME}" REQ="${REQ}" bash -lc \
  'python3 -m pip install --user --upgrade pip --break-system-packages && python3 -m pip install --user --break-system-packages -r "$REQ"'

BASHRC="/home/${WSL4AI_USER}/.bashrc"
if [[ ! -f "${BASHRC}" ]]; then
  : >"${BASHRC}"
  chown "${WSL4AI_USER}:${WSL4AI_USER}" "${BASHRC}"
fi
if ! grep -qF '# Custom WSL4AI startup scripts' "${BASHRC}" 2>/dev/null; then
  printf '\n# Custom WSL4AI startup scripts\ncd ~\nsource ~/.startup-wsl4ai.sh\n' >>"${BASHRC}"
fi
chown "${WSL4AI_USER}:${WSL4AI_USER}" "${BASHRC}"

# ─── PHASE 8: MOUNT ddbb ─────────────────────────────────────────────────────

if [[ ! -d /mnt/c ]]; then
  echo "install.sh: /mnt/c not found — not running in WSL? Cannot mount ddbb from Windows path." >&2
  exit 1
fi

echo -e "${C_STEP}Step 8: bind-mount shared host directories (host → WSL)...${C_R}"
HOST_DDBB_WSL="$(win_path_to_wsl_mnt "${HOST_DDBB}")"
HOST_PROJECTS_WSL="$(win_path_to_wsl_mnt "${HOST_PROJECTS}")"

sudo -u "${WSL4AI_USER}" -H mkdir -p "${WSL_DDBB}"
mkdir -p "${HOST_DDBB_WSL}"

sudo -u "${WSL4AI_USER}" -H mkdir -p "${WSL_PROJECTS}"
mkdir -p "${HOST_PROJECTS_WSL}"

# Bind-mount now (as root) so Phase 10 writes the database to the host path.
# Without this, the DB would be created in the local dir and hidden by the
# mount on the next WSL startup.
if ! mountpoint -q "${WSL_DDBB%/}"; then
  mount --bind "${HOST_DDBB_WSL}" "${WSL_DDBB%/}"
  echo -e "${C_STEP}       bind-mounted ${HOST_DDBB_WSL} → ${WSL_DDBB%/}${C_R}"
fi

# ─── PHASE 8b: COPY .startup-wsl4ai.sh → HOME ───────────────────────────────

STARTUP_SRC="${STARTUP_FILE}"
STARTUP_DST="/home/${WSL4AI_USER}/.startup-wsl4ai.sh"
if [[ ! -f "${STARTUP_SRC}" ]]; then
  echo "install.sh: missing ${STARTUP_SRC}" >&2
  exit 1
fi
sed \
  -e "s|__INSTALL_BASE__|${INSTALL_BASE}|g" \
  "${STARTUP_SRC}" > "${STARTUP_DST}"
chmod +x "${STARTUP_DST}"
chown "${WSL4AI_USER}:${WSL4AI_USER}" "${STARTUP_DST}"
echo -e "${C_STEP}       .startup-wsl4ai.sh → ${STARTUP_DST}${C_R}"

# ─── PHASE 8c: SUDOERS FOR BIND-MOUNTS ──────────────────────────────────────

echo -e "${C_STEP}Step 8c: writing sudoers rule for bind-mounts (NOPASSWD for exact paths)...${C_R}"
SUDOERS_FILE="/etc/sudoers.d/wsl4ai-mount"
_MOUNT_BIN="$(command -v mount)"
# HOST_DDBB_WSL has no trailing slash (from win_path_to_wsl_mnt)
# WSL_DDBB / WSL_PROJECTS have trailing slash (from ensure_trailing_slash)
_UMOUNT_BIN="$(command -v umount)"
cat > "${SUDOERS_FILE}" <<EOF
# WSL4AI: allow ${WSL4AI_USER} to bind-mount the ddbb directory without a password
${WSL4AI_USER} ALL=(root) NOPASSWD: ${_MOUNT_BIN} --bind ${HOST_DDBB_WSL} ${WSL_DDBB}
# WSL4AI: allow ${WSL4AI_USER} to mount/umount under WSL_PROJECTS
${WSL4AI_USER} ALL=(root) NOPASSWD: ${_MOUNT_BIN} --bind * ${WSL_PROJECTS}*
${WSL4AI_USER} ALL=(root) NOPASSWD: ${_UMOUNT_BIN} ${WSL_PROJECTS}*
EOF
chmod 440 "${SUDOERS_FILE}"
echo -e "${C_STEP}       sudoers written → ${SUDOERS_FILE}${C_R}"

# ─── PHASE 9: conf/ (local.env, wsl4ai-update.py, config.json) ──────────────

# INSTALL_CONF already exists (created by mkdir -p WSL_DDBB in phase 8)
CONF_LOCAL="${INSTALL_CONF}local.env"
echo -e "${C_STEP}Step 9: writing local.env → ${CONF_LOCAL}...${C_R}"
{
  printf '%s\n' '# Generated by WSL4AI install.sh — edit or re-run install to change.'
  printf '%s\n' "# Created: $(date -Iseconds 2>/dev/null || date)"
  printf '%s\n' ''
  printf '%s\n' "HOST_DDBB=${HOST_DDBB}"
  printf '%s\n' "WSL_DDBB=${WSL_DDBB}"
  printf '%s\n' "HOST_PROJECTS=${HOST_PROJECTS}"
  printf '%s\n' "WSL_PROJECTS=${WSL_PROJECTS}"
} >"${CONF_LOCAL}"
chown "${WSL4AI_USER}:${WSL4AI_USER}" "${CONF_LOCAL}"

echo -e "${C_STEP}       copying wsl4ai-update.py → ${INSTALL_CONF}${C_R}"
cp -a "${CONF_SRC}/wsl4ai-update.py" "${INSTALL_CONF}wsl4ai-update.py"
chown "${WSL4AI_USER}:${WSL4AI_USER}" "${INSTALL_CONF}wsl4ai-update.py"

if [[ ! -f "${INSTALL_CONF}config.json" ]]; then
  echo -e "${C_STEP}       copying config.json → ${INSTALL_CONF}${C_R}"
  cp -a "${CONF_SRC}/config.json" "${INSTALL_CONF}config.json"
  chown "${WSL4AI_USER}:${WSL4AI_USER}" "${INSTALL_CONF}config.json"
fi

# ─── PHASE 10: INSTALL DATABASE ─────────────────────────────────────────────

echo -e "${C_STEP}Step 10: wsl4ai install database (as ${WSL4AI_USER})...${C_R}"
sudo -u "${WSL4AI_USER}" -H env HOME="${_USER_HOME}" INSTALL_TOOL="${INSTALL_TOOL}" bash -lc 'cd "$INSTALL_TOOL" && python3 wsl4ai.py install database'
echo -e "${C_STEP}       database location:${C_R}"
echo -e "${C_STEP}         WSL:     ${WSL_DDBB}wsl4ai.db${C_R}"
echo -e "${C_STEP}         Windows: ${HOST_DDBB}wsl4ai.db${C_R}"

# ─── CLEANUP ────────────────────────────────────────────────────────────────

rm -rf "${REPO_DIR}"
echo -e "${C_STEP}       removed temporary clone ${REPO_DIR}${C_R}"

echo ""
echo -e "${C_OK}Installation complete.${C_R}"
echo ""
echo -e "${C_PROMPT}IMPORTANT: to apply the default user you must:${C_R}"
echo -e "${C_PROMPT}  1. Exit this session:  exit${C_R}"
echo -e "${C_PROMPT}  2. From Windows, terminate this distro: wsl --terminate ${WSL_DISTRO_NAME:-<distro-name>}${C_R}"
echo -e "${C_PROMPT}  3. Re-enter the distro: wsl -d ${WSL_DISTRO_NAME:-<distro-name>}${C_R}"
