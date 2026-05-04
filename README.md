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

## Directory layout

```
~/.startup-wsl4ai.sh       — startup script (sourced by .bashrc; manages mounts and aliases)

~/wsl4ai/
├── tool/              — Python application (replaced on update)
├── extras/            — optional startup scripts for other WSL distros
├── proyectos/         — bind-mount → HOST_PROJECTS (Windows)
└── conf/              — persistent config (never replaced on update)
    ├── local.env      — HOST_DDBB, WSL_DDBB, HOST_PROJECTS, WSL_PROJECTS
    ├── config.json
    ├── wsl4ai-update.py
    └── ddbb/          — bind-mount → HOST_DDBB (Windows)
        └── wsl4ai.db
```

---

## Installation

### Assisted

Switch all APT sources from HTTP to HTTPS:

```bash
sed -i 's|http://|https://|g' /etc/apt/sources.list.d/ubuntu.sources
```

Then place `install.sh` in `/tmp/wsl4ai/` and run it as root. Use `curl` or `wget`:

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

The script clones the repository and downloads any missing files automatically. Follow the prompts for `WSL4AI_USER`, `WSL_DDBB`, `WSL_PROJECTS`, `HOST_DDBB`, and `HOST_PROJECTS`.

After installation, exit WSL and run `wsl --terminate <distro>` from Windows to apply all changes.

---

### Manual

Perform the following steps **as root** (`sudo -i` or prefix each command with `sudo`).

**Variables** — set these to match your environment before running the commands below:

```bash
WSL4AI_USER="wsl4ai"                            # Linux account to create
INSTALL_BASE="/home/${WSL4AI_USER}/wsl4ai"      # application root
WSL_DDBB="${INSTALL_BASE}/conf/ddbb/"           # WSL path for the database bind-mount
WSL_PROJECTS="${INSTALL_BASE}/proyectos/"       # WSL path for the projects bind-mount
HOST_DDBB="C:/wsl2data/wsl4ai/ddbb/"           # Windows path for the database
HOST_PROJECTS="C:/LocalFiles/proyectos/"        # Windows path for projects
```

---

**Step 1 — switch APT sources to HTTPS**

```bash
sed -i 's|http://|https://|g' /etc/apt/sources.list.d/ubuntu.sources
```

---

**Step 2 — system packages**

```bash
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get upgrade -y
apt-get install -y git python3 python3-pip
```

---

**Step 3 — clone repository**

```bash
mkdir -p /tmp/wsl4ai
git clone --depth=1 --branch main https://github.com/rmompo/wsl4ai.git /tmp/wsl4ai/repo
```

---

**Step 4 — create Linux user**

Password is set to the username; change it after first login.

```bash
useradd -m -s /bin/bash "${WSL4AI_USER}"
echo "${WSL4AI_USER}:${WSL4AI_USER}" | chpasswd
usermod -aG sudo "${WSL4AI_USER}"
```

---

**Step 5 — set default WSL login user**

```bash
printf '[user]\ndefault=%s\n' "${WSL4AI_USER}" > /etc/wsl.conf
```

If `/etc/wsl.conf` already exists, add or update the `default=` line under `[user]` instead of overwriting the file.

---

