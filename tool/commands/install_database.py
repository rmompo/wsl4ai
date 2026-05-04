"""`wsl4ai install database`: create or recreate SQLite DB."""

from argparse import Namespace

from commands.api_json import OptionSpec, options_from_args
from commands.api import emit_from_api, api_install_database


def cmd_install_database(args: Namespace) -> int:
    """Create or recreate ``ddbb/wsl4ai.db`` with base schema and seed rows."""
    opts = options_from_args(args, [OptionSpec("--force", "force", is_flag=True)])
    force = bool(getattr(args, "force", False))
    return emit_from_api(args, api_install_database(force=force), opts)
