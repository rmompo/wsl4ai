#!/bin/bash

echo "[CODEX] Checking for updates..."

# Update Homebrew silently
brew update >/dev/null 2>&1

# Upgrade Codex if a new version is available
brew upgrade codex >/dev/null 2>&1

echo "[CODEX] Update check complete."
