# Specification: WSL4AI bootstrap installer (`install/`)

## 1. Purpose

The installer prepares a **dedicated WSL (Linux)** environment for the **WSL4AI CLI/TUI** (`tool/`):

- Creates a Linux user (password initially **identical to the username**).
- Grants **sudo** (or **wheel** on RHEL-style distros).
- Sets **default WSL login user** via `/etc/wsl.conf`.
- Copies the **Python application** from `tool/` into `INSTALL_TOOL`.
- Copies **`conf/`** contents (`wsl4ai-update.py`, `config.json`) into `INSTALL_CONF` (skips `config.json` if already present).
- Installs **Python 3**, **pip**, and **git** system-wide via **apt**.
- Installs **`tool/requirements.txt`** with **`pip install --user`** for the new user.
- Creates the `WSL_DDBB` and `WSL_PROJECTS` mount point directories.
- Copies **`.startup-wsl4ai.sh`** to the new user's `~`, with paths resolved.
- Configures **`.bashrc`** to source `~/.startup-wsl4ai.sh` on shell start.
- Writes **`local.env`** with the four environment variables.
- Runs **`python3 wsl4ai.py install database`** as the new user.
- Prints a final message instructing to run **`wsl --shutdown`** from Windows.

**Out of scope for this document:** business logic of `wsl4ai` commands (see [`../tool/`](../tool/)).

---

## 2. Prerequisites

- Run inside **WSL** with **`/mnt/c`** available (Windows drives mounted).
- Run the script **as root**: `sudo bash /tmp/wsl4ai/install.sh`.
- Script must be placed in **`/tmp/wsl4ai/`** and run from there.
- **`install/defaults.env`** supplies default values for the interactive prompts. If missing, **`install.sh`** downloads it from GitHub raw (`main` branch) using **`curl`** or **`wget`**.
- **`tool/`** must be present at `/tmp/wsl4ai/tool/`. If missing, `install.sh` clones it from GitHub (requires **`git`**, installed in the apt step first).
- **`conf/`** must be present at `/tmp/wsl4ai/conf/`. Obtained from the same clone as `tool/`.

---

## 3. Configuration: `defaults-{mode}.env`

> **Current state:** a single `install/defaults.env` is used. The split into mode-specific files is planned — see `specs-future.md §1` and `specs-mode.md §4.2`.

Provides default values for the interactive prompts. The file loaded depends on the `--mode` flag passed to `install.sh` (default: `wsl`). If the file is absent, `install.sh` downloads it from GitHub.

### `defaults-wsl.env`

| Variable | Role |
| -------- | ---- |
| `WSL_DDBB` | WSL mount point for the shared database directory |
| `WSL_PROJECTS` | WSL mount point for the projects directory |
| `HOST_DDBB` | Windows path to the shared database directory |
| `HOST_PROJECTS` | Windows path to the projects directory |

```
WSL_DDBB=${HOME}/wsl4ai/conf/ddbb
WSL_PROJECTS=${HOME}/wsl4ai/proyectos
HOST_DDBB=C:/wsl2data/wsl4ai/ddbb
HOST_PROJECTS=C:/LocalFiles/proyectos
```

### `defaults-docker.env`

| Variable | Role |
| -------- | ---- |
| `WSL_DDBB` | Path to database directory inside the container |
| `WSL_PROJECTS` | Path to projects directory inside the container |
| `DOCKER_VOLUME_PATH` | Root path of the Docker volume |

```
WSL_DDBB=${HOME}/wsl4ai/conf/ddbb
WSL_PROJECTS=${HOME}/wsl4ai/proyectos
DOCKER_VOLUME_PATH=/mnt/wsl4ai
```

---

## 4. Interactive prompts (order)

1. **`WSL4AI_USER`** — Linux account to create (required; validated; must not already exist).
2. **`WSL_DDBB`** — WSL mount point for the shared ddbb directory (default from `defaults.env`, `${HOME}` replaced with actual user home).
3. **`WSL_PROJECTS`** — WSL mount point for the projects directory (default from `defaults.env`).
4. **`HOST_DDBB`** — Windows path to the shared database directory (default from `defaults.env`).
5. **`HOST_PROJECTS`** — Windows path to the projects directory (default from `defaults.env`).

**Internal variables** (derived from `WSL_DDBB`; not stored in `local.env`; not prompted):

| Variable | Value |
| -------- | ----- |
| `INSTALL_BASE` | `dirname(dirname(WSL_DDBB))` — root of the WSL4AI installation |
| `INSTALL_CONF` | `INSTALL_BASE/conf/` |
| `INSTALL_TOOL` | `INSTALL_BASE/tool/` |

