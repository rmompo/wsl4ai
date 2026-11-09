#!/usr/bin/env bash
# Version: 0.1.0
# Install the basic tools to work with an AI client in this WSL distro (apt packages).
# Usage: bash ~/wsl4ai/tool/scripts/wsl4ai-install-tools.sh [check] [base] [python] [build] [-h]
set -u

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  C_OK=$'\033[32m'; C_ERR=$'\033[31m'; C_NEXT=$'\033[33m'; C_OFF=$'\033[0m'
else
  C_OK=''; C_ERR=''; C_NEXT=''; C_OFF=''
fi
ok()   { printf '%s%s%s\n' "${C_OK}" "$*" "${C_OFF}"; }
warn() { printf '%s%s%s\n' "${C_ERR}" "$*" "${C_OFF}" >&2; }
next() { printf '%s%s%s\n' "${C_NEXT}" "$*" "${C_OFF}"; }

# The groups of packages, in the order they are handled.
TOOL_GROUPS=(base python build)
declare -A GROUP_TEXT=(
  [base]='Basic tools: certificates, curl, wget, git, sudo, zip/unzip, jq, ripgrep, ssh client, editors and network utilities.'
  [python]='Python: python3, pip, venv, pipx and the python command.'
  [build]='Build tools: build-essential (gcc, make and friends).'
)
declare -A GROUP_PACKAGES=(
  [base]='ca-certificates curl wget nano git sudo zip unzip less jq openssh-client procps bash-completion gnupg xz-utils ripgrep rsync htop iproute2 bind9-dnsutils make tree iputils-ping'
  [python]='python3 python3-pip python3-venv pipx python-is-python3'
  [build]='build-essential'
)

usage() {
  cat <<'USAGE'
wsl4ai-install-tools.sh - install the basic tools to work with an AI client in this WSL distro.

Usage:
  bash ~/wsl4ai/tool/scripts/wsl4ai-install-tools.sh [check] [base] [python] [build] [-h]

Parameters:
  check      Only report what is missing; install nothing (exit code 1 if something is missing).
  base       Certificates, curl, wget, git, sudo, zip, unzip, less, jq, ripgrep, rsync, ssh client,
             nano, htop, tree, make, gnupg, xz, bash-completion, procps and network utilities
             (iproute2, bind9-dnsutils, iputils-ping).
  python     python3, python3-pip, python3-venv, pipx and python-is-python3.
  build      build-essential.
  -h         Show this help and exit.

Without a group it handles all of them.

Examples:
  bash ~/wsl4ai/tool/scripts/wsl4ai-install-tools.sh          Installs whatever is missing.
  bash ~/wsl4ai/tool/scripts/wsl4ai-install-tools.sh check    Lists what is missing and installs nothing.
  bash ~/wsl4ai/tool/scripts/wsl4ai-install-tools.sh python   Installs only the Python group.

Notes:
  - Installing needs root or sudo (sudo asks for the password of your user).
  - It only installs missing packages with apt: nothing is removed and no configuration is changed.
  - It does not install an AI client (use wsl4ai-install-claudecode.sh or wsl4ai-install-ghcopilot.sh).
USAGE
}

check_only=0
selected=()
for argument in "$@"; do
  case "${argument}" in
    -h|--help) usage; exit 0 ;;
    check) check_only=1 ;;
    *)
      if [ -n "${GROUP_PACKAGES[${argument}]+x}" ]; then selected+=("${argument}")
      else warn "Unknown argument: ${argument} (groups: ${TOOL_GROUPS[*]}; also check, -h)."; exit 1; fi ;;
  esac
done
[ "${#selected[@]}" -gt 0 ] || selected=("${TOOL_GROUPS[@]}")

is_installed() { dpkg-query -W -f='${Status}' "$1" 2>/dev/null | grep -q '^install ok installed$'; }

# Print the packages of a group that are not installed (one per line).
missing_packages() {
  local package
  for package in ${GROUP_PACKAGES[$1]}; do
    is_installed "${package}" || printf '%s\n' "${package}"
  done
}

if ! command -v dpkg-query >/dev/null 2>&1 || ! command -v apt-get >/dev/null 2>&1; then
  warn "This script needs a Debian/Ubuntu distro (dpkg and apt-get were not found)."
  exit 1
fi

missing=()
for group in "${selected[@]}"; do
  list="$(missing_packages "${group}")"
  if [ -z "${list}" ]; then
    ok "  ${group}: all the packages are installed."
  else
    echo "  ${group}: missing packages: $(echo "${list}" | tr '\n' ' ')"
    while IFS= read -r package; do missing+=("${package}"); done <<< "${list}"
  fi
done

if [ "${#missing[@]}" -eq 0 ]; then
  ok "Nothing to install."
  exit 0
fi
if [ "${check_only}" = 1 ]; then
  warn "Missing: ${missing[*]}"
  next "Next: bash $0 installs them."
  exit 1
fi

if [ "$(id -u)" -eq 0 ]; then apt_cmd=(apt-get)
elif command -v sudo >/dev/null 2>&1; then apt_cmd=(sudo apt-get)
else warn "Installing needs root or sudo, and sudo was not found."; exit 1; fi

echo "Installing: ${missing[*]} (sudo may ask for your password) ..."
"${apt_cmd[@]}" update -qq || { warn "apt-get update failed."; exit 1; }
"${apt_cmd[@]}" install -y --no-install-recommends "${missing[@]}" >/dev/null || { warn "apt-get install failed."; exit 1; }

failed=0
for group in "${selected[@]}"; do
  left="$(missing_packages "${group}")"
  if [ -z "${left}" ]; then ok "  ${group}: ready."
  else warn "  ${group}: still missing: $(echo "${left}" | tr '\n' ' ')"; failed=1; fi
done
[ "${failed}" -eq 0 ] || exit 1
ok "Tools installed."
next "Next: install an AI client (wsl4ai-install-claudecode.sh or wsl4ai-install-ghcopilot.sh)."
