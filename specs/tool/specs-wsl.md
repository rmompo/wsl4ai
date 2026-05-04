# Specification: `wsl4ai wsl ...`

Command group for WSL rows and per-WSL command settings.
This group follows the global optional-WSL rule in [`specs.md`](specs.md): if WSL selectors are omitted, runtime identity is used.

---

## 1. Subcommands

| Subcommand | Shortcut | Purpose |
|------------|----------|---------|
| `wsl list` | `wl` | List all known `wsls` rows and their `cli_command` values |
| `wsl set` | `ws` | Update `wsls.cli_command` for a target WSL row |

---

## 2. `wsl list`

- Invocation: `wsl4ai wsl list` · `wsl4ai wl`
- Purpose: query known `wsls` rows and `cli_command` values.
- Output contract: always `output.result` + `output.data.rows`.

### Options

None.

Row fields: `wslUuid`, `wslName`, `wslUser`, `cliCommand`.

```mermaid
flowchart LR
    subgraph CLI
        wl["wsl4ai wsl list\nwsl4ai wl"]
        cmd["wsl_cli.cmd_wsl_list()"]
        wl --> cmd
    end
    subgraph Interface["api.py"]
        iface["api_wsl_list()"]
    end
    subgraph TUI
        dispatch["_dispatch(['Wsl','List'])"]
        ldiag["ListDialog (read-only)"]
        wsl_set_init["WslSetDialog.__init__()\n— picker for wsl set"]
    end
    subgraph TUI_Dec["tui_decorator.py"]
        rec["wsl_list_records()"]
    end

    cmd --> iface
    dispatch --> iface
    wsl_set_init --> iface
    iface -->|"envelope"| cmd
    iface -->|"envelope"| rec
    rec --> ldiag
    rec --> wsl_set_init
    cmd -->|"emit_from_api()"| stdout([stdout])
```

---

## 3. `wsl set`

- Invocation: `wsl4ai wsl set -c <value> [-wu <uuid> | -wn <name>]` · `wsl4ai ws ...`
- Purpose: update `wsls.cli_command` for a target WSL row.
- Does not auto-create `wsls` rows.
- Output contract: always `output.result`.

### Options

| Flag | Long | Metavar | Required | Description |
|------|------|---------|----------|-------------|
| `-c` | `--cli` | VALUE | **yes** | Command this WSL workspace should run when invoked |
| `-wu` | `--wsl-uuid` | UUID | no | Target WSL UUID (default: runtime WSL) |
| `-wn` | `--wsl-name` | NAME | no | Target WSL name (default: runtime WSL) |

```mermaid
flowchart LR
    subgraph CLI
        ws["wsl4ai wsl set\n-c 'claude' [-wu uuid | -wn name]"]
        cmd["wsl_cli.cmd_wsl_set()"]
        ws --> cmd
    end
    subgraph Interface["api.py"]
        iface_list["api_wsl_list()"]
        iface_set["api_wsl_set\n(cli_command, wsl_uuid,\nwsl_name, user,\nruntime_wsl_name)"]
    end
    subgraph TUI
        wsl_sel["WslSetDialog\n— picker: select WSL row"]
        wsl_form["WslSetFormDialog\n._do_save()"]
        wsl_sel --> wsl_form
    end
    subgraph TUI_Dec["tui_decorator.py"]
        rec["wsl_list_records()"]
    end

    cmd --> iface_set
    wsl_sel --> iface_list --> rec --> wsl_sel
    wsl_form --> iface_set
    iface_set -->|"envelope"| cmd
    iface_set -->|"envelope → status"| wsl_form
    cmd -->|"emit_from_api()"| stdout([stdout])
    wsl_form -->|"notify success/error"| ui([TUI notify])
```
