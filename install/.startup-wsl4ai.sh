#!/bin/bash
shopt -s expand_aliases

###############################################
# WSL4AI: Automatic mounts
###############################################

# Wait for /mnt/c to be available (drvfs takes a moment)
while [ ! -d /mnt/c ]; do
    sleep 0.1
done

# Mount 1: database directory
if ! mountpoint -q __WSL_DDBB__; then
    mount --bind __HOST_BASE_WSL__ __WSL_DDBB__
fi

# Mount 2: projects directory
if ! mountpoint -q __WSL_PROJECTS__; then
    mount --bind __HOST_PROJECTS_WSL__ __WSL_PROJECTS__
fi

###############################################
# WSL4AI: Environment setup
###############################################

export PATH="${HOME}/.local/bin:${PATH}"

alias wsl4ai="python3 __WSL_TOOL__wsl4ai.py"

wsl4ai use disableall --quiet

cd ~

###############################################
# WSL4AI: Welcome banner
###############################################

echo "[WSL4AI] ready"
echo "  cli: wsl4ai <command>"
echo "  tui: wsl4ai tui"
echo ""
