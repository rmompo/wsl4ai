"""`wsl4ai install update`: delegate to standalone wsl4ai-update.py."""

import os
import sys
from argparse import Namespace

from commands.api_json import OptionSpec, emit_envelope, options_from_args
from commands.common import APP_DIR

UPDATE_SCRIPT = APP_DIR.parent / "conf" / "wsl4ai-update.py"


def cmd_install_update(args: Namespace) -> int:
    opts = options_from_args(args, [OptionSpec("--check", "check_only", is_flag=True)])
    check_only = bool(getattr(args, "check_only", False))

    if not UPDATE_SCRIPT.is_file():
        return emit_envelope(
            args=args, command="install", subcommand="update", options=opts,
            status=1, message=f"update: updater script not found: {UPDATE_SCRIPT}",
        )

    argv = [sys.executable, str(UPDATE_SCRIPT)]
    if check_only:
        argv.append("--check")

    os.execv(sys.executable, argv)
    # unreachable
    return 0
