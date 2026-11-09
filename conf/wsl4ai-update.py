#!/usr/bin/env python3
"""WSL4AI standalone updater — no dependencies on commands/ modules.

Can be run directly if wsl4ai.py is corrupt or unavailable:
    python3 ~/wsl4ai/tool/wsl4ai-update.py
    python3 ~/wsl4ai/tool/wsl4ai-update.py --check
    python3 ~/wsl4ai/tool/wsl4ai-update.py --branch feature/TUI-Textual
    python3 ~/wsl4ai/tool/wsl4ai-update.py --check --branch feature/TUI-Textual
"""

import argparse
import json
import re
import shutil
import sqlite3
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

__version__ = "1.1.0"

REPO_RAW_BASE = "https://raw.githubusercontent.com/rmompo/wsl4ai/{branch}/tool"
REPO_RAW_ROOT = "https://raw.githubusercontent.com/rmompo/wsl4ai/{branch}"
REPO_CLONE_URL = "https://github.com/rmompo/wsl4ai.git"
DEFAULT_BRANCH = "main"
_VERSION_RE = re.compile(r'^__version__\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)
_CONFIG_VERSION_RE = re.compile(r'^__config_version__\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)

CONF_DIR = Path(__file__).resolve().parent   # ~/.../wsl4ai/conf/
BASE_DIR = CONF_DIR.parent                   # ~/.../wsl4ai/
APP_DIR = BASE_DIR / "tool"                  # ~/.../wsl4ai/tool/
TMP_DIR = BASE_DIR / ".tmp"
TMP_REMOTE_PY = TMP_DIR / "wsl4ai.py"
TMP_REPO_DIR = TMP_DIR / "repo"
TMP_OLD_DIR = TMP_DIR / "old"
CONFIG_PATH = CONF_DIR / "config.json"
MANIFEST_PATH = CONF_DIR / "manifest.json"   # local copy of the component manifest


def _parse_config_schema_version(text: str) -> str | None:
    """Extract __config_version__ string from Python source text."""
    m = _CONFIG_VERSION_RE.search(text)
    return m.group(1) if m else None


def _parse_config_version(v: str | None) -> tuple[int, ...]:
    """Parse a schema version string like '1.0' into a comparable tuple."""
    if v is None:
        return ()
    try:
        return tuple(int(x) for x in v.split("."))
    except (ValueError, AttributeError):
        return ()


def _get_schema_version(config: dict) -> str | None:
    """Return metadata.schema_version from a config dict, or None if absent."""
    try:
        return config.get("metadata", {}).get("schema_version") or None
    except Exception:
        return None


def _read_config() -> dict | None:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_config(config: dict) -> None:
    CONFIG_PATH.write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


# ─── Migration functions ──────────────────────────────────────────────────────

def _migrate_none_to_1_0(config: dict) -> dict:
    """Pre-versioning → 1.0: add metadata section."""
    now = datetime.now().isoformat(timespec="seconds")
    meta = {
        "schema_version": "1.0",
        "changelog": [
            {
                "schema_version": "1.0",
                "datetime": now,
                "comment": "added metadata section; config without metadata treated as pre-1.0",
            }
        ],
    }
    return {"metadata": meta, **{k: v for k, v in config.items() if k != "metadata"}}


# Registry: (from_version_or_None, to_version, description, migration_fn)
# Add future migrations here in order.
_MIGRATIONS: list[tuple[str | None, str, str, object]] = [
    (None, "1.0", "added metadata section with schema_version and changelog", _migrate_none_to_1_0),
]


def _apply_config_migrations(
    config: dict,
    target_version: str,
) -> tuple[dict, list[tuple[str | None, str, str]]]:
    """Apply all pending migrations up to target_version.

    Returns (updated_config, applied_migrations).
    applied_migrations is a list of (from_ver, to_ver, description) tuples.
    Does not write to disk — caller decides whether to save.
    """
    applied: list[tuple[str | None, str, str]] = []
    target_v = _parse_config_version(target_version)

    for from_v_str, to_v_str, description, fn in _MIGRATIONS:  # type: ignore[assignment]
        current = _get_schema_version(config)
        current_v = _parse_config_version(current)
        to_v = _parse_config_version(to_v_str)

        if current_v >= to_v:
            continue  # already at or past this migration
        if to_v > target_v:
            continue  # beyond the target version
        if from_v_str is None:
            if current is not None:
                continue  # only applies when there is no metadata at all
        else:
            if current != from_v_str:
                continue  # must match exactly

        config = fn(config)  # type: ignore[operator]
        applied.append((from_v_str, to_v_str, description))

    return config, applied


# ─── Component manifest (see specs/tool/specs-manifest.md) ───────────────────

def _flatten_manifest(manifest: dict | None) -> dict[str, str]:
    """Flatten ``components`` to ``{name: version}``; scripts become ``scripts/<file>``."""
    flat: dict[str, str] = {}
    comps = (manifest or {}).get("components", {})
    if not isinstance(comps, dict):
        return flat
    for name, value in comps.items():
        if isinstance(value, dict):
            for fname, ver in value.items():
                flat[f"{name}/{fname}"] = str(ver)
        else:
            flat[name] = str(value)
    return flat


def _parse_manifest_text(text: str) -> dict | None:
    try:
        data = json.loads(text)
    except ValueError:
        return None
    return data if isinstance(data, dict) and isinstance(data.get("components"), dict) else None


def _read_local_manifest() -> dict | None:
    """The manifest saved by the installer or the last update (None when missing or invalid)."""
    try:
        return _parse_manifest_text(MANIFEST_PATH.read_text(encoding="utf-8"))
    except OSError:
        return None


def _fetch_remote_manifest(branch: str) -> tuple[dict | None, str]:
    """Download ``manifest.json`` from the repository root. Returns ``(manifest, raw_text)``."""
    url = f"{REPO_RAW_ROOT.format(branch=branch)}/manifest.json"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            text = resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return None, ""
    return _parse_manifest_text(text), text


def _component_changes(
    local_manifest: dict | None,
    remote_manifest: dict,
    tool_local: str,
    schema_local: str | None,
    db_local: int | None,
) -> list[tuple[str, str, str]]:
    """Components whose remote version differs from the local one: ``(name, local, remote)``.

    The local values come from the manifest saved at the last install/update, overridden
    by what this updater can read directly (tool, updater, config schema, database).
    """
    local = _flatten_manifest(local_manifest)
    local["tool"] = tool_local
    local["updater"] = __version__
    if schema_local:
        local["config_schema"] = schema_local
    if db_local is not None:
        local["db_schema"] = str(db_local)
    changes = []
    for name, remote in _flatten_manifest(remote_manifest).items():
        have = local.get(name, "unknown")
        if have != remote:
            changes.append((name, have, remote))
    return changes


def _print_component_changes(changes: list[tuple[str, str, str]], branch: str) -> None:
    """List changed components and warn about the two that are never replaced automatically."""
    if not changes:
        return
    print("Components    :")
    for name, have, remote in changes:
        print(f"  {name}: {have} -> {remote}")
    notes = {
        "updater": ("conf/wsl4ai-update.py", f"{REPO_RAW_ROOT.format(branch=branch)}/conf/wsl4ai-update.py"),
        "installer": ("install/wsl4ai-install.sh", f"{REPO_RAW_ROOT.format(branch=branch)}/install/wsl4ai-install.sh"),
    }
    for name, have, remote in changes:
        newer = (_to_tuple(remote) or ()) > (_to_tuple(have) or ())
        if name in notes and have != "unknown" and newer:
            path, url = notes[name]
            print(f"NOTE: a newer {name} exists ({have} -> {remote}); it is never replaced automatically.")
            print(f"      {path}: {url}")


# ─── Database schema migrations (PRAGMA user_version) ────────────────────────

def _ddbb_path() -> Path:
    """``wsl4ai.db`` location: ``WSL_DDBB`` from ``conf/local.env``, else ``conf/ddbb``."""
    try:
        for raw in (CONF_DIR / "local.env").read_text(encoding="utf-8").splitlines():
            key, _, val = raw.strip().partition("=")
            if key.strip() == "WSL_DDBB" and val.strip():
                return Path(val.strip().rstrip("/")) / "wsl4ai.db"
    except OSError:
        pass
    return CONF_DIR / "ddbb" / "wsl4ai.db"


def _db_user_version(path: Path) -> int | None:
    """Schema version of the database (None when there is no usable database)."""
    if not path.is_file():
        return None
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5.0)
        try:
            return int(con.execute("PRAGMA user_version").fetchone()[0])
        finally:
            con.close()
    except sqlite3.Error:
        return None


def _migrate_db_0_to_1(con: sqlite3.Connection) -> None:
    """Unversioned database -> 1: no structural change, the version is only stamped."""


# Registry: (from_version, to_version, description, migration_fn). Add future migrations here in order.
_DB_MIGRATIONS: list[tuple[int, int, str, object]] = [
    (0, 1, "stamp schema version (no structural change)", _migrate_db_0_to_1),
]


def _pending_db_migrations(current: int | None, target: int | None) -> list[tuple[int, int, str, object]]:
    if current is None or target is None or current >= target:
        return []
    pending, version = [], current
    for frm, to, desc, fn in _DB_MIGRATIONS:
        if frm == version and to <= target:
            pending.append((frm, to, desc, fn))
            version = to
    return pending


def _apply_db_migrations(path: Path, migrations: list) -> tuple[list[tuple[int, int, str]], str | None]:
    """Run the migrations in order, stamping ``user_version`` after each. Returns (applied, error)."""
    applied: list[tuple[int, int, str]] = []
    try:
        con = sqlite3.connect(str(path), timeout=5.0)
        try:
            for frm, to, desc, fn in migrations:
                fn(con)  # type: ignore[operator]
                con.execute(f"PRAGMA user_version = {int(to)}")
                con.commit()
                applied.append((frm, to, desc))
        finally:
            con.close()
    except sqlite3.Error as exc:
        return applied, str(exc)
    return applied, None


def _parse_version(text: str) -> tuple[int, ...] | None:
    m = _VERSION_RE.search(text)
    if not m:
        return None
    try:
        return tuple(int(x) for x in m.group(1).split("."))
    except ValueError:
        return None


def _to_tuple(text: str) -> tuple[int, ...] | None:
    """Parse ``'1.2.3'`` (or ``'1'``) into a comparable tuple; None when invalid."""
    try:
        return tuple(int(x) for x in text.strip().split(".")) or None
    except ValueError:
        return None


def _version_str(v: tuple[int, ...]) -> str:
    return ".".join(str(x) for x in v)


def _local_version() -> tuple[tuple[int, ...] | None, str]:
    try:
        content = (APP_DIR / "wsl4ai.py").read_text(encoding="utf-8")
    except OSError:
        return None, "unreadable"
    v = _parse_version(content)
    return (v, _version_str(v)) if v else (None, "unknown")


def _cleanup() -> None:
    shutil.rmtree(TMP_DIR, ignore_errors=True)


def _print_summary(
    branch: str,
    version_from: str,
    version_to: str,
    download: str,
    pip: str,
    config_migrations: list[tuple[str | None, str, str]] | None = None,
) -> None:
    """Print a plain text update summary."""
    print()
    print("WSL4AI Update Summary")
    print(f"  Branch      : {branch}")
    print(f"  Tool        : {version_from} -> {version_to}")
    print(f"  Download    : {download}")
    print(f"  pip install : {pip}")
    if config_migrations:
        for i, (frm, to, desc) in enumerate(config_migrations):
            frm_str = frm if frm is not None else "pre-1.0"
            label = "  Config      :" if i == 0 else "               "
            print(f"{label} {frm_str} -> {to}  {desc}")


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="wsl4ai-update",
        description="WSL4AI standalone updater",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check for a new version without applying the update",
    )
    parser.add_argument(
        "-b", "--branch",
        default=DEFAULT_BRANCH,
        metavar="BRANCH",
        help=f"Repository branch to check and download from (default: {DEFAULT_BRANCH})",
    )
    parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Force update without checking the remote version",
    )
    args = parser.parse_args()

    local_v, local_str = _local_version()
    print(f"Local version : {local_str}")
    print(f"Branch        : {args.branch}")

    # Prepare .tmp/
    _cleanup()
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    # Step 2: read the remote versions: manifest.json first; wsl4ai.py as a fallback
    # for branches that have no manifest yet.
    print("Checking remote version...")
    remote_manifest, remote_manifest_text = _fetch_remote_manifest(args.branch)
    if remote_manifest is not None:
        comps = remote_manifest["components"]
        remote_v = _to_tuple(str(comps.get("tool", "")))
        remote_config_v = str(comps.get("config_schema") or "") or None
        remote_db = _to_tuple(str(comps.get("db_schema", "")))
        remote_db_v = remote_db[0] if remote_db else None
        if remote_v is None:
            print("ERROR: remote manifest.json has no valid 'tool' version", file=sys.stderr)
            _cleanup()
            return 1
    else:
        url = f"{REPO_RAW_BASE.format(branch=args.branch)}/wsl4ai.py"
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                remote_content = resp.read().decode("utf-8", errors="ignore")
            TMP_REMOTE_PY.write_text(remote_content, encoding="utf-8")
        except Exception as exc:
            print(f"ERROR: could not reach remote: {exc}", file=sys.stderr)
            _cleanup()
            return 1
        # Step 3: extract remote tool and config versions
        remote_v = _parse_version(remote_content)
        if remote_v is None:
            print("ERROR: could not parse __version__ from remote wsl4ai.py", file=sys.stderr)
            _cleanup()
            return 1
        remote_config_v = _parse_config_schema_version(remote_content)
        remote_db_v = None
    remote_str = _version_str(remote_v)
    print(f"Remote version: {remote_str}")

    # Determine pending config migrations
    local_config = _read_config()
    pending_config_migrations: list[tuple[str | None, str, str]] = []
    if local_config is not None and remote_config_v:
        _, pending_config_migrations = _apply_config_migrations(local_config, remote_config_v)

    # Pending database migrations and changed components (only when the remote has a manifest)
    db_path = _ddbb_path()
    db_local = _db_user_version(db_path)
    pending_db_migrations = _pending_db_migrations(db_local, remote_db_v)
    if db_local is not None and remote_db_v is not None and db_local > remote_db_v:
        print(f"WARNING: the database schema ({db_local}) is newer than this release supports ({remote_db_v}).")
    changes: list[tuple[str, str, str]] = []
    if remote_manifest is not None:
        changes = _component_changes(
            _read_local_manifest(),
            remote_manifest,
            local_str,
            _get_schema_version(local_config) if local_config is not None else None,
            db_local,
        )

    # Step 4: compare (skipped with --force)
    tool_needs_update = args.force or local_v is None or remote_v > local_v
    if not tool_needs_update and not pending_config_migrations and not pending_db_migrations:
        print("Already up to date.")
        _print_component_changes([c for c in changes if c[0] in ("updater", "installer")], args.branch)
        _cleanup()
        return 0

    if args.check:
        if tool_needs_update:
            print(f"New version available: {remote_str}")
        for i, (frm, to, desc, _fn) in enumerate(pending_db_migrations):
            label = "  Database:" if i == 0 else "           "
            print(f"{label} {frm} -> {to}  {desc}")
        _print_component_changes(changes, args.branch)
        if pending_config_migrations:
            for i, (frm, to, desc) in enumerate(pending_config_migrations):
                frm_str = frm if frm is not None else "pre-1.0"
                label = "  Config:" if i == 0 else "          "
                print(f"{label} {frm_str} -> {to}  {desc}")
        _cleanup()
        return 0

    if tool_needs_update:
        print(f"Updating {local_str} -> {remote_str}...")

    download_status = "skipped"
    pip_status = "skipped"

    if tool_needs_update:
        # Step 5a: git clone
        print("Cloning repository...")
        result = subprocess.run(
            ["git", "clone", "--depth=1", "--branch", args.branch, REPO_CLONE_URL, str(TMP_REPO_DIR)],
            capture_output=True,
        )
        if result.returncode != 0:
            print(f"ERROR: git clone failed: {result.stderr.decode().strip()}", file=sys.stderr)
            _cleanup()
            return 1

        new_tool = TMP_REPO_DIR / "tool"
        if not new_tool.is_dir():
            print("ERROR: tool/ not found in cloned repository", file=sys.stderr)
            _cleanup()
            return 1

        try:
            # conf/ is never touched during update (local.env, config.json, wsl4ai-update.py, ddbb/ are safe)
            shutil.move(str(APP_DIR), str(TMP_OLD_DIR))
            shutil.move(str(new_tool), str(APP_DIR))
        except Exception as exc:
            if TMP_OLD_DIR.is_dir() and not APP_DIR.is_dir():
                print("Restoring previous version...", file=sys.stderr)
                shutil.move(str(TMP_OLD_DIR), str(APP_DIR))
            print(f"ERROR: failed during file replacement: {exc}", file=sys.stderr)
            _cleanup()
            return 1

        download_status = "OK"
        if remote_manifest_text:
            try:
                MANIFEST_PATH.write_text(remote_manifest_text, encoding="utf-8")
            except OSError as exc:
                print(f"WARNING: could not save manifest.json: {exc}", file=sys.stderr)

        # Step 5c: install/update dependencies
        pip_status = "skipped (no requirements.txt)"
        req_file = APP_DIR / "requirements.txt"
        if req_file.is_file():
            print("Installing dependencies...")
            pip_cmd = [sys.executable, "-m", "pip", "install", "-r", str(req_file)]
            pip_result = subprocess.run(pip_cmd, capture_output=True)
            if pip_result.returncode != 0:
                # Retry with --break-system-packages for PEP 668 managed environments
                pip_result = subprocess.run(
                    pip_cmd + ["--break-system-packages"], capture_output=True
                )
            pip_status = "OK" if pip_result.returncode == 0 else "ERROR"

    # Step 6: apply config migrations
    applied_config_migrations: list[tuple[str | None, str, str]] = []
    if local_config is not None and remote_config_v and pending_config_migrations:
        updated_config, applied_config_migrations = _apply_config_migrations(local_config, remote_config_v)
        _write_config(updated_config)

    # Step 6b: apply database migrations
    applied_db_migrations: list[tuple[int, int, str]] = []
    if pending_db_migrations:
        applied_db_migrations, db_error = _apply_db_migrations(db_path, pending_db_migrations)
        if db_error:
            print(f"ERROR: database migration failed: {db_error}", file=sys.stderr)

    # Cleanup
    _cleanup()

    _print_component_changes(
        [c for c in changes if c[0] in ("updater", "installer")], args.branch
    )
    for i, (frm, to, desc) in enumerate(applied_db_migrations):
        label = "Database    :" if i == 0 else "             "
        print(f"{label} {frm} -> {to}  {desc}")

    _print_summary(
        branch=args.branch,
        version_from=local_str,
        version_to=remote_str,
        download=download_status,
        pip=pip_status,
        config_migrations=applied_config_migrations or None,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
