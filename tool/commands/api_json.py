"""Shared JSON envelope helpers for command handlers."""

from __future__ import annotations

import json
from argparse import Namespace
from dataclasses import dataclass


@dataclass
class OptionSpec:
    """Map argparse attributes to normalized long-form option keys."""

    key: str
    attr: str
    is_flag: bool = False


def _runtime_id(args: Namespace) -> dict[str, str]:
    return {
        "machine": str(getattr(args, "machine", "") or ""),
        "user": str(getattr(args, "user", "") or ""),
    }


def options_from_args(args: Namespace, specs: list[OptionSpec]) -> list[dict[str, str]]:
    """Build normalized long-form option list from argparse namespace."""
    out: list[dict[str, str]] = []
    for spec in specs:
        val = getattr(args, spec.attr, None)
        if spec.is_flag:
            if bool(val):
                out.append({"key": spec.key, "value": "true"})
            continue
        if val is None:
            continue
        if isinstance(val, list):
            for item in val:
                if str(item).strip():
                    out.append({"key": spec.key, "value": str(item)})
            continue
        sval = str(val)
        if sval == "":
            continue
        out.append({"key": spec.key, "value": sval})
    return out


def row_from_pairs(pairs: list[tuple[str, str]]) -> dict[str, list[dict[str, str]]]:
    return {"fields": [{"key": str(k), "value": str(v)} for k, v in pairs]}


def emit_envelope(
    *,
    args: Namespace,
    command: str,
    subcommand: str = "",
    options: list[dict[str, str]] | None = None,
    status: int = 0,
    message: str = "",
    uuid: str = "",
    rows: list[dict[str, list[dict[str, str]]]] | None = None,
    include_data: bool | None = None,
) -> int:
    """Render one JSON envelope to stdout and return status."""
    if include_data is None:
        include_data = (subcommand == "list")

    output_obj: dict[str, object] = {
        "result": {
            "status": int(status),
            "message": message,
            "uuid": uuid,
        }
    }
    if include_data:
        output_obj["data"] = {"rows": rows or []}

    payload = {
        "runtimeId": _runtime_id(args),
        "input": {
            "command": command,
            "subcommand": subcommand,
            "options": options or [],
        },
        "output": output_obj,
    }
    print(json.dumps(payload, ensure_ascii=False))
    return int(status)

