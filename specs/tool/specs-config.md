# WSL4AI Configuration and Update Specification

This document covers the persistent configuration file (`conf/config.json`), its schema versioning, and the tool update procedure.

---

## 1. Overview

| File | Location | Managed by |
|------|----------|-----------|
| `config.json` | `~/wsl4ai/conf/config.json` | User + auto-migrations |
| `wsl4ai-update.py` | `~/wsl4ai/conf/wsl4ai-update.py` | User (never replaced by updates) |
| `local.env` | `~/wsl4ai/conf/local.env` | User (never replaced by updates) |

The `conf/` directory is **never modified by tool updates**. Its contents persist across all `wsl4ai install update` runs.

---

## 2. Config file structure

```json
{
  "metadata": {
    "schema_version": "1.0",
    "changelog": [
      {
        "schema_version": "1.0",
        "datetime": "2026-04-10T12:34:56",
        "comment": "added metadata section; config without metadata treated as pre-1.0"
      }
    ]
  },
  "tui": {
    "theme": "normal_dark"
  },
  "log": {
    "level": "WARNING",
    "file":  "logs/wsl4ai.log"
  }
}
```

### 2.1 Sections

| Section | Key | Type | Default | Description |
|---------|-----|------|---------|-------------|
| `metadata` | `schema_version` | string | *(required)* | Current config schema version (e.g. `"1.0"`) |
| `metadata` | `changelog` | array | `[]` | Migration history — one entry per applied migration |
| `tui` | `theme` | string | `"normal_dark"` | Active TUI theme ID (see §7.0 in `specs-tui.md`) |
| `log` | `level` | string | `"WARNING"` | Log level: `DEBUG` · `INFO` · `WARNING` · `ERROR` · `NONE` |
| `log` | `file` | string | `"logs/wsl4ai.log"` | Log file path (relative to `tool/` or absolute; `~` and `$HOME` expanded) |

### 2.2 metadata section

The `metadata` section is mandatory in schema `≥ 1.0`. Its purpose is to allow the tool and updater to detect whether config migrations are needed.

```json
"metadata": {
  "schema_version": "1.0",
  "changelog": [
    {
      "schema_version": "1.0",
      "datetime": "2026-04-10T12:34:56",
      "comment": "human-readable description of what this migration did"
    }
  ]
}
```

- `schema_version`: string in `major.minor` format (e.g. `"1.0"`). Compared numerically.
- `changelog`: append-only list. Each entry documents one migration step applied to this installation.
- Config without a `metadata` section is treated as **pre-1.0** and will be migrated on next update.

### 2.3 log.file resolution rules

| Value | Resolves to |
|-------|-------------|
| `"logs/wsl4ai.log"` | `~/wsl4ai/tool/logs/wsl4ai.log` (relative to `tool/`) |
| `"/var/log/wsl4ai.log"` | `/var/log/wsl4ai.log` (absolute — used as-is) |
| `"~/mylog.log"` | `$HOME/mylog.log` (`~` expanded) |
| A directory path | Appends default filename `wsl4ai.log` |

The log directory is created automatically if it does not exist.

### 2.4 log.level values

| Value | Behavior |
|-------|----------|
| `DEBUG` | All messages |
| `INFO` | Info, warnings, errors |
| `WARNING` | Warnings and errors (default) |
| `ERROR` | Errors only |
| `NONE` | Logging disabled entirely |

---

## 3. Schema versioning

The config schema version is **independent of the tool version** (`__version__` in `wsl4ai.py`). They evolve separately:

| Identifier | Located in | Controls |
|------------|-----------|---------|
| `__version__` | `tool/wsl4ai.py` | Tool release version |
| `__config_version__` | `tool/wsl4ai.py` | Minimum config schema the tool requires |
| `metadata.schema_version` | `conf/config.json` | Schema version of this installation's config |

The tool aborts at startup if `config.json` exists and its `metadata.schema_version` is lower than `__config_version__`. Error message:

```
Error: config schema is 0.9 but tool requires 1.0. Run: wsl4ai install update
```

