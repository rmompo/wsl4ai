"""Router for ``wsl4ai registry`` — subcommands ``list``, ``add``, ``remove`` (+ aliases)."""

from argparse import _SubParsersAction

from commands.add_remove import register_add_command, register_remove_command
from commands.list_registry import register_list_command


def register_registry_command(subparsers: _SubParsersAction) -> None:
    """Register ``registry`` with nested ``list`` / ``add`` / ``remove`` and shorthand aliases."""
    h = "Define and list mount paths that WSL workspaces can attach to."
    reg = subparsers.add_parser(
        "registry",
        help=h,
        description=h,
    )
    reg_sub = reg.add_subparsers(
        dest="registry_command",
        required=True,
        metavar="SUBCOMMAND",
        help="list|rl | add|ra | remove|rr",
    )
    register_list_command(reg_sub, aliases=("rl",))
    register_add_command(reg_sub, aliases=("ra",))
    register_remove_command(reg_sub, aliases=("rr",))


def register_registry_root_shortcuts(subparsers: _SubParsersAction) -> None:
    """Top-level ``rl`` / ``ra`` / ``rr`` — same as ``registry list|add|remove``."""
    register_list_command(
        subparsers,
        name="rl",
        help_override="Shorthand for registry list",
    )
    register_add_command(
        subparsers,
        name="ra",
        help_override="Shorthand for registry add",
    )
    register_remove_command(
        subparsers,
        name="rr",
        help_override="Shorthand for registry remove",
    )
