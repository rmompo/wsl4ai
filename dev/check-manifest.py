#!/usr/bin/env python3
"""Check that manifest.json agrees with the code it describes (specs/tool/specs-manifest.md §5).

Run from anywhere:  python3 dev/check-manifest.py
Exit code 0 when everything matches, 1 otherwise. Development tool: it is not installed.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _find(path: Path, pattern: str) -> str:
    """First capture group of *pattern* in the file, or '' when absent."""
    m = re.search(pattern, path.read_text(encoding="utf-8"), re.MULTILINE)
    return m.group(1) if m else ""


def main() -> int:
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    comp = manifest["components"]
    py_var = r'^{}\s*=\s*["\']([^"\']+)["\']'
    header = r"^# Version:\s*(\S+)"
    checks = [
        ("tool", _find(ROOT / "tool/wsl4ai.py", py_var.format("__version__"))),
        ("config_schema", _find(ROOT / "tool/wsl4ai.py", py_var.format("__config_version__"))),
        ("db_schema", _find(ROOT / "tool/commands/common.py", r"^DB_SCHEMA_VERSION\s*=\s*(\d+)")),
        ("updater", _find(ROOT / "conf/wsl4ai-update.py", py_var.format("__version__"))),
        ("installer", _find(ROOT / "install/wsl4ai-install.sh", header)),
    ]
    errors = []
    for name, actual in checks:
        if comp.get(name) != actual:
            errors.append(f"{name}: manifest={comp.get(name)!r} code={actual!r}")

    scripts = comp.get("scripts", {})
    on_disk = sorted(p.name for p in (ROOT / "tool/scripts").glob("*.sh"))
    for name in on_disk:
        actual = _find(ROOT / "tool/scripts" / name, header)
        if name not in scripts:
            errors.append(f"scripts/{name}: missing in manifest (header {actual!r})")
        elif scripts[name] != actual:
            errors.append(f"scripts/{name}: manifest={scripts[name]!r} header={actual!r}")
    for name in sorted(set(scripts) - set(on_disk)):
        errors.append(f"scripts/{name}: in manifest but not on disk")

    if errors:
        print("manifest.json is out of sync:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("manifest.json is in sync.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
