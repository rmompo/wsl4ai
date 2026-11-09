# Specification: version (`-v` / `--version`)

## 1. Purpose

Report the installed version of WSL4AI without requiring a database or layout check.

## 2. Location

`__version__` string embedded in `tool/wsl4ai.py`:

```python
__version__ = "1.9.2"
```

## 3. CLI flag

```bash
wsl4ai -v
wsl4ai --version
```

Output format (argparse default):

```
wsl4ai 1.9.2
```

## 4. Rules

- Handled by argparse `action="version"` before any command dispatch.
- Does **not** require `conf/ddbb/` to exist (`_ensure_layout()` is never called).
- Version string follows **semantic versioning** (`MAJOR.MINOR.PATCH`).
- The version is the single source of truth used by `wsl4ai-update.py` to decide whether an update is needed.

---

## 5. `wsl4ai version` / `wsl4ai ver`

> **Status: implemented** (CLI `version` / `ver`, TUI `Others › Version`). Uses the component manifest, see [`specs-manifest.md`](specs-manifest.md). Implementation: `api_version()` in [`commands/api.py`](../../tool/commands/api.py), [`commands/version_cmd.py`](../../tool/commands/version_cmd.py).

`-v` / `--version` keeps printing only the tool version. The `version` command reports the version of **every component**.

- Invocation: `wsl4ai version [--remote] [-b BRANCH]` · `wsl4ai ver [--remote] [-b BRANCH]`
- **CLI and TUI** (`Others › Version`). Read-only.
- Does **not** require `conf/ddbb/`: if the database is unavailable, `db_schema` is reported as `unavailable` and the command still succeeds.

### 5.1 Options

| Flag | Long | Required | Description |
|------|------|----------|-------------|
| — | `--remote` | no | Also download the remote `manifest.json` (CLI only) and compare |
| `-b` | `--branch` | no | Repository branch used with `--remote` (default: `main`) |

Without `--remote` the command is **offline**. If the remote cannot be reached or its manifest is invalid, the command fails (`status 1`) with the reason.

### 5.2 Rows

Always the five fixed components in this order — `tool`, `config_schema`, `db_schema`, `updater`, `installer` — then one `scripts/<file>` row per script found on disk, in the local manifest or in the remote one.

| Field | Meaning |
|-------|---------|
| `component` | Manifest key (`scripts/<file>` for scripts) |
| `local` | Installed version; `unknown` when it cannot be determined |
| `remote` | Version in the remote manifest (only with `--remote`) |
| `status` | `ok` · `outdated` (remote newer) · `unknown` |

With `--remote`, `status` compares `local` with `remote`. Offline, `ok` means the artifact matches the local manifest; `unknown` means there is no local manifest or it disagrees. Without `--remote` the `remote` field is absent.

The **local** value is read from the real artifact when possible: `__version__` and `__config_version__` of `wsl4ai.py`, the database, the constant of `wsl4ai-update.py`, the `# Version:` header of each script. The installer is not kept after installation, so its local value comes from `conf/manifest.json`. A mismatch between an artifact and the local manifest is shown as the artifact's value with `status = unknown`.

### 5.3 Output contract

Always `output.result` plus `output.data.rows` (records with the fields above). Exit code `0` unless the command itself fails; `outdated` or `unknown` rows are not errors.

