# WSL4AI

WSL4AI is a **Python CLI and terminal UI (TUI)** for **Linux / WSL** that manages a small **SQLite** catalog: **registries** (mount definitions), per-distro **WSL** rows, and **use** links (bind-mount workflows). It coordinates project locations and tooling across **WSL** and the **Windows** host.

- **Application code:** `tool/` (`wsl4ai` entrypoint, `requirements.txt`).
- **Product specifications (CLI/TUI):** [`specs/tool/`](specs/tool/).
- **Bootstrap installer (WSL):** [`install/`](install/) — see [`specs/install/installer.md`](specs/install/installer.md).

## Requirements

- **WSL** (Debian/Ubuntu-style) with Python **3**, **pip**, and **git** (installed automatically by the bootstrap installer).
- For the **automated installer:** **`sudo`**, **`apt-get`**, **`curl`** or **`wget`**, and **`/mnt/c`** for mounting the shared database path from Windows.

## Install (recommended)

Place `install.sh` in `/tmp/wsl4ai/` and run it as root. The script downloads any missing files (`defaults.env`, `tool/`) automatically.

```bash
mkdir -p /tmp/wsl4ai
curl -fsSL https://raw.githubusercontent.com/rmompo/wsl4ai/main/install/install.sh -o /tmp/wsl4ai/install.sh
sudo bash /tmp/wsl4ai/install.sh
```

Follow the prompts (new Linux user, paths, host folders for **ddbb** and **projects**). The script:

1. Installs Python 3, pip, and git via apt.
2. Creates the Linux user and sets it as the default WSL login user.
3. Copies **`tool/`**, installs pip dependencies, bind-mounts **ddbb**, links **`tool/ddbb`**.
4. Writes **`local.env`** under **`tool/`** with path configuration.
5. Runs **`wsl4ai install database`** to create the SQLite database.
6. Configures **`.bashrc`**: alias, safety `disableall`, welcome message.

After installation, exit the WSL session and run `wsl --shutdown` from Windows to apply all changes.

## Download without `git`

### curl

```bash
mkdir -p /tmp/wsl4ai
curl -fsSL https://raw.githubusercontent.com/rmompo/wsl4ai/main/install/install.sh -o /tmp/wsl4ai/install.sh
sudo bash /tmp/wsl4ai/install.sh
```

### wget

```bash
mkdir -p /tmp/wsl4ai
wget -qO /tmp/wsl4ai/install.sh https://raw.githubusercontent.com/rmompo/wsl4ai/main/install/install.sh
sudo bash /tmp/wsl4ai/install.sh
```

`defaults.env` and `tool/` are downloaded automatically by the script if not already present in `/tmp/wsl4ai/`.

## Usage

```bash
wsl4ai <command>       # CLI mode
wsl4ai tui             # Text User Interface
```

## Documentation

| Area | Location |
| ---- | -------- |
| CLI / TUI specifications | [`specs/tool/`](specs/tool/) |
| Bootstrap installer | [`specs/install/`](specs/install/) |
