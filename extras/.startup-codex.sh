#!/bin/bash

C_TITLE='\e[1;36m'   # bold cyan  — module title
C_USAGE='\e[1;33m'   # bold yellow — usage hints
C_R='\e[0m'          # reset

echo -e "${C_TITLE}[CODEX]${C_R}"
echo "Checking for updates..."

# Update Homebrew silently
brew update >/dev/null 2>&1

# Upgrade Codex if a new version is available
brew upgrade codex >/dev/null 2>&1

echo "Update check complete."

echo ""
