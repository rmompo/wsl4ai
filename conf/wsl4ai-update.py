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
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

REPO_RAW_BASE = "https://raw.githubusercontent.com/rmompo/wsl4ai/{branch}/tool"
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


def _parse_version(text: str) -> tuple[int, ...] | None:
    m = _VERSION_RE.search(text)
    if not m:
        return None
    try:
        return tuple(int(x) for x in m.group(1).split("."))
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

    # Step 2: download remote wsl4ai.py to check version
    raw_base = REPO_RAW_BASE.format(branch=args.branch)
    url = f"{raw_base}/wsl4ai.py"
    print("Checking remote version...")
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
    remote_str = _version_str(remote_v)
    remote_config_v = _parse_config_schema_version(remote_content)
    print(f"Remote version: {remote_str}")

    # Determine pending config migrations
    local_config = _read_config()
    pending_config_migrations: list[tuple[str | None, str, str]] = []
    if local_config is not None and remote_config_v:
        _, pending_config_migrations = _apply_config_migrations(local_config, remote_config_v)

    # Step 4: compare (skipped with --force)
    tool_needs_update = args.force or local_v is None or remote_v > local_v
    if not tool_needs_update and not pending_config_migrations:
        print("Already up to date.")
        _cleanup()
        return 0

    if args.check:
        if tool_needs_update:
            print(f"New version available: {remote_str}")
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

    # Cleanup
    _cleanup()

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
