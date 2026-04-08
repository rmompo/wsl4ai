"""``wsl4ai use`` subcommands and top-level shortcuts (``ua``, ``ur``, …)."""

from argparse import Namespace, _SubParsersAction
from collections.abc import Callable

from commands.api_json import OptionSpec, options_from_args
from commands.help_md import help_summary_for_root, parser_description_from_manual
from commands.interface import (
    emit_from_interface,
    interface_use_add,
    interface_use_disable,
    interface_use_disableall,
    interface_use_enable,
    interface_use_list,
    interface_use_remove,
)


def _ri(args: Namespace):
    return args.runtime_identity


def cmd_use_list(args: Namespace) -> int:
    """List all usage links between wsls and registries."""
    opts = options_from_args(
        args,
        [
            OptionSpec("--all", "use_all", is_flag=True),
            OptionSpec("--wsl-uuid", "use_wsl_uuid"),
            OptionSpec("--wsl-name", "use_wsl_name"),
        ],
    )
    ri = _ri(args)
    env = interface_use_list(
        wsl_uuid=(getattr(args, "use_wsl_uuid", "") or "").strip(),
        wsl_name=(getattr(args, "use_wsl_name", "") or "").strip(),
        user=ri.user,
        runtime_wsl_name=ri.wsl_name,
        use_all=bool(getattr(args, "use_all", False)),
        mounted_filter=None,
    )
    return emit_from_interface(args, env, opts)


def cmd_use_add(args: Namespace) -> int:
    opts = options_from_args(
        args,
        [
            OptionSpec("--registry-uuid", "use_registry_uuid"),
            OptionSpec("--registry-name", "use_registry_name"),
            OptionSpec("--wsl-uuid", "use_wsl_uuid"),
            OptionSpec("--wsl-name", "use_wsl_name"),
        ],
    )
    ri = _ri(args)
    env = interface_use_add(
        registry_uuid=getattr(args, "use_registry_uuid", "") or "",
        wsl_uuid=getattr(args, "use_wsl_uuid", "") or "",
        wsl_name=getattr(args, "use_wsl_name", "") or "",
        user=ri.user,
        runtime_wsl_name=ri.wsl_name,
    )
    return emit_from_interface(args, env, opts)


def cmd_use_remove(args: Namespace) -> int:
    opts = options_from_args(
        args,
        [
            OptionSpec("--registry-uuid", "use_registry_uuid"),
            OptionSpec("--registry-name", "use_registry_name"),
            OptionSpec("--wsl-uuid", "use_wsl_uuid"),
            OptionSpec("--wsl-name", "use_wsl_name"),
        ],
    )
    ri = _ri(args)
    env = interface_use_remove(
        registry_uuid=getattr(args, "use_registry_uuid", "") or "",
        wsl_uuid=getattr(args, "use_wsl_uuid", "") or "",
        registry_name=getattr(args, "use_registry_name", "") or "",
        wsl_name=getattr(args, "use_wsl_name", "") or "",
        user=ri.user,
        runtime_wsl_name=ri.wsl_name,
    )
    return emit_from_interface(args, env, opts)


def cmd_use_enable(args: Namespace) -> int:
    opts = options_from_args(
        args,
        [
            OptionSpec("--registry-uuid", "use_registry_uuid"),
            OptionSpec("--registry-name", "use_registry_name"),
            OptionSpec("--wsl-uuid", "use_wsl_uuid"),
            OptionSpec("--wsl-name", "use_wsl_name"),
        ],
    )
    ri = _ri(args)
    env = interface_use_enable(
        registry_uuid=getattr(args, "use_registry_uuid", "") or "",
        wsl_uuid=getattr(args, "use_wsl_uuid", "") or "",
        registry_name=getattr(args, "use_registry_name", "") or "",
        wsl_name=getattr(args, "use_wsl_name", "") or "",
        user=ri.user,
        runtime_wsl_name=ri.wsl_name,
    )
    return emit_from_interface(args, env, opts)


def cmd_use_disable(args: Namespace) -> int:
    opts = options_from_args(
        args,
        [
            OptionSpec("--registry-uuid", "use_registry_uuid"),
            OptionSpec("--registry-name", "use_registry_name"),
            OptionSpec("--wsl-uuid", "use_wsl_uuid"),
            OptionSpec("--wsl-name", "use_wsl_name"),
        ],
    )
    ri = _ri(args)
    env = interface_use_disable(
        registry_uuid=getattr(args, "use_registry_uuid", "") or "",
        wsl_uuid=getattr(args, "use_wsl_uuid", "") or "",
        registry_name=getattr(args, "use_registry_name", "") or "",
        wsl_name=getattr(args, "use_wsl_name", "") or "",
        user=ri.user,
        runtime_wsl_name=ri.wsl_name,
    )
    return emit_from_interface(args, env, opts)


