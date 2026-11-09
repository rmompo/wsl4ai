# WSL4AI

WSL4AI is a **Python CLI and terminal UI (TUI)** for **Linux / WSL** that manages a small **SQLite** catalog: **registries** (mount definitions), per-distro **WSL** rows, and **use** links (bind-mount workflows). It coordinates project locations and tooling across **WSL** and the **Windows** host.

- **Application code:** `tool/` (`wsl4ai` entrypoint, `requirements.txt`) and the install scripts in `tool/scripts/` (basic tools, Claude Code, GitHub Copilot CLI).
- **Persistent config:** `conf/` (`wsl4ai-update.py`, `config.json` — installed to `~/wsl4ai/conf/`, together with `manifest.json`).
- **Versions:** [`manifest.json`](manifest.json) records the version of every component; `wsl4ai version` shows them.
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
│   └── scripts/       — install scripts: basic tools, Claude Code, GitHub Copilot CLI
├── projects/          — bind-mount → HOST_PROJECTS (Windows)
└── conf/              — persistent config (never replaced on update)
    ├── local.env      — HOST_DDBB, WSL_DDBB, HOST_PROJECTS, WSL_PROJECTS
    ├── config.json
    ├── manifest.json  — versions of the installed components
    ├── wsl4ai-update.py
    └── ddbb/          — bind-mount → HOST_DDBB (Windows)
        └── wsl4ai.db
```

---

## Installation

Switch all APT sources from HTTP to HTTPS:

```bash
sed -i 's|http://|https://|g' /etc/apt/sources.list.d/ubuntu.sources
```

Then place `wsl4ai-install.sh` in `/tmp/wsl4ai/` and run it as root. Use `curl` or `wget`:

```bash
mkdir -p /tmp/wsl4ai
curl -fsSL https://raw.githubusercontent.com/rmompo/wsl4ai/main/install/wsl4ai-install.sh -o /tmp/wsl4ai/wsl4ai-install.sh
sudo bash /tmp/wsl4ai/wsl4ai-install.sh
```

```bash
mkdir -p /tmp/wsl4ai
wget -qO /tmp/wsl4ai/wsl4ai-install.sh https://raw.githubusercontent.com/rmompo/wsl4ai/main/install/wsl4ai-install.sh
sudo bash /tmp/wsl4ai/wsl4ai-install.sh
```

The script clones the repository and downloads any missing files automatically. Follow the prompts for `WSL4AI_USER`, `WSL_DDBB`, `WSL_PROJECTS`, `HOST_DDBB`, and `HOST_PROJECTS`.

After installation, exit WSL and run `wsl --terminate <distro>` from Windows to apply all changes.

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

The updater (`conf/wsl4ai-update.py`) is a standalone script that is **never replaced by updates**. It downloads `manifest.json` from GitHub to compare versions, then clones the repository and replaces `tool/` atomically (config and database migrations are applied when needed). `conf/` is otherwise never touched. When a newer updater or installer exists it prints a note with its URL instead of replacing it.

To see the version of every component (tool, config and database schemas, updater, installer and scripts), use `wsl4ai version` (`--remote` compares with GitHub); `wsl4ai info` shows how the distro is set up.

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

### Replace the updater manually

`conf/wsl4ai-update.py` is **never replaced by an update**, so an install made with an older updater keeps it until you replace it by hand. Do it when `wsl4ai version` shows `updater` as `outdated` (or `wsl4ai iu` prints a `NOTE: a newer updater exists`), or when an install predates the manifest (no `~/wsl4ai/conf/manifest.json`). The new updater also saves that manifest and stamps old databases with their schema version.

Run it inside the distro, as the WSL4AI user:

```bash
# 1. Download the new updater to a temporary file and check that it is valid Python
curl -fsSL https://raw.githubusercontent.com/rmompo/wsl4ai/main/conf/wsl4ai-update.py -o /tmp/wsl4ai-update.py
python3 -m py_compile /tmp/wsl4ai-update.py && grep '^__version__' /tmp/wsl4ai-update.py

# 2. Keep a copy of the current one and put the new one in place
cp -a ~/wsl4ai/conf/wsl4ai-update.py ~/wsl4ai/conf/wsl4ai-update.py.bak
mv /tmp/wsl4ai-update.py ~/wsl4ai/conf/wsl4ai-update.py

