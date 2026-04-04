#!/bin/bash

echo "[Codex] Checking for updates..."

# Update Homebrew silently
brew update >/dev/null 2>&1

# Upgrade Codex if a new version is available
brew upgrade codex >/dev/null 2>&1

echo "[Codex] Update check complete."

echo ""
