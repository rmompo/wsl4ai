"""Interactive Text User Interface for WSL4AI."""

from __future__ import annotations

import json
import os
from argparse import Namespace
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Callable

try:
    import questionary
    from prompt_toolkit.styles import Style
except Exception:  # pragma: no cover - optional dependency at runtime
    questionary = None
    Style = None

from commands.add_remove import cmd_add, cmd_remove
from commands.install_alias import cmd_install_alias
from commands.install_database import cmd_install_database
from commands.install_tool import cmd_install_tool
from commands.list_registry import cmd_list as cmd_registry_list
from commands.common import APP_DIR
from commands.output_decorator import format_envelope_for_cli, try_parse_envelope
from commands.start import cmd_start
from commands.style_constants import GENERAL_ERROR, tty_styled
from commands.use_commands import (
    cmd_use_add,
    cmd_use_disable,
    cmd_use_disableall,
    cmd_use_enable,
    cmd_use_list,
    cmd_use_remove,
)
from commands.whoami import cmd_whoami
from commands.wsl_cli import cmd_wsl_list, cmd_wsl_set

THEMES_DIR = APP_DIR / "tui_themes"
THEME_CONFIG_PATH = APP_DIR.parent / "conf" / "config.json"
DEFAULT_THEME_ID = "normal_dark"
THEME_LABELS: list[tuple[str, str]] = [
    ("Normal (Dark)", "normal_dark"),
    ("Normal (Light)", "normal_light"),
    ("Bright (Dark)", "bright_dark"),
    ("Bright (Light)", "bright_light"),
    ("Color Blind (Dark)", "color_blind_dark"),
    ("Color Blind (Light)", "color_blind_light"),
    ("High Contrast", "high_contrast"),
]
_CURRENT_THEME_ID = DEFAULT_THEME_ID


def _theme_ids() -> set[str]:
    return {tid for _, tid in THEME_LABELS}


