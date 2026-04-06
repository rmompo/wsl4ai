"""CLI output decorator for JSON envelopes."""

from __future__ import annotations

import json

from commands.style_constants import GENERAL_ERROR, GENERAL_OK, HELP_NAME, LIST_IN_USE, LIST_NOT_IN_USE, tty_styled


def _safe_str(value) -> str:
    return str(value) if value is not None else ""


def try_parse_envelope(raw: str) -> dict | None:
    """Parse one JSON envelope from command raw stdout text."""
    text = (raw or "").strip()
    if not text:
        return None
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None
    if not {"runtimeId", "input", "output"} <= set(obj.keys()):
        return None
    return obj


def _format_registry_list(rows: list) -> list[str]:
    """Render registry list as a two-line-per-entry bordered table."""
    entries: list[dict[str, str]] = []
    for row in rows:
        fields = row.get("fields", []) if isinstance(row, dict) else []
        fmap = {f["key"]: f["value"] for f in fields if isinstance(f, dict) and "key" in f}
        entries.append(fmap)

    label_uuid = "UUID: "
    label_name = "Name: "
    label_host = "Host: "
    label_wsl  = "Wsl:  "

    w1 = len("Registry")
    w2 = len("Path")
    w3 = len("In use")
    for e in entries:
        w1 = max(w1, len(label_uuid) + len(e.get("registryUuid", "")),
                 len(label_name) + len(e.get("registryName", "")))
        w2 = max(w2, len(label_host) + len(e.get("hostPath", "")),
                 len(label_wsl)  + len(e.get("wslPath", "")))

    sep = f"+{'-' * (w1 + 2)}+{'-' * (w2 + 2)}+{'-' * (w3 + 2)}+"

    def plain_row(c1: str, c2: str, c3: str) -> str:
        return f"| {c1:<{w1}} | {c2:<{w2}} | {c3:<{w3}} |"

    def colored_row(c1: str, c2: str, in_use_raw: str) -> str:
        style = LIST_IN_USE if in_use_raw == "true" else LIST_NOT_IN_USE
        padded = tty_styled(f"{in_use_raw:<{w3}}", style)
        return f"| {c1:<{w1}} | {c2:<{w2}} | {padded} |"

    lines: list[str] = []
    header = tty_styled(plain_row("REGISTRY", "PATH", "IN USE"), HELP_NAME)
    lines.append(header)
    lines.append(sep)

    for e in entries:
        lines.append(colored_row(label_uuid + e.get("registryUuid", ""), label_host + e.get("hostPath", ""), e.get("inUse", "false")))
        lines.append(plain_row(label_name + e.get("registryName", ""), label_wsl  + e.get("wslPath",  ""), ""))
        lines.append(sep)

    return lines


def _format_use_list(rows: list) -> list[str]:
    """Render use list as a three-line-per-entry bordered table."""
    entries: list[dict[str, str]] = []
    for row in rows:
        fields = row.get("fields", []) if isinstance(row, dict) else []
        fmap = {f["key"]: f["value"] for f in fields if isinstance(f, dict) and "key" in f}
        entries.append(fmap)

    label_uuid = "UUID: "
    label_name = "Name: "
    label_user = "User: "

    w1 = len("Wsl")
    w2 = len("Registry")
    w3 = len("Mounted")
    for e in entries:
        w1 = max(w1, len(label_uuid) + len(e.get("wslUuid", "")),
                 len(label_name) + len(e.get("wslName", "")),
                 len(label_user) + len(e.get("wslUser", "")))
        w2 = max(w2, len(label_uuid) + len(e.get("registryUuid", "")),
                 len(label_name) + len(e.get("registryName", "")))

    sep = f"+{'-' * (w1 + 2)}+{'-' * (w2 + 2)}+{'-' * (w3 + 2)}+"

    def plain_row(c1: str, c2: str, c3: str) -> str:
        return f"| {c1:<{w1}} | {c2:<{w2}} | {c3:<{w3}} |"

    def mounted_row(c1: str, c2: str, mounted_raw: str) -> str:
        display = "true" if mounted_raw == "1" else "false"
        style = LIST_IN_USE if mounted_raw == "1" else LIST_NOT_IN_USE
        padded = tty_styled(f"{display:<{w3}}", style)
        return f"| {c1:<{w1}} | {c2:<{w2}} | {padded} |"

    lines: list[str] = []
    header = tty_styled(plain_row("WSL", "REGISTRY", "MOUNTED"), HELP_NAME)
    lines.append(header)
    lines.append(sep)

    for e in entries:
        lines.append(mounted_row(label_uuid + e.get("wslUuid", ""), label_uuid + e.get("registryUuid", ""), e.get("mounted", "0")))
        lines.append(plain_row(label_name + e.get("wslName", ""), label_name + e.get("registryName", ""), ""))
        lines.append(plain_row(label_user + e.get("wslUser", ""), "", ""))
        lines.append(sep)

    return lines


