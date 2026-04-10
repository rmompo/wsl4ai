# Specification: `wsl4ai registry ...`

Command group for registry lifecycle management.

---

## 1. Subcommands

| Subcommand | Shortcut | Purpose |
|------------|----------|---------|
| `registry list` | `rl` | List all registries with resolved paths and in-use status |
| `registry add` | `ra` | Insert a new registry definition |
| `registry remove` | `rr` | Delete a registry (only if no use links exist) |

Scope rule: `registry` is global and does not expose WSL target selectors (`--wsl-uuid` / `--wsl-name` are not part of this command group).

---

## 2. `registry list`

Purpose: query registry rows with resolved full paths and linked usage information.

- Invocation: `wsl4ai registry list` · `wsl4ai rl`
- Output contract: always `output.result` + `output.data.rows` (query operation).

### Options

None.


Behavior:

1. Requires database file (`conf/ddbb/wsl4ai.db`).
2. Reads `registries` ordered by case-insensitive name.
3. Resolves host/wsl display paths from `conf/local.env` (`HOST_PROJECTS`, `WSL_PROJECTS`) with path-template expansion.
4. For each registry, checks if any `uses` row exists (in-use indicator).
5. Empty set is valid success (`status=0` with empty rows).

Row fields: `registryUuid`, `registryName`, `hostPath`, `wslPath`, `inUse`.

```mermaid
flowchart LR
    subgraph CLI
        rl["wsl4ai registry list\nwsl4ai rl"]
        cmd_list["list_registry.cmd_list()"]
        rl --> cmd_list
    end
    subgraph Interface["api.py"]
        iface["api_registry_list()"]
    end
    subgraph TUI
        dispatch["_dispatch\n(['Registry','List'])"]
        ldiag["ListDialog\n(read-only)"]
    end
    subgraph TUI_Dec["tui_decorator.py"]
        rec["registry_list_records()"]
    end

    cmd_list -->|"call"| iface
    dispatch -->|"call"| iface
    iface -->|"envelope"| cmd_list
    iface -->|"envelope"| rec
    rec --> ldiag
    cmd_list -->|"emit_from_api()"| stdout([stdout])
```

---

## 3. `registry add`

Purpose: insert one registry definition (DB only — no filesystem changes at this stage).

- Invocation: `wsl4ai registry add -n <name> -H <host_rel> -w <wsl_rel> [-f]` · `wsl4ai ra ...`
- Output contract: always `output.result`; `output.result.uuid` contains the new UUID.

### Options

| Flag | Long | Metavar | Required | Description |
|------|------|---------|----------|-------------|
| `-n` | `--name` | NAME | **yes** | Name for the registry (case-insensitive unique) |
| `-H` | `--host` | PATH | **yes** | Host-side folder segment appended to `HOST_PROJECTS` |
| `-w` | `--wsl` | PATH | **yes** | WSL-side folder segment appended to `WSL_PROJECTS` |
| `-f` | `--force` | — | no | Skip host-path existence check |

Rules:

- Required values must be non-empty after trim.
- Name uniqueness is case-insensitive.
- Without `--force`, the resolved absolute host path (`HOST_PROJECTS/rel_path_host`) must exist on disk.
- Insert target table: `registries` (`uuid`, `name`, `rel_path_host`, `rel_path_wsl`).
- **No filesystem changes**: directory creation happens in `use add`.

```mermaid
flowchart LR
    subgraph CLI
        ra["wsl4ai registry add\n-n name -H host -w wsl"]
        cmd_add["add_remove.cmd_add()"]
        ra --> cmd_add
    end
    subgraph Interface["api.py"]
        iface["api_registry_add\n(name, host_rel, wsl_rel, force)"]
    end
    subgraph TUI
        dlg["RegistryAddDialog\n._try_submit()"]
    end

    cmd_add -->|"call"| iface
    dlg -->|"call"| iface
    iface -->|"envelope"| cmd_add
    iface -->|"envelope → status"| dlg
    cmd_add -->|"emit_from_api()"| stdout([stdout])
    dlg -->|"notify success/error"| ui([TUI notify])
```

---

## 4. `registry remove`

Purpose: remove one registry row when no active use links exist.

- Invocation: `wsl4ai registry remove (-u <uuid> | -n <name>)` · `wsl4ai rr ...`
- Output contract: always `output.result`.

### Options

| Flag | Long | Metavar | Required | Description |
|------|------|---------|----------|-------------|
| `-u` | `--uuid` | UUID | one of -u / -n | Select registry by UUID |
| `-n` | `--name` | NAME | one of -u / -n | Select registry by name (case-insensitive) |

At least one of `-u` / `-n` must be provided. If both are given, `-u` takes precedence.

Rules:

- If any `uses` row references the target registry, removal is rejected — run `use disable` + `use remove` for all links first.
- If no links: `DELETE FROM registries`.
- **No filesystem changes**: `registry remove` only deletes from DB.

```mermaid
flowchart LR
    subgraph CLI
        rr["wsl4ai registry remove\n-u uuid | -n name"]
        cmd_rm["add_remove.cmd_remove()"]
        rr --> cmd_rm
    end
    subgraph Interface["api.py"]
        iface_list["api_registry_list()"]
        iface_rm["api_registry_remove\n(registry_uuid, registry_name)"]
    end
    subgraph TUI
        dlg_init["RegistryRemoveDialog\n.__init__() — load list"]
        dlg_check["._confirm_remove()\ncount_uses_for_registry()"]
        dlg_rm["._confirm_remove()\non Ok: remove"]
        dlg_init --> dlg_check --> dlg_rm
    end
    subgraph TUI_Dec["tui_decorator.py"]
        rec["registry_list_records()"]
    end

    cmd_rm -->|"call"| iface_rm
    dlg_init -->|"call"| iface_list
    dlg_rm -->|"call"| iface_rm
    iface_list -->|"envelope"| rec --> dlg_init
    iface_rm -->|"envelope"| cmd_rm
    iface_rm -->|"envelope → status"| dlg_rm
    cmd_rm -->|"emit_from_api()"| stdout([stdout])
    dlg_rm -->|"notify success/error"| ui([TUI notify])
```
