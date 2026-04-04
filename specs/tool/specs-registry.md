# Specification: `wsl4ai registry ...`

Command group for registry lifecycle management.

---

## 1. Subcommands

- `registry list` (`rl`)
- `registry add` (`ra`)
- `registry remove` (`rr`)

Scope rule:

- `registry` is global and does not expose WSL target selectors (`--wsl-uuid` / `--wsl-name` are not part of this command group).

---

## 2. `registry list`

Purpose: query registry rows and linked usage information.

- Invocation:
  - `wsl4ai registry list`
  - `wsl4ai registry rl`
  - `wsl4ai rl`
- Options: none.
- Output contract:
  - Always `output.result`
  - Include `output.data.rows` (query operation)

Behavior:

1. Requires database file (`ddbb/wsl4ai.db`).
2. Reads `registries` ordered by case-insensitive name.
3. Resolves host/wsl display paths from `parameters` (`base_path_host`, `base_path_wsl`) with path-template expansion.
4. For each registry, includes linked `uses` + `wsls` information.
5. Empty set is valid success (`status=0` with empty rows).

---

## 3. `registry add`

Purpose: insert one registry definition.

- Invocation:
  - `wsl4ai registry add --name <name> --host <host_segment> --wsl <wsl_segment> [--force]`
  - `wsl4ai registry ra ...`
  - `wsl4ai ra ...`
- Required options:
  - `-n` / `--name`
  - `-H` / `--host`
  - `-w` / `--wsl`
- Optional:
  - `-f` / `--force` (skip path existence checks)
- Output contract:
  - Always `output.result`
  - No `output.data` (non-query operation)

Rules:

- Required values must be non-empty after trim.
- Name uniqueness is case-insensitive.
- Without `--force`, the resolved host absolute path (`HOST_PROJECTS/rel_path_host`) must exist on disk.
- Insert target table: `registries` (`uuid`, `name`, `rel_path_host`, `rel_path_wsl`).
- **No filesystem changes**: `registry add` only writes to the database. Directory creation happens in `use add`.

---

## 4. `registry remove`

Purpose: remove one registry row when no active links exist.

- Invocation:
  - `wsl4ai registry remove --uuid <uuid>`
  - `wsl4ai registry remove --name <name>`
  - `wsl4ai registry rr ...`
  - `wsl4ai rr ...`
- Selectors:
  - `-u` / `--uuid`
  - `-n` / `--name`
- Rule: at least one selector required; if both are given, lookup is by `uuid`.
- Output contract:
  - Always `output.result`
  - No `output.data` (non-query operation)

Rules:

- If linked rows exist in `uses` for the target registry, removal is rejected. Run `use disable` + `use remove` for all linked uses first.
- If not linked, delete from `registries`.
- **No filesystem changes**: `registry remove` only deletes from the database. Directory removal happens in `use disable`.

