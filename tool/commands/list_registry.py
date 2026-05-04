"""List all registry rows."""

from argparse import Namespace, _SubParsersAction

from commands.help_md import help_summary_for_root, parser_description_from_manual
from commands.api import emit_from_api, api_registry_list


def cmd_list(args: Namespace) -> int:
    """Return all `registries` rows with resolved paths and linked `uses`."""
    return emit_from_api(args, api_registry_list(), [])


def register_list_command(
    subparsers: _SubParsersAction,
    *,
    name: str = "list",
    aliases: tuple[str, ...] = (),
    help_override: str | None = None,
) -> None:
    """Register ``list`` subparser (e.g. under ``registry`` or as root shortcut ``rl``)."""
    fb = "Show every mount definition and which WSL workspaces reference it."
    desc = parser_description_from_manual("registry list", fb)
    if help_override:
        help_line = help_override
    else:
        help_line = help_summary_for_root("registry list", "List mount definitions")
    lst = subparsers.add_parser(
        name,
        aliases=list(aliases),
        help=help_line,
        description=desc,
    )
    lst.set_defaults(func=cmd_list)
