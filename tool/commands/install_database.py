"""`wsl4ai install database`: create or recreate SQLite DB."""

from pathlib import Path
from argparse import Namespace

from commands.api_json import OptionSpec, emit_envelope, options_from_args


def cmd_install_database(args: Namespace) -> int:
    """Create or recreate ``ddbb/wsl4ai.db`` with base schema and seed rows."""
    script_dir = Path(__file__).resolve().parent.parent
    ddbb_dir = script_dir.parent / "conf" / "ddbb"
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
