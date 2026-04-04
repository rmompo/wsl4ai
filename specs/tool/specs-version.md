# Specification: version (`-v` / `--version`)

## 1. Purpose

Report the installed version of WSL4AI without requiring a database or layout check.

## 2. Location

`__version__` string embedded in `tool/wsl4ai.py`:

```python
__version__ = "1.4.3"
```

## 3. CLI flag

```bash
wsl4ai -v
wsl4ai --version
```

Output format (argparse default):

```
wsl4ai 1.4.3
```

## 4. Rules

- Handled by argparse `action="version"` before any command dispatch.
- Does **not** require `conf/ddbb/` to exist (`_ensure_layout()` is never called).
- Version string follows **semantic versioning** (`MAJOR.MINOR.PATCH`).
- The version is the single source of truth used by `wsl4ai-update.py` to decide whether an update is needed.
