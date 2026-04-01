"""CLI output decorator for JSON envelopes."""

from __future__ import annotations

import json

from commands.style_constants import GENERAL_ERROR, GENERAL_OK, tty_styled


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


def format_envelope_for_cli(envelope: dict) -> str:
    """Render a compact human-friendly CLI output from envelope JSON."""
    output = envelope.get("output", {}) if isinstance(envelope, dict) else {}
    input_obj = envelope.get("input", {}) if isinstance(envelope, dict) else {}
    result = output.get("result", {}) if isinstance(output, dict) else {}
    data = output.get("data", {}) if isinstance(output, dict) else {}
    rows = data.get("rows", []) if isinstance(data, dict) else []
    command = _safe_str(input_obj.get("command", "")).strip().lower() if isinstance(input_obj, dict) else ""

    status = int(result.get("status", 1))
    message = _safe_str(result.get("message", "")).strip()
    uid = _safe_str(result.get("uuid", "")).strip()

    lines: list[str] = []
    show_headline = not (status == 0 and isinstance(rows, list) and len(rows) > 0)
    if show_headline:
        prefix = "OK" if status == 0 else "ERROR"
        headline = f"{prefix}: {message or '(no message)'}"
        if status == 0:
            headline = tty_styled(headline, GENERAL_OK)
        else:
            headline = tty_styled(headline, GENERAL_ERROR)
        lines.append(headline)
    if uid:
        lines.append(f"uuid: {uid}")

    if isinstance(rows, list) and rows:
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

