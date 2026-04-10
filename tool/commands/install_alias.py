"""Alias installer/remover for `wsl4ai install alias`."""

from __future__ import annotations

import re
import sys
from argparse import Namespace
from pathlib import Path

from commands.alias_bash import BASH_BEGIN, BASH_END, bashrc_path
from commands.alias_ps import PS_BEGIN, PS_END, profile_paths
from commands.api_json import OptionSpec, emit_envelope, options_from_args, row_from_pairs


def _script_and_python() -> tuple[str, str]:
    script_path = str((Path(__file__).resolve().parent.parent / "wsl4ai.py"))
    python_exe = sys.executable
    return script_path, python_exe


def _extract_block(content: str, begin: str, end: str) -> tuple[str, str, str]:
    b = content.find(begin)
    e = content.find(end)
    if b == -1 or e == -1 or e <= b:
        return content, "", ""
    e2 = e + len(end)
    before = content[:b].rstrip()
    block = content[b:e2]
    after = content[e2:].lstrip()
    return before, block, after


def _build_ps_block(names: list[str], script_path: str, python_exe: str) -> str:
    lines = [PS_BEGIN]
    for name in names:
        lines.extend(
            [
                f"function {name} {{",
                f"    & \"{python_exe}\" \"{script_path}\" @args",
                "}",
            ]
        )
    lines.append(PS_END)
    return "\n".join(lines) + "\n"


def _build_bash_block(names: list[str], script_path: str, python_exe: str) -> str:
    lines = [BASH_BEGIN]
    for name in names:
        lines.extend(
            [
                f"{name}() {{",
                f"  \"{python_exe}\" \"{script_path}\" \"$@\"",
                "}",
            ]
        )
    lines.append(BASH_END)
    return "\n".join(lines) + "\n"


def _ps_names_from_block(block: str) -> list[str]:
    return re.findall(r"(?m)^function\s+([A-Za-z_][\w-]*)\s*\{", block)


def _bash_names_from_block(block: str) -> list[str]:
    return re.findall(r"(?m)^([A-Za-z_][\w-]*)\s*\(\)\s*\{", block)


def _apply_alias_change(
    *,
    existing: str,
    begin: str,
    end: str,
    names: list[str],
    action: str,
    shell_type: str,
    script_path: str,
    python_exe: str,
) -> tuple[str, list[tuple[str, str]]]:
    before, block, after = _extract_block(existing, begin, end)
    current_names = _ps_names_from_block(block) if shell_type == "ps" else _bash_names_from_block(block)
    current_set = set(current_names)
    statuses: list[tuple[str, str]] = []
    target = list(current_names)

    for nm in names:
        if action == "add":
            if nm in current_set:
                statuses.append((nm, "error_exists"))
                continue
            target.append(nm)
            current_set.add(nm)
            statuses.append((nm, "added"))
        else:
            if nm not in current_set:
                statuses.append((nm, "error_not_found"))
                continue
            target = [x for x in target if x != nm]
            current_set = set(target)
            statuses.append((nm, "removed"))

    if shell_type == "ps":
        new_block = _build_ps_block(target, script_path, python_exe)
    else:
        new_block = _build_bash_block(target, script_path, python_exe)

    if not target:
        updated = before
        if after:
            updated = (updated + "\n\n" + after) if updated else after
        updated = updated.rstrip() + ("\n" if updated else "")
        return updated, statuses

    body = before + ("\n\n" if before else "") + new_block
    if after:
        body += ("\n" if not body.endswith("\n") else "") + "\n" + after
    return body, statuses


def cmd_install_alias(args: Namespace) -> int:
    names = [str(x).strip() for x in (getattr(args, "alias_names", []) or []) if str(x).strip()]
    action = (getattr(args, "alias_action", "") or "").strip().lower()
    opts = options_from_args(args, [OptionSpec("--action", "alias_action"), OptionSpec("--name", "alias_names")])
    from commands.api import emit_from_api, api_alias_add, api_alias_list, api_alias_remove
    if action == "list":
        return emit_from_api(args, api_alias_list(), opts, include_data=True)
    if action == "add":
        return emit_from_api(args, api_alias_add(names), opts)
    if action == "remove":
        return emit_from_api(args, api_alias_remove(names), opts)
    from commands.api_json import emit_envelope
    return emit_envelope(args=args, command="install", subcommand="alias", options=opts, status=1, message="install alias: --action is required")

