"""TUI Decorator — convert api envelope dicts to ListDialog record format.

Each function accepts a JSON envelope dict returned by an ``api_*()`` function
and returns ``(header: str, records: list)`` suitable for ``ListDialog``.

Record format (matches what tui.py ListDialog expects)::

    records = [
        [
            (label_str, value_str),   # field 0
            (label_str, value_str),   # field 1
            ...
        ],
        ...
    ]

The label strings are right-padded via ``_lpad(label, width)`` (same helper used in tui.py).
"""
from __future__ import annotations

from commands.api import message_of, rows_of, status_of


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _lpad(label: str, width: int) -> str:
    """Right-pad *label* to *width* chars, then append one space."""
    return label.ljust(width) + " "


def _fields(row: dict) -> dict:
    """Flatten a ``row_from_pairs`` row to a plain ``{key: value}`` dict."""
    return {f["key"]: f["value"] for f in row.get("fields", [])}


def _error_record(message: str) -> tuple[str, list]:
    return "LIST", [[("", f"Error: {message}")]]


def _empty_record(message: str = "(no entries)") -> tuple[str, list]:
    return "LIST", [[(  "", message)]]


# ─── Registry ─────────────────────────────────────────────────────────────────

def registry_list_records(envelope: dict) -> tuple[str, list]:
    """Convert ``api_registry_list()`` envelope to ListDialog records.

    Fields per row: UUID / Name / Path Host / Path Wsl / In Use
    """
    if status_of(envelope) != 0:
        return _error_record(message_of(envelope))
    rows = rows_of(envelope)
    if not rows:
        return _empty_record()
    W = 9  # max("Path Host") = 9
    records = []
    for row in rows:
        f = _fields(row)
        records.append([
            (_lpad("UUID",      W), f.get("registryUuid", "")),
            (_lpad("Name",      W), f.get("registryName", "")),
            (_lpad("Path Host", W), f.get("hostPath", "")),
            (_lpad("Path Wsl",  W), f.get("wslPath",  "")),
            (_lpad("In Use",    W), "yes" if f.get("inUse") == "true" else "no"),
        ])
    return "LIST", records


def registry_available_records(envelope: dict) -> tuple[str, list]:
    """Convert ``api_registry_list_available()`` envelope to ListDialog records.

    Fields per row: UUID / Name / Path Host / Path Wsl
    """
    if status_of(envelope) != 0:
        return _error_record(message_of(envelope))
    rows = rows_of(envelope)
    if not rows:
        return _empty_record("(no registries available)")
    W = 9
    records = []
    for row in rows:
        f = _fields(row)
        records.append([
            (_lpad("UUID",      W), f.get("registryUuid", "")),
            (_lpad("Name",      W), f.get("registryName", "")),
            (_lpad("Path Host", W), f.get("hostPath", "")),
            (_lpad("Path Wsl",  W), f.get("wslPath",  "")),
        ])
    return "LIST", records


# ─── Use ──────────────────────────────────────────────────────────────────────

def use_list_records(envelope: dict) -> tuple[str, list]:
    """Convert ``api_use_list()`` envelope to ListDialog records.

    Fields per row: Registry UUID / Registry Name / Wsl UUID / Wsl Name / Mounted
    """
    if status_of(envelope) != 0:
        return _error_record(message_of(envelope))
    rows = rows_of(envelope)
    if not rows:
        return _empty_record()
    W = 13  # max("Registry UUID") = 13
    records = []
    for row in rows:
        f = _fields(row)
        mounted = f.get("mounted", "0")
        records.append([
            (_lpad("Registry UUID", W), f.get("registryUuid", "")),
            (_lpad("Registry Name", W), f.get("registryName", "")),
            (_lpad("Wsl UUID",      W), f.get("wslUuid",      "")),
            (_lpad("Wsl Name",      W), f.get("wslName",      "")),
            (_lpad("Mounted",       W), "yes" if mounted == "1" else "no"),
        ])
    return "LIST", records


def use_list_mounted_records(envelope: dict) -> tuple[str, list]:
    """Convert ``api_use_list_mounted()`` envelope to ListDialog records.

    Fields per row: Registry UUID / Registry Name / Path Host / Path Wsl
    """
    if status_of(envelope) != 0:
        return _error_record(message_of(envelope))
    rows = rows_of(envelope)
    if not rows:
        return _empty_record("(no mounted uses)")
    W = 13  # max("Registry UUID") = 13
    records = []
    for row in rows:
        f = _fields(row)
        records.append([
            (_lpad("Registry UUID", W), f.get("registryUuid", "")),
            (_lpad("Registry Name", W), f.get("registryName", "")),
            (_lpad("Path Host",     W), f.get("hostPath",     "")),
            (_lpad("Path Wsl",      W), f.get("wslPath",      "")),
        ])
    return "LIST", records


# ─── WSL ──────────────────────────────────────────────────────────────────────

def wsl_list_records(envelope: dict) -> tuple[str, list]:
    """Convert ``api_wsl_list()`` envelope to ListDialog records.

    Fields per row: UUID / Name / User / CLI cmd
    """
    if status_of(envelope) != 0:
        return _error_record(message_of(envelope))
    rows = rows_of(envelope)
    if not rows:
        return _empty_record("(no WSL rows)")
    W = 7  # max("CLI cmd") = 7
    records = []
    for row in rows:
        f = _fields(row)
        records.append([
            (_lpad("UUID",    W), f.get("wslUuid",    "")),
            (_lpad("Name",    W), f.get("wslName",    "")),
            (_lpad("User",    W), f.get("wslUser",    "")),
            (_lpad("CLI cmd", W), f.get("cliCommand", "")),
        ])
    return "LIST", records


# ─── Alias ────────────────────────────────────────────────────────────────────

def alias_list_records(envelope: dict) -> tuple[str, list]:
    """Convert ``api_alias_list()`` envelope to ListDialog records.

    Fields per row: Name / Type
    """
    if status_of(envelope) != 0:
        return _error_record(message_of(envelope))
    rows = rows_of(envelope)
    if not rows:
        return _empty_record("(no aliases)")
    W = 4  # max("Name") = 4
    records = []
    for row in rows:
        f = _fields(row)
        records.append([
            (_lpad("Name", W), f.get("name", "")),
            (_lpad("Type", W), f.get("type", "")),
        ])
    return "LIST", records