def cmd_use_disableall(args: Namespace) -> int:
    opts = options_from_args(args, [OptionSpec("--quiet", "quiet", is_flag=True)])
    quiet = bool(getattr(args, "quiet", False))
    ri = _ri(args)
    env = interface_use_disableall(
        wsl_uuid=getattr(args, "use_wsl_uuid", "") or "",
        wsl_name=getattr(args, "use_wsl_name", "") or "",
        user=ri.user,
        runtime_wsl_name=ri.wsl_name,
    )
    if quiet:
        from commands.interface import status_of
        return status_of(env)
    return emit_from_interface(args, env, opts)


def _add_registry_pair(p) -> None:
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument(
        "-ru",
        "--registry-uuid",
        dest="use_registry_uuid",
        default="",
        metavar="UUID",
        help="Mount definition UUID",
    )
    g.add_argument(
        "-rn",
        "--registry-name",
        dest="use_registry_name",
        default="",
        help="Mount definition name",
    )


def _add_wsl_triple(p) -> None:
    g = p.add_mutually_exclusive_group(required=False)
    g.add_argument(
        "-wu",
        "--wsl-uuid",
        dest="use_wsl_uuid",
        default="",
        metavar="UUID",
        help="WSL UUID (optional; omit to use runtime WSL)",
    )
    g.add_argument(
        "-wn",
        "--wsl-name",
        dest="use_wsl_name",
        default="",
        help="WSL name (omit to use the current workspace)",
    )


def _add_wsl_only(p) -> None:
    g = p.add_mutually_exclusive_group(required=False)
    g.add_argument(
        "-wu",
        "--wsl-uuid",
        dest="use_wsl_uuid",
        default="",
        metavar="UUID",
        help="WSL row UUID (optional; default is runtime WSL)",
    )
    g.add_argument(
        "-wn",
        "--wsl-name",
        dest="use_wsl_name",
        default="",
        help="WSL name (default: runtime WSL)",
    )


def register_use_command(subparsers: _SubParsersAction) -> None:
    """Register ``use`` with real subcommand handlers."""
    use_fb = "Connect WSL workspaces with mount definitions or break those ties."
    use_desc = parser_description_from_manual("use", use_fb)
    help_line = help_summary_for_root("use", "Link WSLs to mount definitions")
    use = subparsers.add_parser(
        "use",
        help=help_line,
        description=use_desc,
    )
    use_sub = use.add_subparsers(
        dest="use_command",
        required=True,
        metavar="SUBCOMMAND",
        help="list | add|ua | remove|ur | enable|ue | disable|ud | disableall|uda",
    )

    list_help = "Show usage links (runtime WSL by default, use --all for every WSL)"
    lst = use_sub.add_parser("list", aliases=["ul"], help=list_help, description=list_help)
    _add_wsl_only(lst)
    lst.add_argument(
        "-a",
        "--all",
        dest="use_all",
        action="store_true",
        help="List links for all WSLs (ignore runtime/default WSL filter)",
    )
    lst.set_defaults(func=cmd_use_list)

    add_help = "Record that a WSL workspace should use a mount definition"
    add = use_sub.add_parser(
        "add",
        aliases=["ua"],
        help=add_help,
        description=add_help,
    )
    _add_registry_pair(add)
    _add_wsl_triple(add)
    add.set_defaults(func=cmd_use_add)

    for name, aliases, h, fn in (
        ("remove", ("ur",), "Stop a WSL from using a mount definition", cmd_use_remove),
        ("enable", ("ue",), "Turn this attachment on again", cmd_use_enable),
        ("disable", ("ud",), "Turn this attachment off for now", cmd_use_disable),
    ):
        p = use_sub.add_parser(name, aliases=list(aliases), help=h, description=h)
        _add_registry_pair(p)
        _add_wsl_triple(p)
        p.set_defaults(func=fn)

    da_help = "Turn off every mount attachment for this WSL"
    da = use_sub.add_parser("disableall", aliases=["uda"], help=da_help, description=da_help)
    _add_wsl_only(da)
    da.add_argument("-q", "--quiet", dest="quiet", action="store_true", help="Suppress all output")
    da.set_defaults(func=cmd_use_disableall)


def register_use_root_shortcuts(subparsers: _SubParsersAction) -> None:
    """Top-level shortcuts for `use` subcommands."""
    mapping: tuple[tuple[str, str, Callable[..., int]], ...] = (
        ("ul", "use list", cmd_use_list),
        ("ua", "use add", cmd_use_add),
        ("ur", "use remove", cmd_use_remove),
        ("ue", "use enable", cmd_use_enable),
        ("ud", "use disable", cmd_use_disable),
        ("uda", "use disableall", cmd_use_disableall),
    )
    for short, full, fn in mapping:
        sh = f"Shorthand for {full}"
        p = subparsers.add_parser(short, help=sh, description=sh)
        if short == "ul":
            _add_wsl_only(p)
            p.add_argument(
                "-a",
                "--all",
                dest="use_all",
                action="store_true",
                help="List links for all WSLs (ignore runtime/default WSL filter)",
            )
        elif short == "uda":
            _add_wsl_only(p)
            p.add_argument("-q", "--quiet", dest="quiet", action="store_true", help="Suppress all output")
        else:
            _add_registry_pair(p)
            _add_wsl_triple(p)
        p.set_defaults(func=fn)
