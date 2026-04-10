# WSL4AI — Runtime Mode Specification

> **Status: planned** — not yet implemented. See `specs-future.md §1`.

This document specifies the `mode` field in `conf/config.json`, the behaviour differences between `wsl` and `docker` modes, and the required changes to the installer and tool.

---

## 1. Overview

WSL4AI supports two runtime modes:

| Mode | Storage mechanism | Target environment |
|------|------------------|--------------------|
| `wsl` | `mount --bind` (Windows-backed v9fs) | WSL2 instance |
| `docker` | Docker volume + symlinks | Docker container |

The mode is set once at install time and stored in `conf/config.json`. It is read at runtime by the tool to determine how `use enable` and `use disable` operate.

---

## 2. Config field

`conf/config.json` — `runtime` section (schema version `1.1`):

```json
{
  "metadata": {
    "schema_version": "1.1"
  },
  "runtime": {
    "mode": "wsl"
  },
  "tui": { ... },
  "log": { ... }
}
```

| Section | Key | Type | Values | Default | Description |
|---------|-----|------|--------|---------|-------------|
| `runtime` | `mode` | string | `"wsl"` · `"docker"` | `"wsl"` | Runtime storage mode |

---

## 3. Behaviour differences

### 3.1 `use enable`

| Mode | Action |
|------|--------|
| `wsl` | `mount --bind <registry_host_path> <registry_wsl_path>` |
| `docker` | `ln -s <volume>/<registry_rel_path> <registry_wsl_path>` |

### 3.2 `use disable`

| Mode | Action |
|------|--------|
| `wsl` | `umount <registry_wsl_path>` |
| `docker` | `rm <registry_wsl_path>` (removes symlink only; never touches volume contents) |

### 3.3 Everything else

Registry management, the database, the API layer, the TUI, and the CLI are **identical** in both modes. The symlink is transparent to all consumers.

---

## 4. Installer changes

### 4.1 `install.sh` — new flag

```
--mode wsl|docker    Runtime mode (default: wsl)
```

### 4.2 `defaults.env` split

The single `install/defaults.env` is replaced by two mode-specific files:

**`install/defaults-wsl.env`**

```bash
WSL_DDBB=${HOME}/wsl4ai/conf/ddbb
WSL_PROJECTS=${HOME}/wsl4ai/proyectos
HOST_DDBB=C:/wsl2data/wsl4ai/ddbb
HOST_PROJECTS=C:/LocalFiles/proyectos
```

**`install/defaults-docker.env`**

```bash
WSL_DDBB=${HOME}/wsl4ai/conf/ddbb
WSL_PROJECTS=${HOME}/wsl4ai/proyectos
DOCKER_VOLUME_PATH=/mnt/wsl4ai
```

The installer loads the file matching the selected mode. If the file is missing, `install.sh` downloads it from GitHub using the URL pattern:

```
https://raw.githubusercontent.com/rmompo/wsl4ai/main/install/defaults-{mode}.env
```

### 4.3 `local.env` contents per mode

**`wsl` mode** (current — unchanged):

| Variable | Description |
|----------|-------------|
| `HOST_DDBB` | Windows path to shared database directory |
| `WSL_DDBB` | WSL mount point for the database directory |
| `HOST_PROJECTS` | Windows path to projects directory |
| `WSL_PROJECTS` | WSL mount point for projects directory |

**`docker` mode** (new):

| Variable | Description |
|----------|-------------|
| `WSL_DDBB` | Path to database directory inside the container |
| `WSL_PROJECTS` | Path to projects directory inside the container |
| `DOCKER_VOLUME_PATH` | Root path of the Docker volume (e.g. `/mnt/wsl4ai`) |

### 4.4 Storage setup per mode

**`wsl` mode** (current):
```bash
mkdir -p "$WSL_DDBB" "$WSL_PROJECTS"
# mount --bind executed at shell startup via .startup-wsl4ai.sh
```

**`docker` mode**:
```bash
mkdir -p "$WSL_DDBB" "$WSL_PROJECTS"
# No bind-mount; volume is already available at DOCKER_VOLUME_PATH
# .startup-wsl4ai.sh skips the mount --bind section in docker mode
```

### 4.5 Config written at install

The installer writes `runtime.mode` to `conf/config.json`:

```json
"runtime": {
  "mode": "wsl"
}
```

---

## 5. Tool changes

### 5.1 `common.py`

Add `runtime_mode()` helper:

```python
def runtime_mode() -> str:
    """Return 'wsl' or 'docker' from config.json runtime.mode (default: 'wsl')."""
```

### 5.2 `api.py` — `api_use_enable` / `api_use_disable`

Both functions branch on `runtime_mode()`:

```python
mode = runtime_mode()
if mode == "docker":
    # symlink logic
else:
    # mount --bind logic  (current behaviour)
```

### 5.3 `.startup-wsl4ai.sh`

The automatic-mounts section is guarded by the mode:

```bash
MODE=$(python3 "$INSTALL_BASE/tool/wsl4ai.py" config get runtime.mode 2>/dev/null || echo wsl)
if [ "$MODE" = "wsl" ]; then
    # existing mount --bind logic
fi
```

---

## 6. Config migration

When this feature is implemented, a config migration `1.0 → 1.1` will add `runtime.mode = "wsl"` to existing installations (preserving current behaviour):

```python
def _migrate_1_0_to_1_1(config: dict) -> dict:
    config.setdefault("runtime", {})["mode"] = "wsl"
    return config
```

---

## 7. Layout after installation (docker mode)

```
~/wsl4ai/                    ← INSTALL_BASE
├── tool/                    ← Python application
├── proyectos/               ← WSL_PROJECTS (plain directory; symlinks created here by use enable)
└── conf/
    ├── local.env
    ├── config.json          ← runtime.mode = "docker"
    ├── wsl4ai-update.py
    └── ddbb/
        └── wsl4ai.db

/mnt/wsl4ai/                 ← DOCKER_VOLUME_PATH (Docker volume mount point)
├── ddbb/
│   └── wsl4ai.db            (volume copy synced or shared)
└── proyectos/
    ├── project-a/           ← symlinked as ~/wsl4ai/proyectos/project-a → here
    └── project-b/
```
