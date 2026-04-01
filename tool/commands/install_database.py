"""`wsl4ai install database`: create or recreate SQLite DB and seed `parameters`."""

import re
import sqlite3
from pathlib import Path
from argparse import Namespace

from commands.api_json import OptionSpec, emit_envelope, options_from_args

# Fallback when ``local.env`` is missing or keys are absent.
PARAM_SEED_BASE_PATH_HOST = "/mnt/c/LocalFiles/proyectos/"
PARAM_SEED_BASE_PATH_WSL = "$HOME/proyectos/"


def _parse_local_env(path: Path) -> dict[str, str]:
    """Parse ``KEY=value`` lines from ``local.env`` (``#`` comments, blanks skipped)."""
    if not path.is_file():
        return {}
    out: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        out[key.strip()] = val.strip()
    return out


def _ensure_trailing_slash(path: str) -> str:
    s = (path or "").strip()
    if not s:
        return s
    return s if s.endswith("/") else s + "/"


def _windows_path_to_mnt(path: str) -> str:
    """Map ``C:/dir/...`` to ``/mnt/c/dir/...``."""
    p = (path or "").strip().replace("\\", "/")
    m = re.match(r"^([A-Za-z]):/(.*)$", p)
    if not m:
        return p.rstrip("/")
    letter = m.group(1).lower()
    rest = (m.group(2) or "").strip("/")
    return f"/mnt/{letter}/{rest}" if rest else f"/mnt/{letter}"


def _resolve_seed_paths(app_dir: Path) -> tuple[str, str]:
    """Return ``(base_path_host, base_path_wsl)`` from ``local.env`` beside ``wsl4ai.py`` or built-in defaults."""
    env = _parse_local_env(app_dir / "local.env")
    host_raw = env.get("HOST_PROJECTS", "").strip()
    wsl_raw = env.get("WSL_PROJECTS", "").strip()

    if host_raw.startswith("/mnt/"):
        base_host = _ensure_trailing_slash(host_raw)
    elif host_raw and len(host_raw) >= 2 and host_raw[1] == ":":
        base_host = _ensure_trailing_slash(_windows_path_to_mnt(host_raw))
    elif host_raw:
        base_host = _ensure_trailing_slash(host_raw)
    else:
        base_host = PARAM_SEED_BASE_PATH_HOST

    if wsl_raw:
        base_wsl = _ensure_trailing_slash(wsl_raw)
    else:
        base_wsl = PARAM_SEED_BASE_PATH_WSL

    return base_host, base_wsl


def _seed_initial_params(con: sqlite3.Connection, app_dir: Path) -> None:
    """Insert ``parameters`` rows ``base_path_host`` and ``base_path_wsl``.

    When ``app_dir/local.env`` exists, ``HOST_PROJECTS`` and ``WSL_PROJECTS`` override defaults.
    """
    base_host, base_wsl = _resolve_seed_paths(app_dir)
    for key, val in (
        ("base_path_host", base_host),
        ("base_path_wsl", base_wsl),
    ):
        con.execute("INSERT INTO parameters (id, value) VALUES (?, ?)", (key, val))


def cmd_install_database(args: Namespace) -> int:
    """Create or recreate ``ddbb/wsl4ai.db`` with base schema and seed rows."""
    script_dir = Path(__file__).resolve().parent.parent
    ddbb_dir = script_dir / "ddbb"
    db_path = ddbb_dir / "wsl4ai.db"

    ddbb_dir.mkdir(parents=True, exist_ok=True)

    options = options_from_args(args, [OptionSpec("--force", "force", is_flag=True)])
    force = bool(getattr(args, "force", False))
    if db_path.is_file() and not force:
        return emit_envelope(
            args=args,
            command="install",
            subcommand="database",
            options=options,
            status=0,
            message=f"database already exists: {db_path}",
        )

    if db_path.is_file() and force:
        db_path.unlink()

    from .common import TABLE_DDL, connect_db

    con = connect_db(db_path)
    con.executescript(TABLE_DDL)
    _seed_initial_params(con, script_dir)
    con.commit()
    con.close()

    return emit_envelope(
        args=args,
        command="install",
        subcommand="database",
        options=options,
        status=0,
        message="database created" if not force else "database recreated",
        rows=[],
    )
