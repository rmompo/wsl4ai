# Specification: `wsl4ai wsl ...`

Command group for WSL rows and per-WSL command settings.
This group follows the global optional-WSL rule in [`specs.md`](specs.md): if WSL selectors are omitted, runtime identity is used.

---

## 1. Subcommands

- `wsl list` (`wl`)
- `wsl set` (`ws`)

---

## 2. `wsl list`

- Purpose: query known `wsls` rows and `cli_command` values.
- Options: none.
- Output contract:
  - Always `output.result`
  - Include `output.data.rows` (query operation)

---

## 3. `wsl set`

- Purpose: update `wsls.cli_command` for a target WSL row.
- Required options:
  - `-c` / `--cli`
- Optional target selectors:
  - `-wu` / `--wsl-uuid`
  - `-wn` / `--wsl-name`
- Optionality + default:
  - Both selectors are optional.
  - If neither selector is provided, target is resolved from runtime (`RuntimeIdentity` -> `wsl_name` + `user` -> `wsl_uuid`).
- Output contract:
  - Always `output.result`
  - No `output.data` (non-query operation)

Behavior:

1. Requires `-c` / `--cli` with non-empty value.
2. Resolves WSL target by one of:
   - `--wsl-uuid`
   - `--wsl-name` (scoped to runtime user)
   - Runtime fallback (`wsl_name` + `user`) when selectors are omitted
3. Does not auto-create `wsls` rows.
4. Updates `wsls.cli_command` for the resolved row.