def _format_wsl_list(rows: list) -> list[str]:
    """Render wsl list as a three-line-per-entry bordered table."""
    entries: list[dict[str, str]] = []
    for row in rows:
        fields = row.get("fields", []) if isinstance(row, dict) else []
        fmap = {f["key"]: f["value"] for f in fields if isinstance(f, dict) and "key" in f}
        entries.append(fmap)

    label_uuid = "UUID: "
    label_name = "Name: "
    label_user = "User: "

    w1 = len("Wsl")
    w2 = len("CLI Command")
    for e in entries:
        w1 = max(w1, len(label_uuid) + len(e.get("wslUuid", "")),
                 len(label_name) + len(e.get("wslName", "")),
                 len(label_user) + len(e.get("wslUser", "")))
        w2 = max(w2, len(e.get("cliCommand", "")))

    sep = f"+{'-' * (w1 + 2)}+{'-' * (w2 + 2)}+"

    def plain_row(c1: str, c2: str) -> str:
        return f"| {c1:<{w1}} | {c2:<{w2}} |"

    lines: list[str] = []
    header = tty_styled(plain_row("WSL", "CLI COMMAND"), HELP_NAME)
    lines.append(header)
    lines.append(sep)

    for e in entries:
        lines.append(plain_row(label_uuid + e.get("wslUuid", ""), e.get("cliCommand", "")))
        lines.append(plain_row(label_name + e.get("wslName", ""), ""))
        lines.append(plain_row(label_user + e.get("wslUser", ""), ""))
        lines.append(sep)

    return lines


def _format_install_alias_list(rows: list) -> list[str]:
    """Render install alias list as a single-line-per-entry bordered table."""
    entries: list[dict[str, str]] = []
    for row in rows:
        fields = row.get("fields", []) if isinstance(row, dict) else []
        fmap = {f["key"]: f["value"] for f in fields if isinstance(f, dict) and "key" in f}
        entries.append(fmap)

    w1 = len("NAME")
    w2 = len("TYPE")
    for e in entries:
        w1 = max(w1, len(e.get("name", "")))
        w2 = max(w2, len(e.get("type", "")))

    sep = f"+{'-' * (w1 + 2)}+{'-' * (w2 + 2)}+"

    def plain_row(c1: str, c2: str) -> str:
        return f"| {c1:<{w1}} | {c2:<{w2}} |"

    lines: list[str] = []
    header = tty_styled(plain_row("NAME", "TYPE"), HELP_NAME)
    lines.append(header)
    lines.append(sep)

    for e in entries:
        lines.append(plain_row(e.get("name", ""), e.get("type", "")))
        lines.append(sep)

    return lines


def format_envelope_for_cli(envelope: dict) -> str:
    """Render a compact human-friendly CLI output from envelope JSON."""
    output = envelope.get("output", {}) if isinstance(envelope, dict) else {}
    input_obj = envelope.get("input", {}) if isinstance(envelope, dict) else {}
    result = output.get("result", {}) if isinstance(output, dict) else {}
    data = output.get("data", {}) if isinstance(output, dict) else {}
    rows = data.get("rows", []) if isinstance(data, dict) else []
    command = _safe_str(input_obj.get("command", "")).strip().lower() if isinstance(input_obj, dict) else ""
    subcommand = _safe_str(input_obj.get("subcommand", "")).strip().lower() if isinstance(input_obj, dict) else ""

    status = int(result.get("status", 1))
    message = _safe_str(result.get("message", "")).strip()
    uid = _safe_str(result.get("uuid", "")).strip()

    lines: list[str] = []
    show_headline = not (status == 0 and isinstance(rows, list) and len(rows) > 0)
    if show_headline:
        prefix = "OK" if status == 0 else "ERROR"
        headline = f"{prefix}: {message or '(no message)'}"
        headline = tty_styled(headline, GENERAL_OK if status == 0 else GENERAL_ERROR)
        lines.append(headline)
    if uid:
        lines.append(f"uuid: {uid}")

    if isinstance(rows, list) and rows:
        if status == 0 and command == "registry" and subcommand == "list":
            lines.extend(_format_registry_list(rows))
        elif status == 0 and command == "use" and subcommand == "list":
            lines.extend(_format_use_list(rows))
        elif status == 0 and command == "wsl" and subcommand == "list":
            lines.extend(_format_wsl_list(rows))
        elif status == 0 and command == "install" and subcommand == "alias":
            options = input_obj.get("options", []) if isinstance(input_obj, dict) else []
            alias_action = next((o.get("value", "") for o in options if isinstance(o, dict) and o.get("key") == "--action"), "")
            if alias_action == "list":
                lines.extend(_format_install_alias_list(rows))
        else:
            if status == 0 and command == "whoami":
                lines.append("WSL4AI Runtime ID:")
            for idx, row in enumerate(rows, start=1):
                fields = row.get("fields", []) if isinstance(row, dict) else []
                if isinstance(fields, list):
                    for fld in fields:
                        if not isinstance(fld, dict):
                            continue
                        key = _safe_str(fld.get("key", "")).strip()
                        val = _safe_str(fld.get("value", ""))
                        if key:
                            if status == 0 and command == "whoami" and key == "machine":
                                key = "workstation"
                            lines.append(f"  {key}: {val}")
                if len(rows) > 1 and idx < len(rows):
                    lines.append("")
    return "\n".join(lines)
