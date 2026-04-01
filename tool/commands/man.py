"""Manual command: show wsl4ia-man.md in the terminal via Rich Markdown."""

from argparse import Namespace, _SubParsersAction
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown

from commands.common import MAN_DIR

MANUAL_MD = MAN_DIR / "wsl4ia-man.md"


def _show_manual_in_console(md_path: Path) -> int:
    if not md_path.is_file():
        print(f"Manual not found: {md_path}")
        return 1
    text = md_path.read_text(encoding="utf-8")
    Console(soft_wrap=True).print(Markdown(text))
    return 0


def cmd_man(_: Namespace) -> int:
    """Show ``wsl4ia-man.md`` rendered as Markdown (requires ``rich``)."""
    return _show_manual_in_console(MANUAL_MD)


def register_man_command(subparsers: _SubParsersAction) -> None:
    """Register `man` subcommand (no arguments)."""
    man = subparsers.add_parser(
        "man",
        help="Show the full Markdown command reference",
    )
    man.set_defaults(func=cmd_man)
