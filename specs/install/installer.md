# Specification: WSL4AI bootstrap installer (`install/`)

## 1. Purpose

The installer prepares a **dedicated WSL (Linux)** environment for the **WSL4AI CLI/TUI** (`tool/`):

- Creates a Linux user (password initially **identical to the username**).
- Grants **sudo** (or **wheel** on RHEL-style distros).
- Sets **default WSL login user** via `/etc/wsl.conf` (always; no prompt).
- Copies the **Python application** from `tool/` into `WSL_BASE/tool/`.
- Installs **Python 3**, **pip**, and **git** system-wide via **apt**.
- Installs **`tool/requirements.txt`** with **`pip install --user`** for the new user.
- **Bind-mounts** the shared database directory on Windows (`HOST_DDBB`) onto `WSL_BASE/ddbb/`.
- Creates a **symbolic link** `WSL_BASE/tool/ddbb` → `WSL_BASE/ddbb/` so `wsl4ai.py` sees the shared files.
- Writes **`local.env`** to **`WSL_TOOL/local.env`** (only location; no copy elsewhere).
- Configures **`.bashrc`** of the new user: PATH, `cd ~`, `wsl4ai` alias, safety `disableall --quiet`, welcome message.
- Runs **`python3 wsl4ai.py install database`** as the new user after `local.env` exists.
- Prints a final message instructing to run **`wsl --shutdown`** from Windows.

**Out of scope for this document:** business logic of `wsl4ai` commands (see [`../tool/`](../tool/)).

---

## 2. Prerequisites

- Run inside **WSL** with **`/mnt/c`** available (Windows drives mounted).
- Run the script **as root**: `sudo bash /tmp/wsl4ai/install.sh`.
- Script must be placed in **`/tmp/wsl4ai/`** and run from there.
- **`install/defaults.env`** supplies **`HOST_DDBB`** / **`HOST_PROJECTS`** defaults. If missing, **`install.sh`** downloads it from GitHub raw (`main` branch) using **`curl`** or **`wget`**.
- **`tool/`** must be present at `/tmp/wsl4ai/tool/`. If missing, `install.sh` clones it from GitHub (requires **`git`**, installed in the apt step first).

---

## 3. Configuration: `defaults.env`

Provides default values for the interactive prompts:

| Variable | Role |
| -------- | ---- |
| `HOST_DDBB` | Windows path to shared ddbb folder |
| `HOST_PROJECTS` | Windows base path for projects |

`WSL_BASE`, `WSL_DDBB`, `WSL_TOOL`, `WSL_PROJECTS` are derived from the prompted `WSL_BASE` value; they are not in `defaults.env`.

---

## 4. Interactive prompts (order)

1. **`WSL4AI_USER`** — Linux account to create (required; validated; must not already exist).
2. **`WSL_BASE`** — default `/home/<WSL4AI_USER>/wsl4ai/` (trailing `/` normalized).
3. Derived (not prompted): **`WSL_DDBB`**, **`WSL_TOOL`**, **`WSL_PROJECTS`** = `base + ddbb/`, `tool/`, `projects/`.
4. **`HOST_DDBB`** — Windows path to the shared ddbb folder.
5. **`HOST_PROJECTS`** — Windows base path for projects.

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
| 6 | Copy **`tool/`** → **`WSL_TOOL`** (exclude `ddbb/` if present in source); create **`projects/`**; `chown`. |
| 7 | As new user: **`pip install --user`** from **`WSL_TOOL/requirements.txt`**; extend **`.bashrc`** with PATH, `cd ~`, `wsl4ai` alias, `wsl4ai use disableall --quiet`, and welcome message. |
| 8 | **`mount --bind`** (`HOST_DDBB` → `/mnt/c/...`) onto **`WSL_DDBB`**; append **`fstab`** line if missing. |
| 9 | **`ln -sfn`** **`WSL_DDBB`** → **`WSL_TOOL/ddbb`**. |
| 10 | Write **`local.env`** to **`WSL_TOOL/local.env`** only; `chown` to new user. |
| 11 | As **`WSL4AI_USER`**: **`cd WSL_TOOL && python3 wsl4ai.py install database`**. |
| — | Print final message: exit WSL and run `wsl --shutdown` from Windows. |

---

## 6. Output: `local.env`

Written to **`WSL_TOOL/local.env`** only (next to `wsl4ai.py`). Owned by the new user. Contains:

| Variable | Value |
| -------- | ----- |
| `WSL_BASE` | Base directory for the WSL4AI installation |
| `WSL_DDBB` | Path to the shared database directory |
| `WSL_TOOL` | Path to the tool directory |
| `WSL_PROJECTS` | Path to the WSL projects directory |
| `HOST_DDBB` | Windows path to the shared ddbb folder |
| `HOST_PROJECTS` | Windows base path for projects |
| `HOST_DDBB_WSL` | `/mnt/...` translation of `HOST_DDBB` |

`WSL4AI_USER` and `WSL4AI_SET_DEFAULT_USER` are **not** written to `local.env` (installer-only variables).

---

## 7. `.bashrc` additions (new user)

Added in order, each guarded by a grep check to avoid duplicates on re-run:

1. `export PATH="${HOME}/.local/bin:${PATH}"` — pip --user scripts.
2. `cd ~` — start every session in home directory.
3. `alias wsl4ai="python3 <WSL_TOOL>/wsl4ai.py"` — main command alias.
4. `wsl4ai use disableall --quiet` — safety call on session start.
5. Welcome message:
   ```
   WSL4AI ready
     cli: wsl4ai <command>
     tui: wsl4ai tui
   ```

---

## 8. Download and run (without `git` pre-installed)

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

## 9. Security notes

- Creating a user with **password equal to username** is weak; acceptable only in controlled dev WSL images.
- The script requires and enforces execution from `/tmp/wsl4ai/`.
