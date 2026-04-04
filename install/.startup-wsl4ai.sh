#!/bin/bash
shopt -s expand_aliases

###############################################
# WSL4AI: Load config
###############################################

source __INSTALL_BASE__/conf/local.env

# Convert Windows path (C:/...) to WSL mount path (/mnt/c/...)
_wsl_mnt() {
    local p="${1//\\//}"
    p="${p%/}"
    if [[ "${p}" =~ ^([A-Za-z]):[/](.*)$ ]]; then
        echo "/mnt/${BASH_REMATCH[1],,}/${BASH_REMATCH[2]}"
    else
        echo "${p}"
    fi
}

###############################################
# WSL4AI: Automatic mounts
###############################################

# Wait for /mnt/c to be available (drvfs takes a moment)
while [ ! -d /mnt/c ]; do
    sleep 0.1
done

# Mount 1: ddbb directory
if ! mountpoint -q "${WSL_DDBB}"; then
    sudo mount --bind "$(_wsl_mnt "${HOST_DDBB}")" "${WSL_DDBB}"
fi

# Mount 2: projects directory
if ! mountpoint -q "${WSL_PROJECTS}"; then
    sudo mount --bind "$(_wsl_mnt "${HOST_PROJECTS}")" "${WSL_PROJECTS}"
fi

###############################################
# WSL4AI: Environment setup
###############################################

# pip --user scripts
export PATH="${HOME}/.local/bin:${PATH}"

cd ~

###############################################
# WSL4AI: Aliases
###############################################

# >>> WSL4AI BEGIN >>>
wsl4ai() {
  "python3" "__INSTALL_BASE__/tool/wsl4ai.py" "$@"
}
# <<< WSL4AI END <<<

###############################################
# WSL4AI: Welcome banner
###############################################

python3 __INSTALL_BASE__/tool/wsl4ai.py use disableall --quiet
python3 __INSTALL_BASE__/tool/wsl4ai.py -v
echo "cli: wsl4ai <command>"
echo "tui: wsl4ai tui"
echo ""