**Step 6 — copy tool/**

```bash
mkdir -p "${INSTALL_BASE}/tool"
cp -a /tmp/wsl4ai/repo/tool/. "${INSTALL_BASE}/tool/"
chown -R "${WSL4AI_USER}:${WSL4AI_USER}" "${INSTALL_BASE}/tool"
```

---

**Step 7 — install pip dependencies**

```bash
sudo -u "${WSL4AI_USER}" -H env HOME="/home/${WSL4AI_USER}" bash -lc \
  'python3 -m pip install --user --upgrade pip --break-system-packages && \
   python3 -m pip install --user --break-system-packages -r ~/wsl4ai/tool/requirements.txt'
```

---

**Step 8 — configure .bashrc**

```bash
BASHRC="/home/${WSL4AI_USER}/.bashrc"
[[ -f "${BASHRC}" ]] || { touch "${BASHRC}"; chown "${WSL4AI_USER}:${WSL4AI_USER}" "${BASHRC}"; }
printf '\n# Custom WSL4AI startup scripts\ncd ~\nsource ~/.startup-wsl4ai.sh\n' >> "${BASHRC}"
chown "${WSL4AI_USER}:${WSL4AI_USER}" "${BASHRC}"
```

---

**Step 9 — create mount point directories**

Convert Windows paths to WSL mount paths (`C:/foo/bar` → `/mnt/c/foo/bar`):

```bash
HOST_DDBB_WSL="/mnt/c/wsl2data/wsl4ai/ddbb"      # adjust drive letter / path
HOST_PROJECTS_WSL="/mnt/c/LocalFiles/proyectos"   # adjust drive letter / path

sudo -u "${WSL4AI_USER}" -H mkdir -p "${WSL_DDBB}" "${WSL_PROJECTS}"
mkdir -p "${HOST_DDBB_WSL}" "${HOST_PROJECTS_WSL}"
```

Apply the bind-mount immediately so the database is written to the host path:

```bash
mount --bind "${HOST_DDBB_WSL}" "${WSL_DDBB%/}"
```

---

**Step 10 — install .startup-wsl4ai.sh**

```bash
sed "s|__INSTALL_BASE__|${INSTALL_BASE}|g" \
    /tmp/wsl4ai/repo/install/.startup-wsl4ai.sh \
    > "/home/${WSL4AI_USER}/.startup-wsl4ai.sh"
chmod +x "/home/${WSL4AI_USER}/.startup-wsl4ai.sh"
chown "${WSL4AI_USER}:${WSL4AI_USER}" "/home/${WSL4AI_USER}/.startup-wsl4ai.sh"
```

---

**Step 11 — configure sudoers for bind-mounts**

```bash
MOUNT_BIN="$(command -v mount)"
UMOUNT_BIN="$(command -v umount)"
cat > /etc/sudoers.d/wsl4ai-mount <<EOF
${WSL4AI_USER} ALL=(root) NOPASSWD: ${MOUNT_BIN} --bind ${HOST_DDBB_WSL} ${WSL_DDBB}
${WSL4AI_USER} ALL=(root) NOPASSWD: ${MOUNT_BIN} --bind * ${WSL_PROJECTS}*
${WSL4AI_USER} ALL=(root) NOPASSWD: ${UMOUNT_BIN} ${WSL_PROJECTS}*
EOF
chmod 440 /etc/sudoers.d/wsl4ai-mount
```

---

**Step 12 — write conf/**

```bash
INSTALL_CONF="${INSTALL_BASE}/conf/"
mkdir -p "${INSTALL_CONF}"

# local.env
cat > "${INSTALL_CONF}local.env" <<EOF
# Generated manually — edit to change.
HOST_DDBB=${HOST_DDBB}
WSL_DDBB=${WSL_DDBB}
HOST_PROJECTS=${HOST_PROJECTS}
WSL_PROJECTS=${WSL_PROJECTS}
EOF

# updater script and default config
cp -a /tmp/wsl4ai/repo/conf/wsl4ai-update.py "${INSTALL_CONF}wsl4ai-update.py"
[[ -f "${INSTALL_CONF}config.json" ]] || cp -a /tmp/wsl4ai/repo/conf/config.json "${INSTALL_CONF}config.json"

chown -R "${WSL4AI_USER}:${WSL4AI_USER}" "${INSTALL_CONF}"
```

---

**Step 13 — create the SQLite database**

```bash
sudo -u "${WSL4AI_USER}" -H env HOME="/home/${WSL4AI_USER}" bash -lc \
  "cd ${INSTALL_BASE}/tool && python3 wsl4ai.py install database"
```

---

**Step 14 — restart WSL**

From Windows PowerShell or CMD:

```powershell
wsl --terminate <distro-name>
```

Then re-open the distro. The startup script runs automatically, mounts the directories, and makes the `wsl4ai` alias available.

---

## Update

Check whether a newer version is available without applying it:

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

### Update from a specific branch

Use `-b` / `--branch` to check or apply an update from a branch other than `main` (e.g. a feature or release-candidate branch):

```bash
wsl4ai install update --branch feature/TUI-Textual
wsl4ai iu -b feature/TUI-Textual              # shorthand

# check only, without applying
wsl4ai install update --check --branch feature/TUI-Textual
wsl4ai iu --check -b feature/TUI-Textual
```

The updater can also be run directly when the CLI is unavailable:

```bash
python3 ~/wsl4ai/conf/wsl4ai-update.py -b feature/TUI-Textual
python3 ~/wsl4ai/conf/wsl4ai-update.py --check -b feature/TUI-Textual
```

> **Warning:** Branches other than `main` may contain unstable or experimental code. Use only for testing purposes.

---

## Usage

```bash
wsl4ai <command>       # CLI mode
wsl4ai tui             # Text User Interface
wsl4ai -v              # Show version
```

---

## WSL configuration guides

General WSL commands you may need before following a tool-specific guide:

Create a WSL distribution with a specific name from a specific image:

```bash
wsl --import <image name> c:\wsl2data\<image name> C:\tools\ubuntu24.tar.gz
```

Start a specific WSL distribution:

```bash
wsl --distribution <image name>
```

Terminate a specific WSL distribution so it fully stops and reloads `wsl.conf` on the next start:

```bash
wsl --terminate <image name>
```

Completely remove a specific WSL distribution:

```bash
wsl --unregister <image name>
```

Step-by-step setup guides for WSL distros dedicated to specific AI tools:

| Guide | Tool | Method |
| ----- | ---- | ------ |
| [`wsls/wsl4codexcli.md`](wsls/wsl4codexcli.md) | OpenAI Codex CLI | Homebrew |
| [`wsls/wsl4claudecode.md`](wsls/wsl4claudecode.md) | Anthropic Claude Code | Native installer |
| [`wsls/wsl4ghcopilot.md`](wsls/wsl4ghcopilot.md) | GitHub Copilot CLI | Homebrew + gh extension |

Each guide covers prerequisites, installation, authentication, and startup script configuration.

---

## Documentation

| Area | Location |
| ---- | -------- |
| CLI / TUI specifications | [`specs/tool/`](specs/tool/) |
| Bootstrap installer | [`specs/install/`](specs/install/) |
