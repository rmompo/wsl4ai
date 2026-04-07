#!/usr/bin/env python3
"""WSL4AI standalone updater — no dependencies on commands/ modules.

Can be run directly if wsl4ai.py is corrupt or unavailable:
    python3 ~/wsl4ai/tool/wsl4ai-update.py
    python3 ~/wsl4ai/tool/wsl4ai-update.py --check
    python3 ~/wsl4ai/tool/wsl4ai-update.py --branch feature/TUI-Textual
    python3 ~/wsl4ai/tool/wsl4ai-update.py --check --branch feature/TUI-Textual
"""

import argparse
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO_RAW_BASE = "https://raw.githubusercontent.com/rmompo/wsl4ai/{branch}/tool"
REPO_CLONE_URL = "https://github.com/rmompo/wsl4ai.git"
DEFAULT_BRANCH = "main"
_VERSION_RE = re.compile(r'^__version__\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)

CONF_DIR = Path(__file__).resolve().parent   # ~/.../wsl4ai/conf/
BASE_DIR = CONF_DIR.parent                   # ~/.../wsl4ai/
APP_DIR = BASE_DIR / "tool"                  # ~/.../wsl4ai/tool/
TMP_DIR = BASE_DIR / ".tmp"
TMP_REMOTE_PY = TMP_DIR / "wsl4ai.py"
TMP_REPO_DIR = TMP_DIR / "repo"
TMP_OLD_DIR = TMP_DIR / "old"


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
) -> None:
    """Print a plain text update summary."""
    print()
    print("WSL4AI Update Summary")
    print(f"  Branch      : {branch}")
    print(f"  Version     : {version_from} -> {version_to}")
    print(f"  Download    : {download}")
    print(f"  pip install : {pip}")


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

    # Step 3: extract remote version
    remote_v = _parse_version(remote_content)
    if remote_v is None:
        print("ERROR: could not parse __version__ from remote wsl4ai.py", file=sys.stderr)
        _cleanup()
        return 1
    remote_str = _version_str(remote_v)
    print(f"Remote version: {remote_str}")

    # Step 4: compare
    if local_v is not None and remote_v <= local_v:
        print("Already up to date.")
        _cleanup()
        return 0

    if args.check:
        print(f"New version available: {remote_str}")
        _cleanup()
        return 0

    print(f"Updating {local_str} -> {remote_str}...")

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

    # Step 5g: cleanup
    _cleanup()

    _print_summary(
        branch=args.branch,
        version_from=local_str,
        version_to=remote_str,
        download="OK",
        pip=pip_status,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
