# Specification: `wsl4ai start`

Launch one concrete mounted `use` in the current terminal session.

---

## 1. Purpose

`start` resolves a single `uses` link, changes directory to the resolved WSL path, and executes the target WSL `cli_command`.

---

## 2. CLI: inputs and target resolution

- Invocation: `wsl4ai start (-ru <uuid> | -rn <name>) [-wu <uuid> | -wn <name>]`

### Options

| Flag | Long | Metavar | Required | Description |
|------|------|---------|----------|-------------|
| `-ru` | `--registry-uuid` | UUID | one of -ru/-rn | Registry UUID of the use to start |
| `-rn` | `--registry-name` | NAME | one of -ru/-rn | Registry name of the use to start |
| `-wu` | `--wsl-uuid` | UUID | no | Target WSL UUID (default: runtime WSL) |
| `-wn` | `--wsl-name` | NAME | no | Target WSL name (default: runtime WSL) |

If WSL selector is omitted, runtime identity is used (`RuntimeIdentity` → runtime `wsl_name` + runtime `user`).

This identifies one concrete `use`: (`wsl_uuid`, `registry_uuid`).

---

## 3. Security and execution rules (normative)

1. The `use` row must exist; otherwise fail.
2. The `use` row must have `mounted=1`; otherwise fail (security gate).
3. The working directory is resolved as: `WSL_PROJECTS` (from `local.env`) + `rel_path_wsl` (from selected `registry`).
4. `wsls.cli_command` for the resolved `wsl_uuid` must be non-empty; otherwise fail.
5. Execution mode is foreground in the same terminal session (not detached).
6. TUI-triggered `start` also runs in the same console session.

The command is fail-closed: any missing/invalid dependency prevents execution.

---

## 4. Output contract

- Always `output.result`
- No `output.data` (action command)
- `output.result.status`: `0` on success, non-zero for validation errors or subprocess failure

---

## 5. CLI flow

The CLI `start` command accesses the database directly (does not use the api layer).

```mermaid
flowchart LR
    subgraph CLI
        st["wsl4ai start\n-ru uuid | -rn name"]
        cmd["start.cmd_start()"]
        st --> cmd
    end
    subgraph DB["Database (direct)"]
        resolve["resolve_registry_target()\nresolve_wsl_uuid()"]
        query["SELECT uses JOIN registries JOIN wsls\nWHERE mounted=1"]
        resolve --> query
    end
    subgraph Exec
        run["subprocess.run(cli_command\ncwd=workdir)"]
    end

    cmd -->|"connect_db"| resolve
    query -->|"mounted, rel_path_wsl, cli_command"| cmd
    cmd --> run --> stdout([exit code → stdout])
```

---

## 6. TUI flow

In the TUI, **Start** is a menu item (not a dialog with selectors). It shows all `mounted=1` uses for the runtime WSL. After the user selects one and confirms, the TUI exits and `cmd_tui` runs the tool. When the tool exits, the TUI relaunches automatically.

```mermaid
flowchart TD
    subgraph TUI_Consumer["TUI Consumer (tui.py)"]
        dispatch["_dispatch(['Start'])"]
        prep["api_start_prepare\n(wsl_name, user)\n— validates cli_command"]
        mnt["api_use_list_mounted\n(wsl_name, user)\n— mounted=1 rows"]
        diag["StartDialog\n— picker"]
        pending["_pending_start =\n{cli, workdir, name}"]
        exit_app["Wsl4aiApp.exit()"]

        dispatch --> prep
        prep -->|"ok"| mnt
        mnt --> diag
        diag -->|"user selects"| pending
        pending --> exit_app
    end
    subgraph TUI_Dec["tui_decorator.py"]
        rec["use_list_mounted_records()"]
    end
    subgraph cmd_tui["cmd_tui() loop"]
        run["subprocess.run(cli)\ncwd=workdir"]
        relaunch["_load_theme()\nWsl4aiApp.run()"]
        run --> relaunch
    end

    mnt -->|"envelope"| rec --> diag
    exit_app -->|"_pending_start"| run
```