The default WSL login user is **always set** to `WSL4AI_USER` (no prompt).

---

## 5. Execution steps (after prompts)

| Step | Action |
| ---- | ------ |
| 1 | `apt-get update` |
| 2 | `apt-get upgrade` |
| 3 | `apt-get install git python3 python3-pip` |
| 4 | `useradd`, `chpasswd` (password = username), add to **sudo** or **wheel**. |
| 5 | Update/create **`/etc/wsl.conf`** `[user] default=<WSL4AI_USER>`. |
| 6 | Copy **`tool/`** → **`INSTALL_TOOL`**; `chown`. |
| 7 | As new user: **`pip install --user`** from **`INSTALL_TOOL/requirements.txt`**; add to **`.bashrc`**: `source ~/.startup-wsl4ai.sh`. |
| 8 | Create mount point directories: `WSL_DDBB` and `WSL_PROJECTS` (and their Windows-side counterparts). |
| 8b | Copy **`.startup-wsl4ai.sh`** template to `~/.startup-wsl4ai.sh`, replacing `__INSTALL_BASE__` with the resolved `INSTALL_BASE` path. |
| 9 | Write **`local.env`** → `INSTALL_CONF`; copy `wsl4ai-update.py` and `config.json` from repo `conf/` into `INSTALL_CONF` (`config.json` skipped if already present); `chown`. |
| 10 | As **`WSL4AI_USER`**: **`cd INSTALL_TOOL && python3 wsl4ai.py install database`**. |
| — | Print final message: exit WSL and run `wsl --shutdown` from Windows. |

---

## 6. Layout after installation

```
~/.startup-wsl4ai.sh       — startup script (sourced by .bashrc)
~/.bashrc                  — sources ~/.startup-wsl4ai.sh

~/wsl4ai/                  ← INSTALL_BASE
├── tool/                  ← INSTALL_TOOL — Python application (replaced on update)
├── proyectos/             ← WSL_PROJECTS — bind-mount → HOST_PROJECTS (Windows)
├── .tmp/                  — temporary working directory (used by updater)
└── conf/                  ← INSTALL_CONF — persistent configuration (never replaced on update)
    ├── local.env
    ├── config.json
    ├── wsl4ai-update.py
    └── ddbb/              ← WSL_DDBB — bind-mount → HOST_DDBB (Windows)
        └── wsl4ai.db
```

**Windows side:**
```
HOST_DDBB/                 — shared across WSL machines (e.g. C:/…/wsl4ai/ddbb/)
  wsl4ai.db
HOST_PROJECTS/             — per-machine (e.g. C:/LocalFiles/proyectos/)
```

---

## 7. Output: `local.env`

Written to **`INSTALL_CONF/local.env`**. Owned by the new user. Read at runtime by `~/.startup-wsl4ai.sh` and by `tool/commands/common.py`.

| Variable | Value |
| -------- | ----- |
| `HOST_DDBB` | Windows path to the shared database directory |
| `WSL_DDBB` | WSL mount point for the database directory |
| `HOST_PROJECTS` | Windows path to the projects directory |
| `WSL_PROJECTS` | WSL mount point for the projects directory |

---

## 8. `~/.startup-wsl4ai.sh` (sourced by `.bashrc`)

Installed from `install/.startup-wsl4ai.sh` template. The only placeholder substituted at install time is `__INSTALL_BASE__`.

Sections in order:

1. **Load config** — `source INSTALL_BASE/conf/local.env`
2. **Automatic mounts** — waits for `/mnt/c`, then bind-mounts `HOST_DDBB` → `WSL_DDBB` and `HOST_PROJECTS` → `WSL_PROJECTS` if not already mounted.
3. **Environment setup** — extends `PATH` with `~/.local/bin`; `cd ~`.
4. **Aliases** — managed block between markers `# >>> WSL4AI BEGIN >>>` / `# <<< WSL4AI END <<<`; default alias is `wsl4ai()`.
5. **Welcome banner** — calls `python3 INSTALL_BASE/tool/wsl4ai.py -v`, then `use disableall --quiet`, then prints usage hints.

---

## 9. Download and run

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

`defaults.env` and `tool/` are downloaded automatically if not present in `/tmp/wsl4ai/`.

---

## 10. Security notes

- Creating a user with **password equal to username** is weak; acceptable only in controlled dev WSL images.
- The script requires and enforces execution from `/tmp/wsl4ai/`.
