"""Installation command router (`database`, `alias`)."""

from argparse import Namespace, _SubParsersAction

from commands.install_alias import cmd_install_alias
from commands.install_database import cmd_install_database
from commands.install_update import cmd_install_update


def register_install_command(subparsers: _SubParsersAction) -> None:
    """Register `install` router and root shortcuts (`id`, `ia`)."""
    h = "Create the database, manage shell aliases and update WSL4AI"
    install = subparsers.add_parser("install", help=h, description=h)
    install_sub = install.add_subparsers(dest="install_command", required=True, metavar="SUBCOMMAND")

    p_db = install_sub.add_parser(
        "database",
        help="Create database or recreate with --force",
        description="Create the SQLite database if it is missing; with --force, delete and recreate it (destructive).",
    )
    p_db.add_argument("-f", "--force", action="store_true", help="Overwrite existing database")
    p_db.set_defaults(func=cmd_install_database)

    p_alias = install_sub.add_parser(
        "alias",
        help="Add/remove/list aliases for PowerShell or Bash",
        description="Add, remove or list the wsl4ai shell aliases in the Bash (or PowerShell) profile.",
    )
    p_alias.add_argument(
        "-a",
        "--action",
        dest="alias_action",
        required=True,
        choices=["add", "remove", "list"],
        help="Alias action",
    )
    p_alias.add_argument(
        "-n",
        "--name",
        dest="alias_names",
        metavar="ALIAS",
        required=False,
        action="append",
        help="Alias name (repeatable; required for add/remove)",
    )
    p_alias.set_defaults(func=cmd_install_alias)

    p_update = install_sub.add_parser(
        "update",
        help="Check and apply updates from GitHub",
        description="Check GitHub for a newer WSL4AI and apply it: replaces tool/, applies config and database migrations and lists the components that changed.",
    )
    p_update.add_argument("--check", dest="check_only", action="store_true", help="Check for updates without applying")
    p_update.add_argument("-f", "--force", action="store_true", help="Force update even if already up to date (runs pip install)")
    p_update.add_argument("-b", "--branch", metavar="BRANCH", help="Repository branch to check and download from (default: main)")
    p_update.set_defaults(func=cmd_install_update)

    p_id = subparsers.add_parser("id", help="Shorthand for install database")
    p_id.add_argument("-f", "--force", action="store_true", help="Overwrite existing database")
    p_id.set_defaults(func=cmd_install_database)

    p_ia = subparsers.add_parser("ia", help="Shorthand for install alias")
    p_ia.add_argument(
        "-a",
        "--action",
        dest="alias_action",
        required=True,
        choices=["add", "remove", "list"],
        help="Alias action",
    )
    p_ia.add_argument(
        "-n",
        "--name",
        dest="alias_names",
        metavar="ALIAS",
        required=False,
        action="append",
        help="Alias name (repeatable; required for add/remove)",
    )
    p_ia.set_defaults(func=cmd_install_alias)

    p_iu = subparsers.add_parser("iu", help="Shorthand for install update")
    p_iu.add_argument("--check", dest="check_only", action="store_true", help="Check for updates without applying")
    p_iu.add_argument("-f", "--force", action="store_true", help="Force update even if already up to date (runs pip install)")
    p_iu.add_argument("-b", "--branch", metavar="BRANCH", help="Repository branch to check and download from (default: main)")
    p_iu.set_defaults(func=cmd_install_update)
