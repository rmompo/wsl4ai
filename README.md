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

The script downloads any missing files (`defaults.env`, `tool/`, `conf/`) automatically. Follow the prompts (Linux user, `WSL_BASE`, `HOST_BASE`, `HOST_PROJECTS`). The installer:

1. Installs Python 3, pip, and git via apt.
2. Creates the Linux user; sets it as default WSL login user.
3. Copies `tool/` and `conf/` into `~/wsl4ai/`.
4. Installs pip dependencies (`--user`).
5. Bind-mounts `HOST_BASE` → `conf/ddbb/` and `HOST_PROJECTS` → `projects/`.
6. Writes `conf/local.env` with path configuration.
7. Runs `wsl4ai install database` to create the SQLite database.
8. Configures `.bashrc`: alias, safety `disableall --quiet`, welcome message.

After installation, exit WSL and run `wsl --shutdown` from Windows to apply all changes.

---

## Directory layout

```
~/wsl4ai/
├── tool/              — Python application (replaced on update)
├── projects/          — bind-mount → HOST_PROJECTS (Windows)
└── conf/              — persistent config (never replaced on update)
    ├── local.env
    ├── config.json
    ├── wsl4ai-update.py
    └── ddbb/          — bind-mount → HOST_BASE (Windows)
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

```bash
wsl4ai install update          # apply update if a newer version exists
wsl4ai install update --check  # check without applying
```

The updater (`conf/wsl4ai-update.py`) is a standalone script that is never replaced by updates. It downloads `wsl4ai.py` from GitHub to compare versions, then clones the repository and replaces `tool/` atomically. `conf/` is never touched.

---

## Documentation

| Area | Location |
| ---- | -------- |
| CLI / TUI specifications | [`specs/tool/`](specs/tool/) |
| Bootstrap installer | [`specs/install/`](specs/install/) |
