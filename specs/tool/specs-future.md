# WSL4AI — Future Improvements

This document collects planned or proposed enhancements that are not yet implemented. Each entry describes the motivation, the proposed approach, and the expected scope of change.

---

## 1. Docker mode (`mode: docker`)

### Motivation

The current architecture is WSL-specific: it relies on Windows-backed bind-mounts (`mount --bind /mnt/c/...`) to share the database and project directories across machines. This mechanism is not available in Docker containers.

A Docker-compatible mode would allow WSL4AI to run inside a container where storage is provided by a Docker volume instead of a Windows-mounted filesystem.

### Proposed approach

Introduce a `mode` field in `conf/config.json` with two values: `wsl` (current behaviour) and `docker` (new).

The only two points in the system that differ between modes are:

| Operation | `wsl` mode | `docker` mode |
|-----------|-----------|---------------|
| Install — storage setup | `mount --bind <HOST_PATH> <WSL_PATH>` | No mount; volume is already available at a fixed path |
| `use enable` | `mount --bind <registry_host_path> <registry_wsl_path>` | `ln -s <volume>/<registry_rel_path> <registry_wsl_path>` |
| `use disable` | `umount <registry_wsl_path>` | `rm <registry_wsl_path>` (symlink only) |

All other layers (registry, database, API layer, TUI, CLI, config) remain unchanged — the symlink is transparent to the rest of the application.

### Installer changes

- `install.sh` gains a `--mode wsl|docker` flag (default: `wsl`).
- In `docker` mode the installer skips bind-mount setup and instead records the volume path.
- `defaults.env` is split into `defaults-wsl.env` and `defaults-docker.env`, each with the variables relevant to its mode (see `specs-mode.md`).
- The selected mode is written to `conf/config.json` at install time.

### Config changes

`conf/config.json` gains a top-level `"runtime"` section:

```json
"runtime": {
  "mode": "wsl"
}
```

### Scope of code changes

- `install/install.sh` — mode flag, conditional mount/symlink logic, source correct `defaults-*.env`
- `tool/commands/use_commands.py` / `api.py` — `use enable` and `use disable` branch on `mode`
- `tool/commands/common.py` — expose `runtime.mode` from `config.json`
- `conf/config.json` — new `runtime.mode` field (migration `1.0 → 1.1`)
- `install/defaults.env` → split into `install/defaults-wsl.env` + `install/defaults-docker.env`

See `specs-mode.md` for the full specification.
