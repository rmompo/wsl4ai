"""`wsl4ai install database`: create or recreate SQLite DB and seed `parameters`."""

import sqlite3
from pathlib import Path
from argparse import Namespace
from commands.api_json import OptionSpec, emit_envelope, options_from_args

# Initial ``parameters`` rows when ``wsl4ai.db`` is first created (id + value).
PARAM_SEED_BASE_PATH_HOST = "/mnt/c/LocalFiles/proyectos/"
PARAM_SEED_BASE_PATH_WSL = "$HOME/proyectos/"


def _seed_initial_params(con: sqlite3.Connection) -> None:
    """Insert both required ``parameters`` rows: ``base_path_host`` and ``base_path_wsl`` (``id``, ``value``).

    WSL side seed uses ``$HOME`` for runtime expansion via :func:`commands.common.expand_path_template`.
    """
    for key, val in (
        ("base_path_host", PARAM_SEED_BASE_PATH_HOST),
        ("base_path_wsl", PARAM_SEED_BASE_PATH_WSL),
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
    _seed_initial_params(con)
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
