# WSL4AI — CLI/TUI specifications (`specs/tool/`)

**This directory** holds the **product** specifications for the Python CLI/TUI under `tool/`. Other specs (e.g. the **bootstrap installer**) live under [`../install/`](../install/). The index of all spec areas is [`../README.md`](../README.md).

Do not add parallel spec files outside `specs/` unless the project convention changes.

| Document | Contents |
| -------- | -------- |
| [specs.md](specs.md) | Global index: **§1** runtime identity, **§2** shared core rules (JSON/exit/output), **§4** command inventory, **§5** grouped command specs, **§7** style constants, **§8** CLI help/error formatting, **§9** special-command scope. |
| [specs-architecture.md](specs-architecture.md) | Layer diagram: CLI Consumer → api.py → TUI Consumer / Decorators. Mermaid diagrams, JSON envelope contract, file map. |
| [specs-install.md](specs-install.md) | `wsl4ai install ...` — `database`, `alias`, `update` and related rules. |
| [specs-registry.md](specs-registry.md) | `wsl4ai registry ...` — global command group (`list`, `add`, `remove`) with no WSL target selectors. |
| [specs-use.md](specs-use.md) | `wsl4ai use ...` — `list`, `add`, `remove`, `enable`, `disable`, `disableall` with optional WSL selectors, runtime default, and lifecycle state machine. |
| [specs-wsl.md](specs-wsl.md) | `wsl4ai wsl ...` — `list` and `set`, including `--cli`, optional WSL selectors, and runtime default target resolution. |
| [specs-whoami.md](specs-whoami.md) | `wsl4ai whoami` / `wai` runtime identity output contract (CLI only). |
| [specs-start.md](specs-start.md) | `wsl4ai start` — run one mounted use in foreground; CLI and TUI flows. |
| [specs-tui.md](specs-tui.md) | `wsl4ai tui` — TUI specification: menu model, scope rules, theme, log config, Start loop behavior, UI design (banner, menus, dialogs, buttons, style tokens). |
| [specs-config.md](specs-config.md) | `conf/config.json` — config file structure, schema versioning, update procedure, and config migrations. |
| [specs-mode.md](specs-mode.md) | *(planned)* `runtime.mode` — `wsl` vs `docker` mode: storage mechanism, installer changes, `defaults-*.env` split, tool changes. |
| [specs-future.md](specs-future.md) | Planned improvements not yet implemented: Docker mode, and other enhancements. |
| [specs-version.md](specs-version.md) | `-v` / `--version` flag — version string location and format. |
