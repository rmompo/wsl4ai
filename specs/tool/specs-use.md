# Specification: `wsl4ai use ...`

Core (non-special) commands. Align with **[`specs.md`](specs.md)** §2. Implementation: [`commands/use_commands.py`](../commands/use_commands.py), [`commands/wsl_db.py`](../commands/wsl_db.py). WSL resolution uses **`RuntimeIdentity`** (`args.runtime_identity`: `machine`, `user`, `wsl_name` from `WSL_DISTRO_NAME` or `default`).

---

## 1. Shared flags

- **Registry (required** for `add`, `remove`, `enable`, `disable`**):** exactly one of **`--registry-uuid`** or **`--registry-name`** (case-insensitive name).
- **WSL (optional):** at most one of **`--wsl-uuid`** or **`--wsl-name`**. If neither is set, the target `wsls` row is resolved by **`wsl_name` + `user`** from runtime identity.
- **`--wsl-name`** matches `wsls` where `LOWER(name)` and **`wsls.user`** equals runtime **`user`**.
- This follows the global rule in [`specs.md`](specs.md): optional WSL selectors default to runtime target when omitted.

---

## 2. `use list`

Query all usage links (`uses` rows) with joined registry/WSL context.

- Shortcut: `wsl4ai ul`
- Optional WSL filters:
  - `--wsl-uuid`
  - `--wsl-name`
- Optional scope override:
  - `-a` / `--all` (list links for all WSLs)
- Combination rule:
  - `--all` cannot be combined with `--wsl-uuid` or `--wsl-name`.
- Default behavior:
  - If neither `--wsl-uuid` nor `--wsl-name` nor `--all` is passed, list is scoped to runtime WSL.
  - If `--wsl-uuid`/`--wsl-name` is passed, list is scoped to that WSL.
  - If `--all` is passed, list is global across all WSLs.
- Output contract:
  - Always `output.result`
  - Include `output.data.rows` (query operation)

---

## 3. `use add`

1. Resolve `registry_uuid`. Resolve `wsl_uuid` via `resolve_wsl_uuid` with **`create_if_missing=True`**: insert **`wsls`** (`cli_command NULL`) if missing.
2. If **`uses`** already has `(wsl_uuid, registry_uuid)` → error.
3. Else **`INSERT INTO uses (wsl_uuid, registry_uuid, mounted)`** with **`mounted = 0`**.

WSL target selectors are optional; if omitted, target WSL is resolved from runtime identity.

**Shortcuts:** `wsl4ai ua`.

Output contract:
- Always `output.result`
- No `output.data` (non-query operation)

---

## 4. `use remove`

1. Resolve `wsl_uuid` (**no** auto-create) and `registry_uuid`.
2. If no **`uses`** row → error.
3. If **`mounted = 1`** → error (`use disable` first).
4. Else **`DELETE`** that **`uses`** row.

WSL target selectors are optional.

**Shortcuts:** `wsl4ai ur`.

Output contract:
- Always `output.result`
- No `output.data` (non-query operation)

---

## 5. `use enable`

Activates one `uses` link: creates the WSL directory and bind-mounts the host path onto it.

**Execution order (strict):**
1. Resolve `wsl_uuid` and `registry_uuid`; fetch `rel_path_host` and `rel_path_wsl` from `registries`.
2. Resolve full paths from **`local.env`** (`HOST_PROJECTS` + `rel_path_host`, `WSL_PROJECTS` + `rel_path_wsl`).
3. **Create directory**: `os.makedirs(wsl_path, exist_ok=True)`.
4. **Mount**: `sudo mount --bind <host_path> <wsl_path>`. If mount fails, remove the created directory and return error.
5. **Update DB**: `UPDATE uses SET mounted = 1` — only on mount success.

If no `uses` row → error. Path resolution errors (missing `local.env` keys) → error.

WSL target selectors are optional.

**Shortcuts:** `wsl4ai ue`.

Output contract:
- Always `output.result`
- No `output.data` (non-query operation)

---

## 6. `use disable`

Deactivates one `uses` link: unmounts and removes the WSL directory.

**Execution order (strict):**
1. Resolve `wsl_uuid` and `registry_uuid`; fetch `rel_path_wsl` from `registries`.
2. Resolve full WSL path from **`local.env`** (`WSL_PROJECTS` + `rel_path_wsl`).
3. **Unmount**: `sudo umount <wsl_path>`. If unmount fails → error (stop).
4. **Remove directory**: `os.rmdir(wsl_path)`. If removal fails → error (stop).
5. **Update DB**: `UPDATE uses SET mounted = 0` — only when both steps succeed.

If no `uses` row → error.

WSL target selectors are optional.

**Shortcuts:** `wsl4ai ud`.

Output contract:
- Always `output.result`
- No `output.data` (non-query operation)

---

## 7. `use disableall`

Applies `use disable` logic to **all** `uses` rows of the runtime WSL, regardless of their `mounted` state.

**Behavior:**
1. Resolve `wsl_uuid` from runtime identity (no WSL selector options).
2. Query **all** `uses` rows for that `wsl_uuid` (no `mounted` filter).
3. For each row, call `_disable_one` (umount → rmdir → update DB).
4. Continue processing remaining rows even if one fails.
5. Report total disabled and any errors.

**Options:**
- `-q` / `--quiet`: suppress all output; return exit code only (`0` = all ok, `1` = any failure).

Called automatically on session start via `.bashrc` with `--quiet`.

**Shortcuts:** `wsl4ai uda`.

Output contract:
- Always `output.result` (unless `--quiet`)
- `output.data.rows` lists each successfully disabled use (unless `--quiet`)

---

## 8. Implementation reference

- `commands/use_commands.py` — handlers, `_disable_one` helper, argparse.
- `commands/wsl_db.py` — `resolve_wsl_uuid`, `resolve_registry_target`.
- `commands/common.py` — `load_local_env_paths`, `expand_path_template`.
