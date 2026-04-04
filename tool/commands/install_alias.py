"""Alias installer/remover for `wsl4ai install alias`."""

from __future__ import annotations

import platform
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
    shell_type = "ps" if platform.system() == "Windows" else "bash"
    specs = [
        OptionSpec("--action", "alias_action"),
        OptionSpec("--name", "alias_names"),
    ]
    options = options_from_args(args, specs)
    if not action or not shell_type:
        return emit_envelope(
            args=args,
            command="install",
            subcommand="alias",
            options=options,
            status=1,
            message="install alias: --action is required",
        )
    if action in ("add", "remove") and not names:
        return emit_envelope(
            args=args,
            command="install",
            subcommand="alias",
            options=options,
            status=1,
            message="install alias: --name is required for add/remove actions",
        )
    script_path, python_exe = _script_and_python()
    rows: list[dict[str, list[dict[str, str]]]] = []
    failures = 0
    targets: list[Path]
    begin: str
    end: str
    if shell_type == "ps":
        targets = profile_paths()
        begin, end = PS_BEGIN, PS_END
    else:
        targets = [bashrc_path()]
        begin, end = BASH_BEGIN, BASH_END

    if action == "list":
        for target_path in targets:
            existing = target_path.read_text(encoding="utf-8") if target_path.exists() else ""
            _, block, _ = _extract_block(existing, begin, end)
            current_names = _ps_names_from_block(block) if shell_type == "ps" else _bash_names_from_block(block)
            for alias_name in current_names:
                rows.append(
                    row_from_pairs(
                        [
                            ("type", shell_type),
                            ("name", alias_name),
                            ("action", "list"),
                            ("status", "ok"),
                        ]
                    )
                )
        return emit_envelope(
            args=args,
            command="install",
            subcommand="alias",
            options=options,
            status=0,
            message="install alias: list completed",
            rows=rows,
        )

    # Treat each alias name as one logical unit across all target profiles.
    profile_state: list[tuple[Path, str, list[str]]] = []
    for target_path in targets:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        existing = target_path.read_text(encoding="utf-8") if target_path.exists() else ""
        _, block, _ = _extract_block(existing, begin, end)
        current_names = _ps_names_from_block(block) if shell_type == "ps" else _bash_names_from_block(block)
        profile_state.append((target_path, existing, current_names))

    requested = list(dict.fromkeys(names))
    status_by_name: dict[str, str] = {}
    to_add: list[str] = []
    to_remove: list[str] = []

    for alias_name in requested:
        exists_anywhere = any(alias_name in set(curr) for _, _, curr in profile_state)
        if action == "add":
            if exists_anywhere:
                status_by_name[alias_name] = "error_exists"
            else:
                status_by_name[alias_name] = "added"
                to_add.append(alias_name)
        else:
            if exists_anywhere:
                status_by_name[alias_name] = "removed"
                to_remove.append(alias_name)
            else:
                status_by_name[alias_name] = "error_not_found"

    for target_path, existing, _ in profile_state:
        effective_names: list[str] = []
        _, block, _ = _extract_block(existing, begin, end)
        current_names = _ps_names_from_block(block) if shell_type == "ps" else _bash_names_from_block(block)
        for nm in current_names:
            if nm not in to_remove and nm not in effective_names:
                effective_names.append(nm)
        for nm in to_add:
            if nm not in effective_names:
                effective_names.append(nm)

        if shell_type == "ps":
            new_block = _build_ps_block(effective_names, script_path, python_exe)
        else:
            new_block = _build_bash_block(effective_names, script_path, python_exe)

        before, _, after = _extract_block(existing, begin, end)
        if not effective_names:
            updated = before
            if after:
                updated = (updated + "\n\n" + after) if updated else after
            updated = updated.rstrip() + ("\n" if updated else "")
        else:
            updated = before + ("\n\n" if before else "") + new_block
            if after:
                updated += ("\n" if not updated.endswith("\n") else "") + "\n" + after
        target_path.write_text(updated, encoding="utf-8")

    for alias_name in requested:
        st = status_by_name.get(alias_name, "error_unknown")
        if st.startswith("error_"):
            failures += 1
        rows.append(
            row_from_pairs(
                [
                    ("type", shell_type),
                    ("name", alias_name),
                    ("action", action),
                    ("status", st),
                ]
            )
        )

    status = 1 if failures > 0 else 0
    if status == 0:
        if shell_type == "ps":
            message = "install alias: completed; reload PowerShell profile (. $PROFILE) or open a new console"
        else:
            message = "install alias: completed; reload shell (source ~/.startup-wsl4ai.sh) or open a new terminal"
    else:
        message = "install alias: one or more aliases failed"
    return emit_envelope(
        args=args,
        command="install",
        subcommand="alias",
        options=options,
        status=status,
        message=message,
        rows=rows,
    )

