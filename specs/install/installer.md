# Specification: WSL4AI bootstrap installer (`install/`)

## 1. Purpose

The installer prepares a **dedicated WSL (Linux)** environment for the **WSL4AI CLI/TUI** (`tool/`):

- Creates a Linux user (password initially **identical to the username**).
- Grants **sudo** (or **wheel** on RHEL-style distros).
- Optionally sets **default WSL login user** via `/etc/wsl.conf`.
- Copies the **Python application** from `tool/` next to `install/` into `WSL_BASE/tool/`.
- Installs **Python 3** and **pip** system-wide where **apt** is available.
- Installs **`tool/requirements.txt`** with **`pip install --user`** for the new user.
- **Bind-mounts** the shared database directory on Windows (`HOST_DDBB`) onto `WSL_BASE/ddbb/`.
- Creates a **symbolic link** `WSL_BASE/tool/ddbb` → `WSL_BASE/ddbb` so `wsl4ai.py` (which expects **`tool/ddbb/`** next to the entry script) sees the same files as the shared mount.
- Writes **`local.env`** to **`WSL_TOOL/local.env`** (canonical for the app) and a **copy** to **`~/wsl4ai/local.env`**.
- Runs **`python3 wsl4ai.py install database`** as the **new user** **after** `local.env` exists, so **`install database`** can seed the **`parameters`** table from **`HOST_PROJECTS`** / **`WSL_PROJECTS`** in that file (fallback to built-in defaults if keys are missing).
- **`parameters`** at runtime are still read from SQLite; initial values come from **`local.env`** at DB creation time.

**Out of scope for this document:** business logic of `wsl4ai` commands (see [`../tool/`](../tool/)).

---

## 2. Prerequisites

- Run inside **WSL** with **`/mnt/c`** available (Windows drives mounted).
- Run the script **as root**: `sudo bash install/install.sh`.
- Repository layout: **`install/`** and **`tool/`** as siblings (the installer resolves `../tool` relative to `install.sh`).
- **`install/defaults.env`** supplies **`HOST_DDBB`** / **`HOST_PROJECTS`** (and optional **`WSL_*`** lines). The installer **`source`s** it from the path next to **`install.sh`**. If that file is **missing**, **`install.sh`** downloads it from **GitHub raw** (`master`: `install/defaults.env`) using **`curl`** or **`wget`**, then **`source`s** it. **`HOST_*`** values are **not** embedded in **`install.sh`**.

---

## 3. Configuration: `defaults.env`

The file **`install/defaults.env`** in the repo is the canonical template. At run time it must end up beside **`install.sh`** (from a clone, or downloaded by **`install.sh`** when missing).

**`WSL_BASE`** in that file uses `${HOME}` for illustration only; during **`sudo`** install, **prompt defaults for `WSL_BASE`** are **`/home/<WSL4AI_USER>/wsl4ai/`**, not root’s **`HOME`**.

---

## 4. Interactive prompts (order)

1. **`WSL4AI_USER`** — Linux account to **create** (required; validated; must not exist).
2. **Default WSL user** — whether to set `[user] default=…` in **`/etc/wsl.conf`** (`[y/N]`).
3. **`WSL_BASE`** — default `/home/<WSL4AI_USER>/wsl4ai/` (trailing `/` normalized).
4. Derived (not prompted separately): **`WSL_DDBB`**, **`WSL_TOOL`**, **`WSL_PROJECTS`** = `base + ddbb/`, `tool/`, `projects/`.
5. **`HOST_DDBB`** — Windows path to the shared **ddbb** folder (e.g. `C:/.../ddbb/`).
6. **`HOST_PROJECTS`** — Windows base path for projects (e.g. `C:/.../proyectos/`).

---

## 5. Execution steps (after prompts)

| Step | Action |
| ---- | ------ |
| 4–5 | `useradd`, `chpasswd` (password = username), add to **sudo** or **wheel**. |
| 6 | If requested: update/create **`/etc/wsl.conf`** for default user. |
| 7 | Copy **`tool/`** → **`WSL_TOOL`**, exclude **`ddbb`** if present in source; create **`projects/`**; `chown`. |
| 8 | **`apt-get`**: **`python3`**, **`python3-pip`** (if `apt-get` exists); fail if **`python3`** still missing. |
| 9 | As new user: **`pip install --user`** from **`WSL_TOOL/requirements.txt`**; extend **`.bashrc`** with **`~/.local/bin`** on `PATH` if needed. |
| 10 | **`mount --bind`** host path (`HOST_DDBB` → `/mnt/c/...`) onto **`WSL_DDBB`**; append **`fstab`** line if missing. |
| 11 | **`ln -sfn`** **`WSL_DDBB`** → **`WSL_TOOL/ddbb`** (layout required by `tool/wsl4ai.py`: `APP_DIR / "ddbb"`). |
| — | Write **`local.env`** to **`WSL_TOOL/local.env`** and copy to **`/home/<user>/wsl4ai/local.env`**. |
| 12 | As **`WSL4AI_USER`**: **`cd WSL_TOOL && python3 wsl4ai.py install database`** (creates **`wsl4ai.db`**, seeds **`parameters`** from **`tool/local.env`** when present). |

---

## 6. Output: `local.env`

Written first to **`WSL_TOOL/local.env`** (next to **`wsl4ai.py`**), then copied to **`/home/<WSL4AI_USER>/wsl4ai/local.env`**. Same content; owned by the new user. Contains at least:

- `WSL4AI_USER`, `WSL4AI_SET_DEFAULT_USER`
- `WSL_BASE`, `WSL_DDBB`, `WSL_TOOL`, `WSL_PROJECTS`
- `HOST_DDBB`, `HOST_PROJECTS`, `HOST_DDBB_WSL`

---

## 7. Download without `git` (curl / wget)

### Single raw file: `install.sh`

Operators may save only **`install/install.sh`** from GitHub raw. On first run, if **`defaults.env`** is absent, **`install.sh`** fetches it from raw **`master`** (requires **`curl`** or **`wget`**). **`tool/`** must still exist as **`../tool`**.

```bash
mkdir -p install
curl -fsSL https://raw.githubusercontent.com/rmompo/wsl4ai/master/install/install.sh -o install/install.sh
chmod +x install/install.sh
sudo bash install/install.sh
```

The **`git clone`** flow (see §2) is the other supported way to obtain **`install/`** and **`tool/`** together.

---

## 8. Security notes

- Creating a user with **password equal to username** is weak; acceptable only in controlled dev WSL images.
- **`curl | sudo bash`** patterns trust the network and the script; prefer pinned branch/commit and verify checksums in high-assurance environments.
