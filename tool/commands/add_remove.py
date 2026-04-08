"""Add and remove registry rows only."""

from argparse import Namespace, _SubParsersAction

from commands.api_json import OptionSpec, options_from_args
from commands.common import load_local_env_paths
from commands.help_md import help_summary_for_root, parser_description_from_manual
from commands.interface import emit_from_interface, interface_registry_add, interface_registry_remove


def cmd_add(args: Namespace) -> int:
    opts = options_from_args(
        args,
        [
            OptionSpec("--name", "name"),
            OptionSpec("--host", "host"),
            OptionSpec("--wsl", "wsl"),
            OptionSpec("--force", "force", is_flag=True),
        ],
    )
    env = interface_registry_add(
        name=(args.name or "").strip(),
        host_rel=(args.host or "").strip(),
        wsl_rel=(args.wsl or "").strip(),
        force=bool(getattr(args, "force", False)),
    )
    return emit_from_interface(args, env, opts)


def cmd_remove(args: Namespace) -> int:
    opts = options_from_args(
        args,
        [
            OptionSpec("--uuid", "remove_uuid"),
            OptionSpec("--name", "remove_name"),
        ],
    )
    env = interface_registry_remove(
        registry_uuid=(getattr(args, "remove_uuid", None) or "").strip(),
        registry_name=(getattr(args, "remove_name", None) or "").strip(),
    )
    return emit_from_interface(args, env, opts)


def register_add_command(
    subparsers: _SubParsersAction,
    *,
    name: str = "add",
    aliases: tuple[str, ...] = (),
    help_override: str | None = None,
) -> None:
    fb = "Register a new mount definition (name plus host and WSL path segments)."
    desc = parser_description_from_manual("registry add", fb)
    if help_override:
        help_line = help_override
    else:
        help_line = help_summary_for_root("registry add", "Add a mount definition")
    add = subparsers.add_parser(
        name,
        aliases=list(aliases),
        help=help_line,
        description=desc,
    )
    base_host, base_wsl = load_local_env_paths()
    host_base_hint = base_host if base_host else "(HOST_PROJECTS not set)"
    wsl_base_hint = base_wsl if base_wsl else "(WSL_PROJECTS not set)"

    req = add.add_argument_group("Required")
    req.add_argument("-n", "--name", dest="name", required=True, help="Name for this mount definition")
    req.add_argument(
        "-H",
        "--host",
        dest="host",
        required=True,
        help=f"Host-side folder segment appended to HOST_PROJECTS ({host_base_hint})",
    )
    req.add_argument(
        "-w",
        "--wsl",
        dest="wsl",
        required=True,
        help=f"WSL-side folder segment appended to WSL_PROJECTS ({wsl_base_hint})",
    )
    add.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Proceed when folder paths are not ready yet",
    )
    # Show required flags before optional (--force, --help)
    if req in add._action_groups and add._optionals in add._action_groups:
        add._action_groups.remove(req)
        idx = add._action_groups.index(add._optionals)
        add._action_groups.insert(idx, req)
    add.set_defaults(func=cmd_add)


def register_remove_command(
    subparsers: _SubParsersAction,
    *,
    name: str = "remove",
    aliases: tuple[str, ...] = (),
    help_override: str | None = None,
) -> None:
    fb = "Delete a mount definition from the catalog."
    desc = parser_description_from_manual("registry remove", fb)
    if help_override:
        help_line = help_override
    else:
        help_line = help_summary_for_root("registry remove", "Remove a mount definition")
    rm = subparsers.add_parser(
        name,
        aliases=list(aliases),
        help=help_line,
        description=desc,
    )
    rm.add_argument(
        "-u",
        "--uuid",
        dest="remove_uuid",
        metavar="UUID",
        default="",
        help="Select the definition by UUID",
    )
    rm.add_argument(
        "-n",
        "--name",
        dest="remove_name",
        default="",
        help="Select the definition by name",
    )
    rm.set_defaults(func=cmd_remove)
