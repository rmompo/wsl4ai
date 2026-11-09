#!/usr/bin/env bash
# Install Claude Code (latest) in this WSL distro with its official native installer.
# Rule: one AI client per WSL distro.
# Usage: bash ~/wsl4ai/tool/scripts/wsl4ai-install-claudecode.sh [-h]
set -euo pipefail

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  C_OK=$'\033[32m'; C_ERR=$'\033[31m'; C_NEXT=$'\033[33m'; C_OFF=$'\033[0m'
else
  C_OK=''; C_ERR=''; C_NEXT=''; C_OFF=''
fi
ok()   { printf '%s%s%s\n' "${C_OK}" "$*" "${C_OFF}"; }
warn() { printf '%s%s%s\n' "${C_ERR}" "$*" "${C_OFF}" >&2; }
next() { printf '%s%s%s\n' "${C_NEXT}" "$*" "${C_OFF}"; }

usage() {
  cat <<'USAGE'
wsl4ai-install-claudecode.sh - install Claude Code (latest) in this WSL distro.

Usage:
  bash ~/wsl4ai/tool/scripts/wsl4ai-install-claudecode.sh [-h]

What it does:
  1. Refuses to continue if GitHub Copilot CLI is already installed
     (one AI client per WSL distro).
  2. Downloads and runs the official installer from claude.ai
     (about 240 MB, no progress bar; it can take a few minutes).

Notes:
  - Claude Code goes under ~/.local; ~/.local/bin is already on the PATH
    through ~/.startup-wsl4ai.sh.
  - The native installer needs no Node.js and keeps Claude Code up to date.
USAGE
}

for argument in "$@"; do
  case "${argument}" in
    -h|--help) usage; exit 0 ;;
    *) warn "Unknown argument: ${argument} (use -h)."; exit 1 ;;
  esac
done

if command -v copilot >/dev/null 2>&1 || [ -e "${HOME}/.local/bin/copilot" ]; then
  warn "GitHub Copilot CLI is already installed in this distro."
  warn "Use another WSL distro to install Claude Code."
  exit 1
fi

echo "Downloading and installing Claude Code (about 240 MB; no progress bar is shown)..."
curl -fsSL https://claude.ai/install.sh | bash

ok "Claude Code installed."
next "Next: run 'claude' (open a new shell first if the command is not found)."
