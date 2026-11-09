#!/usr/bin/env bash
# Install GitHub Copilot CLI (latest) in this WSL distro with its standalone installer (no Node.js needed).
# Rule: one AI client per WSL distro.
# Usage: bash ~/wsl4ai/tool/scripts/wsl4ai-install-ghcopilot.sh [-h]
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
wsl4ai-install-ghcopilot.sh - install GitHub Copilot CLI (latest) in this WSL distro.

Usage:
  bash ~/wsl4ai/tool/scripts/wsl4ai-install-ghcopilot.sh [-h]

What it does:
  1. Refuses to continue if Claude Code is already installed
     (one AI client per WSL distro).
  2. Downloads and runs the standalone installer from gh.io
     (no Node.js or Homebrew needed; no progress bar; it can take a few minutes).

Notes:
  - GitHub Copilot CLI goes under ~/.local; ~/.local/bin is already on the PATH
    through ~/.startup-wsl4ai.sh.
USAGE
}

for argument in "$@"; do
  case "${argument}" in
    -h|--help) usage; exit 0 ;;
    *) warn "Unknown argument: ${argument} (use -h)."; exit 1 ;;
  esac
done

if command -v claude >/dev/null 2>&1 || [ -e "${HOME}/.local/bin/claude" ]; then
  warn "Claude Code is already installed in this distro."
  warn "Use another WSL distro to install GitHub Copilot CLI."
  exit 1
fi

echo "Downloading and installing GitHub Copilot CLI (no progress bar is shown)..."
curl -fsSL https://gh.io/copilot-install | bash

ok "GitHub Copilot CLI installed."
next "Next: run 'copilot' (open a new shell first if the command is not found)."
