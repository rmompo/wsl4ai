# WSL4AI

WSL4AI is a **Python CLI and terminal UI (TUI)** for **Linux / WSL** that manages a small **SQLite** catalog: **registries** (mount definitions), per-distro **WSL** rows, and **use** links (bind-mount workflows). It coordinates project locations and tooling across **WSL** and the **Windows** host.

- **Application code:** `tool/` (`wsl4ai` entrypoint, `requirements.txt`).
- **Persistent config:** `conf/` (`wsl4ai-update.py`, `config.json` — installed to `~/wsl4ai/conf/`).
- **Product specifications (CLI/TUI):** [`specs/tool/`](specs/tool/).
- **Bootstrap installer (WSL):** [`install/`](install/) — see [`specs/install/installer.md`](specs/install/installer.md).

---

## Requirements

- **WSL** (Debian/Ubuntu-style) with Python **3**, **pip**, and **git** (installed automatically by the bootstrap installer).
- **`sudo`**, **`apt-get`**, **`curl`** or **`wget`**, and **`/mnt/c`** available.

---

## Install

Place `install.sh` in `/tmp/wsl4ai/` and run it as root:

```bash
mkdir -p /tmp/wsl4ai
curl -fsSL https://raw.githubusercontent.com/rmompo/wsl4ai/main/install/install.sh -o /tmp/wsl4ai/install.sh
sudo bash /tmp/wsl4ai/install.sh
```

```bash
mkdir -p /tmp/wsl4ai
wget -qO /tmp/wsl4ai/install.sh https://raw.githubusercontent.com/rmompo/wsl4ai/main/install/install.sh
sudo bash /tmp/wsl4ai/install.sh
```

The script downloads any missing files (`defaults.env`, `tool/`, `conf/`) automatically. Follow the prompts (Linux user, `WSL_DDBB`, `WSL_PROJECTS`, `HOST_DDBB`, `HOST_PROJECTS`). The installer:

1. Installs Python 3, pip, and git via apt.
2. Creates the Linux user; sets it as default WSL login user.
3. Copies `tool/` into `~/wsl4ai/tool/`.
4. Installs pip dependencies (`--user`).
5. Creates mount point directories for `WSL_DDBB` and `WSL_PROJECTS`.
6. Installs `~/.startup-wsl4ai.sh`; configures `.bashrc` to source it on start.
7. Writes `conf/local.env` with `HOST_DDBB`, `WSL_DDBB`, `HOST_PROJECTS`, `WSL_PROJECTS`.
8. Runs `wsl4ai install database` to create the SQLite database.

After installation, exit WSL and run `wsl --terminate <distro>` from Windows (where `<distro>` is your WSL distribution name) to apply all changes.

---

## Directory layout

```
~/.startup-wsl4ai.sh       — startup script (sourced by .bashrc; manages mounts and aliases)

~/wsl4ai/
├── tool/              — Python application (replaced on update)
├── proyectos/         — bind-mount → HOST_PROJECTS (Windows)
└── conf/              — persistent config (never replaced on update)
    ├── local.env      — HOST_DDBB, WSL_DDBB, HOST_PROJECTS, WSL_PROJECTS
    ├── config.json
    ├── wsl4ai-update.py
    └── ddbb/          — bind-mount → HOST_DDBB (Windows)
        └── wsl4ai.db
```

---

## Usage

```bash
wsl4ai <command>       # CLI mode
wsl4ai tui             # Text User Interface
wsl4ai -v              # Show version
```

---

## Update

Check whether a newer version is available:

```bash
wsl4ai install update --check
wsl4ai iu --check              # shorthand
```

Check and apply the update if a newer version exists:

```bash
wsl4ai install update
wsl4ai iu                      # shorthand
```

The updater (`conf/wsl4ai-update.py`) is a standalone script that is **never replaced by updates**. It downloads `wsl4ai.py` from GitHub to compare versions, then clones the repository and replaces `tool/` atomically. `conf/` is never touched.

> **Note:** `install update` is a CLI-only command — it is not available in the TUI.

---

## WSL configuration guides

Step-by-step setup guides for WSL distros dedicated to specific AI tools:

| Guide | Tool | Method |
| ----- | ---- | ------ |
| [`wsls/wsl4codex.md`](wsls/wsl4codex.md) | OpenAI Codex CLI | Homebrew |
| [`wsls/wsl4claudecode.md`](wsls/wsl4claudecode.md) | Anthropic Claude Code | Native installer |
| [`wsls/wsl4copilot.md`](wsls/wsl4copilot.md) | GitHub Copilot CLI | Homebrew + gh extension |

Each guide covers prerequisites, installation, authentication, and startup script configuration.

---

## Documentation

| Area | Location |
| ---- | -------- |
| CLI / TUI specifications | [`specs/tool/`](specs/tool/) |
| Bootstrap installer | [`specs/install/`](specs/install/) |
