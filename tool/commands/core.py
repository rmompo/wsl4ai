"""Core WSL4AI command routers."""

from argparse import _SubParsersAction

from commands.registry import register_registry_command, register_registry_root_shortcuts
from commands.start import register_start_command
from commands.tui import cmd_tui
from commands.use_commands import register_use_command, register_use_root_shortcuts
from commands.wsl_cli import register_wsl_command, register_wsl_root_shortcuts
from commands.whoami import register_whoami_command


def register_core_commands(subparsers: _SubParsersAction) -> None:
    """Register core command names with placeholder handlers.

    Args:
        subparsers (_SubParsersAction): Root subparser registry.
    """
    register_whoami_command(subparsers)
    register_registry_command(subparsers)
    register_registry_root_shortcuts(subparsers)
    register_use_command(subparsers)
    register_use_root_shortcuts(subparsers)
    register_wsl_command(subparsers)
    register_wsl_root_shortcuts(subparsers)
    register_start_command(subparsers)
    th = "Open interactive text user interface"
    tui = subparsers.add_parser("tui", help=th, description=th)
    tui.set_defaults(func=cmd_tui, bypass_capture=True)