# 3. Check, then update (--force also writes conf/manifest.json when the tool is already up to date)
wsl4ai install update --check
wsl4ai install update          # add --force if it says "Already up to date" and there is no conf/manifest.json
wsl4ai version                 # every component should now be listed with a version
```

Use `wget -qO /tmp/wsl4ai-update.py <url>` instead of `curl` if you prefer. To take the updater from another branch, replace `main` in the URL. If something goes wrong, restore the copy: `mv ~/wsl4ai/conf/wsl4ai-update.py.bak ~/wsl4ai/conf/wsl4ai-update.py`.

If `wsl4ai` itself does not start, run the updater directly: `python3 ~/wsl4ai/conf/wsl4ai-update.py`.

---

## Usage

```bash
wsl4ai <command>       # CLI mode
wsl4ai tui             # Text User Interface
wsl4ai -v              # Show the tool version
wsl4ai <command> -h    # Help of one command
```

| Command | Shortcut | What it does |
| ------- | -------- | ------------ |
| `wsl4ai whoami` | `wai` | Print the `machine` and `user` of this session |
| `wsl4ai info` | `inf` | Report how this distro is set up: identity, paths, mounts, database, config and AI client |
| `wsl4ai version [--remote]` | `ver` | Version of every component; `--remote` compares with GitHub |
| `wsl4ai registry list / add / remove` | `rl` / `ra` / `rr` | Manage the mount definitions (registries) |
| `wsl4ai use list / add / remove / enable / disable / disableall` | `ul` / `ua` / `ur` / `ue` / `ud` / `uda` | Link this distro to a registry and bind-mount or unmount it |
| `wsl4ai wsl list / set` | `wl` / `ws` | List the known WSL machines and set their launch command |
| `wsl4ai start` | — | Run the launch command of one mounted use |
| `wsl4ai tui` | — | Open the text user interface |
| `wsl4ai install database / alias / update` | `id` / `ia` / `iu` | Create the database, manage shell aliases, update WSL4AI |

Typical order: `registry add` → `use add` → `use enable`; to tear down: `use disable` → `use remove` → `registry remove`.

### Text user interface

`wsl4ai tui` opens a menu bar with the same operations (runtime distro only):

```
Registry  Use  Wsl  Start │ Others │ Exit
```

`Others` holds `Log` (View, Setup), `Theme`, `Install` (Database, Alias) and, at the end, `Info` and `Version`.

---

## WSL distro management

General WSL commands, run from Windows:

Create a WSL distribution with a specific name from a specific image:

```bash
wsl --import <image name> C:\LocalFiles\data\wsl\<image name> C:\tools\ubuntu24.tar.gz
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

---

## Install an AI client

First, make sure the basic tools are there (curl, wget, git, sudo, zip, unzip, jq, ripgrep, nano, Python, build-essential and the rest of what the AI clients and their installers use). The same set the docker-devbox image ships:

```bash
bash ~/wsl4ai/tool/scripts/wsl4ai-install-tools.sh          # installs what is missing (apt, needs sudo)
bash ~/wsl4ai/tool/scripts/wsl4ai-install-tools.sh check    # only lists what is missing
```

Then install the client. Each WSL distro is dedicated to **one** AI client: a script refuses to run if the other client is already installed. Run the one you need inside the distro (they ship with the tool in `~/wsl4ai/tool/scripts/`; `-h` shows their help):

| Client | Script | Installer used | First run |
| ------ | ------ | -------------- | --------- |
| Anthropic Claude Code | `bash ~/wsl4ai/tool/scripts/wsl4ai-install-claudecode.sh` | Official native installer (`claude.ai/install.sh`, about 240 MB, no Node.js) | `claude` — opens the browser to log in; `claude doctor` for diagnostics |
| GitHub Copilot CLI | `bash ~/wsl4ai/tool/scripts/wsl4ai-install-ghcopilot.sh` | Standalone installer (`gh.io/copilot-install`, no Node.js or Homebrew) | `copilot` — log in with your GitHub account |

Both install under `~/.local`; `~/.local/bin` is already on the `PATH` through `~/.startup-wsl4ai.sh`, so no shell reload is needed (open a new shell if the command is not found).

---

## Development

Repository layout:

```
manifest.json      — version of every component
tool/              — Python application (+ tool/scripts/ install scripts)
conf/              — updater and default config
install/           — bootstrap installer, defaults and startup script template
dev/               — development tools (not installed)
specs/             — specifications
```

`manifest.json` records the version of every component (see [`specs/tool/specs-manifest.md`](specs/tool/specs-manifest.md)). When you change one, bump it in the manifest and in the code, then check that they agree:

```bash
python3 dev/check-manifest.py
```

---

## Documentation

| Area | Location |
| ---- | -------- |
| CLI / TUI specifications | [`specs/tool/`](specs/tool/) |
| Bootstrap installer | [`specs/install/`](specs/install/) |
