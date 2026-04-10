#!/usr/bin/env python3
"""WSL4AI CLI entrypoint and command registration."""

import json
import sys
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from commands.cli_help import (
    Wsl4aiArgumentParser,
    argv_contains_help_flag,
    print_help_for_argv,
    print_wsl4ai_root_help,
)
from commands.common import resolve_runtime_identity
from commands.core import register_core_commands
from commands.help_md import root_description_short, root_epilog_short
from commands.install import register_install_command
from commands.output_decorator import format_envelope_for_cli, try_parse_envelope

__version__ = "1.5.89"
__config_version__ = "1.0"

APP_DIR = Path(__file__).resolve().parent
CONF_DIR = APP_DIR.parent / "conf"
DDBB_DIR = CONF_DIR / "ddbb"

_INSTALL_COMMANDS = {"install", "it", "id", "ia", "iu"}


def _parse_config_version(v: str) -> tuple[int, ...]:
    try:
        return tuple(int(x) for x in v.split("."))
    except (ValueError, AttributeError):
        return ()


def _check_config_version(command: str) -> None:
    """Abort if config.json schema version is older than required.

    Skipped for install commands — they handle setup and migration.
    Skipped if config.json does not yet exist (fresh install).
    """
    if command in _INSTALL_COMMANDS:
        return
    config_path = CONF_DIR / "config.json"
    if not config_path.is_file():
        return
    try:
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return
    meta = cfg.get("metadata")
    if not meta or not meta.get("schema_version"):
        raise SystemExit(
            "Error: config.json has no schema version. Run: wsl4ai install update"
        )
    local_v = _parse_config_version(meta["schema_version"])
    required_v = _parse_config_version(__config_version__)
    if not local_v or local_v < required_v:
        raise SystemExit(
            f"Error: config schema is {meta['schema_version']} but tool requires "
            f"{__config_version__}. Run: wsl4ai install update"
        )


def _ensure_layout() -> None:
    """Validate mandatory WSL4AI folder layout.

    Required directories:
        - `conf/ddbb/`: SQLite database directory.

    Raises:
        RuntimeError: If one or more required directories are missing.
    """
    missing = []
    if not DDBB_DIR.is_dir():
        missing.append(str(DDBB_DIR))
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(f"Invalid WSL4AI layout. Missing required directories: {joined}")


def build_parser() -> Wsl4aiArgumentParser:
    """Build the top-level CLI parser and attach all command groups.

    Returns:
        Wsl4aiArgumentParser: Configured parser instance with registered command handlers.
    """
    parser = Wsl4aiArgumentParser(
        prog="wsl4ai",
        description=root_description_short(),
        epilog=root_epilog_short(),
    )

    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"wsl4ai {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", required=False)

    register_core_commands(subparsers)
    register_install_command(subparsers)

    return parser


def main() -> int:
    """Run WSL4AI CLI.

    Returns:
        int: Exit code returned by the selected command handler.
    """
    argv = sys.argv[1:]
    parser = build_parser()

    try:
        if argv_contains_help_flag(argv):
            return print_help_for_argv(parser, argv)

        args = parser.parse_args()

        if not getattr(args, "command", None):
            print_wsl4ai_root_help(parser)
            return 1

        _ensure_layout()
        _check_config_version(args.command)
        args.app_version = __version__
        ri = resolve_runtime_identity()
        args.runtime_identity = ri
        args.machine = ri.machine
        args.user = ri.user
        args.wsl_name = ri.wsl_name
        if bool(getattr(args, "bypass_capture", False)):
            return int(args.func(args))
        buf = StringIO()
        with redirect_stdout(buf):
            rc = int(args.func(args))
        raw = buf.getvalue()
        env = try_parse_envelope(raw)
        if env is None:
            # Fallback for commands that still print plain text/help.
            print(raw, end="")
        else:
            print(format_envelope_for_cli(env))
        return rc
    finally:
        print(file=sys.stdout)


if __name__ == "__main__":
    raise SystemExit(main())
