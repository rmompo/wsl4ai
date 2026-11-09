"""Print the version of every component (see ``specs/tool/specs-version.md`` §5)."""

from argparse import Namespace, _SubParsersAction

from commands.api import api_version, emit_from_api
from commands.api_json import OptionSpec, options_from_args


def cmd_version(args: Namespace) -> int:
    """Return the component versions as a JSON envelope."""
    opts = options_from_args(args, [
        OptionSpec("--remote", "remote", is_flag=True),
        OptionSpec("--branch", "branch"),
    ])
    env = api_version(
        remote=bool(getattr(args, "remote", False)),
        branch=str(getattr(args, "branch", "") or "main"),
    )
    return emit_from_api(args, env, opts, include_data=True)


def _add(subparsers: _SubParsersAction, name: str, help_text: str) -> None:
    sub = subparsers.add_parser(name, help=help_text, description=help_text)
    sub.add_argument("--remote", action="store_true", help="Compare with the manifest of the repository on GitHub")
    sub.add_argument("-b", "--branch", metavar="BRANCH", help="Repository branch used with --remote (default: main)")
    sub.set_defaults(func=cmd_version)


def register_version_command(subparsers: _SubParsersAction) -> None:
    _add(subparsers, "version", "Show the version of every component (tool, schemas, updater, installer, scripts)")
    _add(subparsers, "ver", "Shorthand for version")
