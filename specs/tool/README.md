# WSL4AI — CLI/TUI specifications (`specs/tool/`)

**This directory** holds the **product** specifications for the Python CLI/TUI under `tool/`. Other specs (e.g. the **bootstrap installer**) live under [`../install/`](../install/). The index of all spec areas is [`../README.md`](../README.md).

Do not add parallel spec files outside `specs/` unless the project convention changes.

| Document | Contents |
| -------- | -------- |
| [specs.md](specs.md) | Global index: **§1** runtime identity, **§2** shared core rules (JSON/exit/output), **§4** command inventory, **§5** grouped command specs, **§7** style constants, **§8** special-command scope. |
| [specs-install.md](specs-install.md) | `wsl4ai install ...` — `tool`, `database`, `alias` and related rules. |
| [specs-registry.md](specs-registry.md) | `wsl4ai registry ...` — global command group (`list`, `add`, `remove`) with no WSL target selectors. |
| [specs-use.md](specs-use.md) | `wsl4ai use ...` — `list`, `add`, `remove`, `enable`, `disable`, `disableall` with optional WSL selectors and runtime default. |
| [specs-wsl.md](specs-wsl.md) | `wsl4ai wsl ...` — `list` and `set`, including `--cli`, optional WSL selectors, and runtime default target resolution. |
| [specs-whoami.md](specs-whoami.md) | `wsl4ai whoami` / `wai` runtime identity output contract. |
| [specs-start.md](specs-start.md) | `wsl4ai start` placeholder behavior. |
| [specs-tui.md](specs-tui.md) | `wsl4ai tui` interactive Text User Interface specification and theme model. |