def _load_theme_config() -> str:
    """Load theme from strict schema {\"tui\": {\"theme\": \"...\"}}.

    On missing/invalid/unknown values, rewrite config with default theme.
    """
    if not THEME_CONFIG_PATH.is_file():
        _save_theme_config(DEFAULT_THEME_ID)
        return DEFAULT_THEME_ID
    try:
        data = json.loads(THEME_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        _save_theme_config(DEFAULT_THEME_ID)
        return DEFAULT_THEME_ID
    if not isinstance(data, dict):
        _save_theme_config(DEFAULT_THEME_ID)
        return DEFAULT_THEME_ID
    tui_obj = data.get("tui", {})
    if not isinstance(tui_obj, dict):
        _save_theme_config(DEFAULT_THEME_ID)
        return DEFAULT_THEME_ID
    theme_id = str(tui_obj.get("theme", "") or "").strip()
    if theme_id in _theme_ids():
        return theme_id
    _save_theme_config(DEFAULT_THEME_ID)
    return DEFAULT_THEME_ID


def _save_theme_config(theme_id: str) -> None:
    if theme_id not in _theme_ids():
        return
    payload = {"tui": {"theme": theme_id}}
    THEME_CONFIG_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _set_theme(theme_id: str) -> None:
    global _CURRENT_THEME_ID
    _CURRENT_THEME_ID = theme_id if theme_id in _theme_ids() else DEFAULT_THEME_ID


def _load_theme_styles(theme_id: str) -> dict[str, str]:
    theme_file = THEMES_DIR / f"{theme_id}.json"
    if not theme_file.is_file():
        return {}
    try:
        data = json.loads(theme_file.read_text(encoding="utf-8"))
    except Exception:
        return {}
    styles = data.get("styles", {})
    if not isinstance(styles, dict):
        return {}
    out: dict[str, str] = {}
    for key, value in styles.items():
        k = str(key).strip()
        v = str(value).strip()
        if k and v:
            out[k] = v
    return out


def _theme():
    if Style is None:
        return None
    if os.environ.get("NO_COLOR"):
        return Style.from_dict({})
    styles = _load_theme_styles(_CURRENT_THEME_ID)
    if not styles:
        styles = _load_theme_styles(DEFAULT_THEME_ID)
    return Style.from_dict(styles)


def _select(message: str, choices: list[str]) -> str | None:
    if questionary is None:
        return None
    return questionary.select(message, choices=choices, style=_theme()).ask()


def _text(message: str, default: str = "") -> str | None:
    if questionary is None:
        return None
    return questionary.text(message, default=default, style=_theme()).ask()


def _confirm(message: str, default: bool = False) -> bool | None:
    if questionary is None:
        return None
    return questionary.confirm(message, default=default, style=_theme()).ask()


def _emit(msg: str) -> None:
    print(msg)
    print()


def _rows_from_envelope(envelope: dict) -> list[dict]:
    output = envelope.get("output", {}) if isinstance(envelope, dict) else {}
    data = output.get("data", {}) if isinstance(output, dict) else {}
    rows = data.get("rows", []) if isinstance(data, dict) else []
    return rows if isinstance(rows, list) else []


def _fields_to_map(row: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    fields = row.get("fields", []) if isinstance(row, dict) else []
    if not isinstance(fields, list):
        return out
    for field in fields:
        if not isinstance(field, dict):
            continue
        key = str(field.get("key", "") or "").strip()
        if not key:
            continue
        out[key] = str(field.get("value", "") or "")
    return out


def _invoke(
    root_args: Namespace,
    func: Callable[[Namespace], int],
    command: str,
    subcommand: str,
    **kwargs,
) -> tuple[int, dict | None]:
    args = Namespace(**kwargs)
    args.command = command
    args.runtime_identity = root_args.runtime_identity
    args.machine = root_args.machine
    args.user = root_args.user
    args.wsl_name = root_args.wsl_name
    buf = StringIO()
    with redirect_stdout(buf):
        rc = int(func(args))
    env = try_parse_envelope(buf.getvalue())
    return rc, env


def _run_and_print(
    root_args: Namespace,
    func: Callable[[Namespace], int],
    command: str,
    subcommand: str,
    **kwargs,
) -> tuple[int, dict | None]:
    rc, env = _invoke(root_args, func, command, subcommand, **kwargs)
    if env is None:
        _emit(tty_styled("ERROR: invalid command envelope", GENERAL_ERROR))
        return 1, None
    _emit(format_envelope_for_cli(env))
    return rc, env


def _wait() -> None:
    if questionary is None:
        return
    questionary.text("Press Enter to continue", default="", style=_theme()).ask()


def _theme_label(theme_id: str) -> str:
    for label, tid in THEME_LABELS:
        if tid == theme_id:
            return label
    return "Unknown"


def _theme_menu() -> None:
    selected = _select("Theme", [label for label, _ in THEME_LABELS] + ["Go back"])
    if selected in (None, "Go back"):
        return
    theme_id = next((tid for label, tid in THEME_LABELS if label == selected), "")
    if not theme_id:
        return
    _set_theme(theme_id)
    _save_theme_config(theme_id)
    _emit(f"Theme applied: {_theme_label(theme_id)}")
    _wait()


def _registry_refs(root_args: Namespace) -> list[dict[str, str]]:
    _, env = _invoke(root_args, cmd_registry_list, "registry", "list")
    refs: list[dict[str, str]] = []
    if not env:
        return refs
    for row in _rows_from_envelope(env):
        mapped = _fields_to_map(row)
        if "registryUuid" in mapped and "registryName" in mapped and "wslUuid" not in mapped:
            refs.append(mapped)
    return refs


def _wsl_refs(root_args: Namespace) -> list[dict[str, str]]:
    _, env = _invoke(root_args, cmd_wsl_list, "wsl", "list")
    refs: list[dict[str, str]] = []
    if not env:
        return refs
    for row in _rows_from_envelope(env):
        mapped = _fields_to_map(row)
        if "wslUuid" in mapped and "wslName" in mapped:
            refs.append(mapped)
    return refs


def _pick_registry_uuid(root_args: Namespace) -> str | None:
    refs = _registry_refs(root_args)
    if not refs:
        _emit("No registries found.")
        return None
    labels: dict[str, str] = {}
    for item in refs:
        label = (
            f"{item.get('registryName', '<unnamed>')} | "
            f"{item.get('hostPath', '')} -> {item.get('wslPath', '')} | "
            f"{item.get('registryUuid', '')}"
        )
        labels[label] = item.get("registryUuid", "")
    selected = _select("Select a registry", list(labels.keys()))
    return labels.get(selected) if selected else None


def _pick_mounted_use_registry_uuid(root_args: Namespace) -> str | None:
    _, env = _invoke(
        root_args,
        cmd_use_list,
        "use",
        "list",
        use_all=False,
        use_wsl_uuid="",
        use_wsl_name="",
    )
    if not env:
        _emit("Unable to load use links.")
        return None
    labels: dict[str, str] = {}
    for row in _rows_from_envelope(env):
        mapped = _fields_to_map(row)
        if mapped.get("mounted", "") != "1":
            continue
        reg_uuid = mapped.get("registryUuid", "").strip()
        if not reg_uuid:
            continue
        reg_name = mapped.get("registryName", "<unnamed>")
        wsl_name = mapped.get("wslName", "")
        wsl_user = mapped.get("wslUser", "")
        labels[f"{reg_name} | mounted=1 | {wsl_name}/{wsl_user} | {reg_uuid}"] = reg_uuid
    if not labels:
        _emit("No mounted use links found for runtime WSL.")
        return None
    selected = _select("Select mounted use to start", list(labels.keys()))
    return labels.get(selected) if selected else None


def _registry_menu(root_args: Namespace) -> None:
    while True:
        choice = _select("Registry", ["List", "Add", "Remove", "Go back"])
        if choice in (None, "Go back"):
            return
        if choice == "List":
            _run_and_print(root_args, cmd_registry_list, "registry", "list")
            _wait()
            continue
        if choice == "Add":
            name = (_text("Registry name") or "").strip()
            host = (_text("Host path segment") or "").strip()
            wsl = (_text("WSL path segment") or "").strip()
            if not name or not host or not wsl:
                _emit(tty_styled("ERROR: name, host, and wsl are required", GENERAL_ERROR))
                _wait()
                continue
            force = bool(_confirm("Skip path checks (--force)?", default=False))
            _run_and_print(root_args, cmd_add, "registry", "add", name=name, host=host, wsl=wsl, force=force)
            _wait()
            continue
        if choice == "Remove":
            reg_uuid = _pick_registry_uuid(root_args)
            if not reg_uuid:
                _wait()
                continue
            ok = _confirm("This will remove the selected registry. Continue?", default=False)
            if not ok:
                _emit("Operation cancelled.")
                _wait()
                continue
            _run_and_print(root_args, cmd_remove, "registry", "remove", remove_uuid=reg_uuid, remove_name="")
            _wait()


def _use_menu(root_args: Namespace) -> None:
    while True:
        choice = _select("Use", ["List", "Add", "Remove", "Enable", "Disable", "Disableall", "Go back"])
        if choice in (None, "Go back"):
            return
        if choice == "List":
            _run_and_print(
                root_args,
                cmd_use_list,
                "use",
                "list",
                use_all=False,
                use_wsl_uuid="",
                use_wsl_name="",
            )
            _wait()
            continue

        if choice == "Disableall":
            ok = _confirm("Disable all use links for this WSL?", default=False)
            if not ok:
                _emit("Operation cancelled.")
                _wait()
                continue
            _run_and_print(
                root_args,
                cmd_use_disableall,
                "use",
                "disableall",
                use_wsl_uuid="",
                use_wsl_name="",
            )
            _wait()
            continue

        reg_uuid = _pick_registry_uuid(root_args)
        if not reg_uuid:
            _wait()
            continue
        if choice == "Add":
            _run_and_print(
                root_args,
                cmd_use_add,
                "use",
                "add",
                use_registry_uuid=reg_uuid,
                use_registry_name="",
                use_wsl_uuid="",
                use_wsl_name="",
            )
        elif choice == "Remove":
            ok = _confirm("Remove this use link?", default=False)
            if not ok:
                _emit("Operation cancelled.")
                _wait()
                continue
            _run_and_print(
                root_args,
                cmd_use_remove,
                "use",
                "remove",
                use_registry_uuid=reg_uuid,
                use_registry_name="",
                use_wsl_uuid="",
                use_wsl_name="",
            )
        elif choice == "Enable":
            _run_and_print(
                root_args,
                cmd_use_enable,
                "use",
                "enable",
                use_registry_uuid=reg_uuid,
                use_registry_name="",
                use_wsl_uuid="",
                use_wsl_name="",
            )
        elif choice == "Disable":
            _run_and_print(
                root_args,
                cmd_use_disable,
                "use",
                "disable",
                use_registry_uuid=reg_uuid,
                use_registry_name="",
                use_wsl_uuid="",
                use_wsl_name="",
            )
        _wait()


def _wsl_menu(root_args: Namespace) -> None:
    while True:
        choice = _select("WSL", ["List", "Set", "Go back"])
        if choice in (None, "Go back"):
            return
        if choice == "List":
            _run_and_print(root_args, cmd_wsl_list, "wsl", "list")
            _wait()
            continue
        cli_cmd = (_text("CLI command value (--cli)") or "").strip()
        if not cli_cmd:
            _emit(tty_styled("ERROR: --cli must be non-empty", GENERAL_ERROR))
            _wait()
            continue
        _run_and_print(
            root_args,
            cmd_wsl_set,
            "wsl",
            "set",
            wsl_cli=cli_cmd,
            wsl_set_wsl_uuid="",
            wsl_set_wsl_name="",
        )
        _wait()


def _install_menu(root_args: Namespace) -> None:
    while True:
        choice = _select("Install", ["Tool", "Database", "Alias", "Go back"])
        if choice in (None, "Go back"):
            return
        if choice == "Tool":
            _run_and_print(root_args, cmd_install_tool, "install", "tool")
            _wait()
            continue
        if choice == "Database":
            force = bool(_confirm("Force recreate database (--force)?", default=False))
            if force:
                ok = _confirm("This action is destructive. Continue?", default=False)
                if not ok:
                    _emit("Operation cancelled.")
                    _wait()
                    continue
            _run_and_print(root_args, cmd_install_database, "install", "database", force=force)
            _wait()
            continue
        action = _select("Alias action", ["add", "remove"])
        shell_type = _select("Alias type", ["ps", "bash"])
        names_raw = (_text("Alias names (comma-separated)") or "").strip()
        names = [x.strip() for x in names_raw.split(",") if x.strip()]
        if not action or not shell_type or not names:
            _emit(tty_styled("ERROR: action, type, and at least one alias name are required", GENERAL_ERROR))
            _wait()
            continue
        if action == "remove":
            ok = _confirm("Remove selected aliases?", default=False)
            if not ok:
                _emit("Operation cancelled.")
                _wait()
                continue
        _run_and_print(
            root_args,
            cmd_install_alias,
            "install",
            "alias",
            alias_action=action,
            alias_type=shell_type,
            alias_names=names,
        )
        _wait()


def cmd_tui(args: Namespace) -> int:
    """Run interactive text UI and dispatch existing command handlers."""
    if questionary is None:
        _emit(tty_styled("ERROR: questionary is required; run pip install -r requirements.txt", GENERAL_ERROR))
        return 1
    _set_theme(_load_theme_config())
    print("WSL4AI Text User Interface")
    print()
    try:
        while True:
            current = _theme_label(_CURRENT_THEME_ID)
            choice = _select(
                "Main menu",
                ["Registry", "Use", "WSL", "Install", "Whoami", "Start", f"Theme ({current})", "Exit"],
            )
            if choice in (None, "Exit"):
                return 0
            if choice == "Registry":
                _registry_menu(args)
            elif choice == "Use":
                _use_menu(args)
            elif choice == "WSL":
                _wsl_menu(args)
            elif choice == "Install":
                _install_menu(args)
            elif choice == "Whoami":
                _run_and_print(args, cmd_whoami, "whoami", "")
                _wait()
            elif choice == "Start":
                reg_uuid = _pick_mounted_use_registry_uuid(args)
                if not reg_uuid:
                    _wait()
                    continue
                _run_and_print(
                    args,
                    cmd_start,
                    "start",
                    "",
                    start_registry_uuid=reg_uuid,
                    start_registry_name="",
                    start_wsl_uuid="",
                    start_wsl_name="",
                )
                _wait()
            elif choice.startswith("Theme "):
                _theme_menu()
    except KeyboardInterrupt:
        print()
        return 0