Install commands (`install`, `it`, `id`, `ia`, `iu`) bypass this check — they handle setup and migration.

---

## 4. Update procedure

### 4.1 Commands

| Command | Action |
|---------|--------|
| `wsl4ai install update` | Check and apply update (tool + config migrations) |
| `wsl4ai iu` | Shorthand |
| `wsl4ai install update --check` | Check only — print available update and pending migrations, do not apply |
| `wsl4ai iu --check` | Shorthand |
| `wsl4ai iu -b <branch>` | Update from a specific branch (default: `main`) |
| `wsl4ai iu --check -b <branch>` | Check from a specific branch |

The updater can also be run directly when the CLI is unavailable:

```bash
python3 ~/wsl4ai/conf/wsl4ai-update.py
python3 ~/wsl4ai/conf/wsl4ai-update.py --check
python3 ~/wsl4ai/conf/wsl4ai-update.py -b feature/TUI-Textual
```

### 4.2 Update steps

```
Local version : 1.5.90
Branch        : main
Checking remote version...
Remote version: 1.5.96
Updating 1.5.90 -> 1.5.96...
Cloning repository...
Installing dependencies...

WSL4AI Update Summary
  Branch      : main
  Tool        : 1.5.90 -> 1.5.96
  Download    : OK
  pip install : OK
  Config      : pre-1.0 -> 1.0  added metadata section with schema_version and changelog
```

**Step-by-step:**

1. Read local `tool/wsl4ai.py` → extract `__version__` (local tool version).
2. Download remote `wsl4ai.py` from `https://raw.githubusercontent.com/rmompo/wsl4ai/{branch}/tool/wsl4ai.py`.
3. Extract remote `__version__` and `__config_version__` from downloaded file.
4. Compute pending config migrations by comparing local `config.json` schema with remote `__config_version__`.
5. If local version ≥ remote AND no pending config migrations → print "Already up to date." and exit.
6. If `--check` → print available update and pending migration list; **do not apply**; exit.
7. If tool update needed: `git clone --depth=1 --branch {branch}` into `.tmp/repo/`.
8. Atomic swap: move existing `tool/` → `.tmp/old/`; move new `tool/` into place. On failure: restore previous `tool/` from `.tmp/old/`.
9. Run `pip install -r tool/requirements.txt` (with `--break-system-packages` fallback for PEP 668 environments).
10. Apply pending config migrations to `conf/config.json` (in-place write).
11. Delete `.tmp/` directory.
12. Print summary.

### 4.3 Safety guarantees

- `conf/` is **never modified** by the tool swap (only `config.json` is updated by migrations, not replaced).
- `wsl4ai-update.py` is a **standalone script** — no imports from `commands/` — so it works even if `tool/` is corrupt or incompatible.
- Atomic swap with rollback: if the file replacement fails mid-way, the previous `tool/` is restored before exiting with error.
- `--force` flag bypasses version comparison and forces update regardless of local version.

---

## 5. Config migrations

Migrations are defined in `conf/wsl4ai-update.py` as a registry:

```python
_MIGRATIONS = [
    (from_version_or_None, to_version, description, migration_fn),
    ...
]
```

Each entry is applied only when the current config schema matches `from_version` (or has no `metadata` when `from_version` is `None`). Migrations are applied in order, incrementally.

### 5.1 Applied migrations

| From | To | Description |
|------|----|-------------|
| *(none / pre-1.0)* | `1.0` | Added `metadata` section with `schema_version` and `changelog` |

### 5.2 Adding a new migration

1. Increment `__config_version__` in `tool/wsl4ai.py` (e.g. `"1.0"` → `"1.1"`).
2. Write a migration function `_migrate_1_0_to_1_1(config: dict) -> dict` in `conf/wsl4ai-update.py`.
3. Append `("1.0", "1.1", "description", _migrate_1_0_to_1_1)` to `_MIGRATIONS`.
4. The migration runs automatically on the next `wsl4ai install update`.
