"""Installation command router (`tool`, `database`, `alias`)."""

from argparse import Namespace, _SubParsersAction

from commands.install_alias import cmd_install_alias
from commands.install_database import cmd_install_database
from commands.install_tool import cmd_install_tool
from commands.install_update import cmd_install_update


def register_install_command(subparsers: _SubParsersAction) -> None:
    """Register `install` router and root shortcuts (`it`, `id`, `ia`)."""
    h = "Install tool/database resources and shell aliases"
    install = subparsers.add_parser("install", help=h, description=h)
    install_sub = install.add_subparsers(dest="install_command", required=True, metavar="SUBCOMMAND")

    p_tool = install_sub.add_parser("tool", help="Install or verify tool layout")
    p_tool.set_defaults(func=cmd_install_tool)

    p_db = install_sub.add_parser("database", help="Create database or recreate with --force")
    p_db.add_argument("-f", "--force", action="store_true", help="Overwrite existing database")
    p_db.set_defaults(func=cmd_install_database)

    p_alias = install_sub.add_parser("alias", help="Add/remove/list aliases for PowerShell or Bash")
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
        required=False,
        action="append",
        help="Alias name (repeatable; required for add/remove)",
    )
    p_alias.set_defaults(func=cmd_install_alias)

    p_update = install_sub.add_parser("update", help="Check and apply updates from GitHub")
    p_update.add_argument("--check", dest="check_only", action="store_true", help="Check for updates without applying")
    p_update.set_defaults(func=cmd_install_update)

    p_it = subparsers.add_parser("it", help="Shorthand for install tool")
    p_it.set_defaults(func=cmd_install_tool)

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
        required=False,
        action="append",
        help="Alias name (repeatable; required for add/remove)",
    )
    p_ia.set_defaults(func=cmd_install_alias)

    p_iu = subparsers.add_parser("iu", help="Shorthand for install update")
    p_iu.add_argument("--check", dest="check_only", action="store_true", help="Check for updates without applying")
    p_iu.set_defaults(func=cmd_install_update)
