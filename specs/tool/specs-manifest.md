# WSL4AI — Component Manifest Specification

> **Status: implemented.** `manifest.json`, the version of every component, the installer writing `conf/manifest.json`, the consistency check (`dev/check-manifest.py`), the updater comparing manifests and running database migrations (§4), and the `wsl4ai version` command.

This document specifies `manifest.json`: a single file that records the version of every independently versioned component of WSL4AI, and how the updater uses it.

---

## 1. Motivation

Today only two things carry a version: the tool (`__version__` in `tool/wsl4ai.py`) and the `config.json` schema (`__config_version__`). The updater reads the tool version with a regular expression over `wsl4ai.py`. Everything else is unversioned:

- `conf/wsl4ai-update.py` is never replaced by an update, so a fix in it never reaches existing installs, and there is no way to tell which version an install has.
- The SQLite database has no schema version, so it cannot be migrated.
- The installer has only a comment (`install v3.0`) that nothing reads.
- The install scripts in `tool/scripts/` have no version.

---

## 2. File

`manifest.json` at the **repository root**:

```json
{
  "manifest_version": 1,
  "components": {
    "tool": "1.6.9",
    "config_schema": "1.0",
    "db_schema": "1",
    "updater": "1.0.0",
    "installer": "3.0.0",
    "scripts": {
      "wsl4ai-install-claudecode.sh": "0.1.0",
      "wsl4ai-install-ghcopilot.sh": "0.1.0"
    }
  }
}
```

| Component | What it versions | Source of the value |
|-----------|------------------|---------------------|
| `tool` | The Python application (`tool/`) | `__version__` in `tool/wsl4ai.py` |
| `config_schema` | Structure of `conf/config.json` | `__config_version__` in `tool/wsl4ai.py` |
| `db_schema` | Structure of the SQLite database | `DB_SCHEMA_VERSION` in `tool/commands/common.py`, stored in the database as `PRAGMA user_version` (an **integer**; `0` = unversioned database created before this field) |
| `updater` | `conf/wsl4ai-update.py` | `__version__` constant in the script |
| `installer` | `install/wsl4ai-install.sh` | `# Version:` header in the script |
| `scripts` | Each file in `tool/scripts/`, by file name | `# Version:` header in each script |

Versions follow **semantic versioning** (`MAJOR.MINOR.PATCH`). `config_schema` keeps the `MAJOR.MINOR` form it already has, and `db_schema` is a plain integer.

`manifest_version` is the version of the manifest format itself (an integer).

---

## 3. Installed copy

The updater keeps a **local copy** at `conf/manifest.json` (never replaced by tool updates). It records what this install has:

- The installer writes the initial copy at install time.
- The updater rewrites it **only after a successful update**.
- If it is missing (installs made before this feature), every component is treated as **unknown** and the next update creates it. A missing file must never make the updater fail.

---

## 4. Updater behaviour

`wsl4ai install update [--check]` downloads the remote `manifest.json` (same branch rules as today, see `--branch`) instead of parsing `wsl4ai.py`, and compares each component with the local copy.

| Component | On difference |
|-----------|---------------|
| `tool`, `scripts` | Applied by the update: both travel inside `tool/`, which is replaced atomically. `--check` lists which ones changed. |
| `config_schema` | Migrations are applied as already specified in [`specs-config.md`](specs-config.md). |
| `db_schema` | A migration chain, analogous to the config one, applies pending database migrations. |
| `updater`, `installer` | **Advisory only.** The updater is never replaced automatically; `--check` and the update print a warning that a newer version exists and where to get it. |

`--check` output lists every component whose remote version differs, one per line (`component: local → remote`).

The updater falls back to the old `wsl4ai.py` parsing when the remote branch has no `manifest.json`, so branches created before the manifest keep updating. The full report is the `wsl4ai version` command (CLI and TUI), specified in [`specs-version.md`](specs-version.md) §5; `wsl4ai info` ([`specs-info.md`](specs-info.md)) reports the setup of the distro.

---

## 5. Consistency rules

The manifest must never disagree with the code it describes. These must hold in every commit:

1. `components.tool` equals `__version__` in `tool/wsl4ai.py`.
2. `components.config_schema` equals `__config_version__` in `tool/wsl4ai.py`.
3. `components.db_schema` equals `DB_SCHEMA_VERSION` in `tool/commands/common.py`.
4. `components.updater` equals the version constant in `conf/wsl4ai-update.py`.
5. `components.installer` equals the `# Version:` header of the installer.
6. Each entry of `components.scripts` equals the `# Version:` header of that script, and every `*.sh` in `tool/scripts/` has an entry.

The **consistency check** `python3 dev/check-manifest.py` enforces these rules (exit code `1` and a list of differences when they do not hold). It is a development tool and is not installed; running it from a pre-commit hook is left to the developer. When a component changes, its version is bumped in both places in the same commit.

---

## 6. Out of scope

- `specs/` carries no version: it follows the repository.
- Per-script update on its own: scripts are replaced together with `tool/`.

---

## 7. Open questions

- The first database migration. Databases created before `db_schema` existed report `user_version = 0` and must be stamped with `1` by the updater (no structural change).
- Whether the updater should be allowed to replace itself on request (e.g. `--self`), instead of warning only.
