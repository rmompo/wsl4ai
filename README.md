# WSL4AI

WSL4AI is a **Python CLI and terminal UI (TUI)** for **Linux / WSL** that manages a small **SQLite** catalog: Windows and WSL path bases, **registries**, per-distro **WSL** rows, and **use** links (mount / enable workflows). It is meant to coordinate project locations and tooling across **WSL** and the **Windows** host.

- **Application code:** `tool/` (`wsl4ai` entrypoint, `requirements.txt`).
- **Product specifications (CLI/TUI):** [`specs/tool/`](specs/tool/).
- **Bootstrap installer (WSL):** [`install/`](install/) — see [`specs/install/installer.md`](specs/install/installer.md).

## Requirements

- **WSL** (or another Linux environment) with Python **3** and dependencies listed in `tool/requirements.txt`.
- For the **automated installer:** **`sudo`**, **`apt-get`** (Debian/Ubuntu-style), **`curl`** or **`wget`** (only if `defaults.env` is not already next to `install.sh`), and **`/mnt/c`** for mounting the shared database path from Windows.

## Install (recommended)

Clone this repository so **`install/`** and **`tool/`** stay side by side, then run the installer **as root**:

```bash
git clone https://github.com/rmompo/wsl4ai.git
cd wsl4ai
sudo bash install/install.sh
```

Follow the prompts (new Linux user, optional default WSL user, paths, host folders for **ddbb** and **projects**). The script copies **`tool/`**, installs **Python** via **apt**, runs **`pip install --user`**, bind-mounts **ddbb**, links **`tool/ddbb`** to that folder, writes **`local.env`** under **`tool/`** (and a copy under **`~/wsl4ai/`**), then runs **`wsl4ai install database`** so SQLite **`parameters`** are seeded from **`HOST_PROJECTS`** / **`WSL_PROJECTS`** in that file.

## Download without `git`

### One file: `install.sh` only

Save **`install.sh`** from GitHub raw (`master`), make it executable, and run it **as root**. If **`defaults.env`** is not next to **`install.sh`**, the script **downloads** it from the same branch on GitHub raw (needs **`curl`** or **`wget`**). You still need the **`tool/`** tree as **`../tool`** relative to **`install/`** (clone or copy).

```bash
mkdir -p install
curl -fsSL https://raw.githubusercontent.com/rmompo/wsl4ai/master/install/install.sh -o install/install.sh
chmod +x install/install.sh
sudo bash install/install.sh
```

```bash
mkdir -p install
wget -qO install/install.sh https://raw.githubusercontent.com/rmompo/wsl4ai/master/install/install.sh
chmod +x install/install.sh
sudo bash install/install.sh
```

## Documentation

| Area | Location |
| ---- | -------- |
| CLI / TUI specifications | [`specs/tool/`](specs/tool/) |
| Bootstrap installer | [`specs/install/`](specs/install/) |
