# Specification: `wsl4ai use ...`

Core (non-special) commands. Align with **[`specs.md`](specs.md)** §2. Implementation: [`commands/use_commands.py`](../commands/use_commands.py), [`commands/wsl_db.py`](../commands/wsl_db.py). WSL resolution uses **`RuntimeIdentity`** (`args.runtime_identity`: `machine`, `user`, `wsl_name` from `WSL_DISTRO_NAME` or `default`).

---

## 0. Lifecycle and filesystem ownership

The lifecycle of a use link follows a strict state machine. Each step owns specific filesystem and DB operations. **Order is critical — incorrect order can cause irreversible data loss on the Windows host.**

| Step | Command | Filesystem | DB | Precondition |
|------|---------|------------|-----|--------------|
| 1 | `registry add` | none | insert registry | — |
| 2 | `use add` | `mkdir -p WSL_PROJECTS/rel_wsl` | insert use (`mounted=0`) | registry exists |
| 3 | `use enable` | `sudo mount --bind host wsl` | set `mounted=1` | `mounted=0` |
| 4 | `use disable` | `sudo umount wsl` | set `mounted=0` | `mounted=1` |
| 5 | `use remove` | `rmtree WSL_PROJECTS/rel_wsl` | delete use row | `mounted=0` |
| 6 | `registry remove` | none | delete registry row | no use links |

> **`disable` does not remove the directory.** The WSL mount point is preserved so `enable` can be called again. Only `use remove` deletes the directory.

> **CRITICAL — data loss prevention:** `use remove` calls `rmtree` only when `mounted=0`. If called while mounted, it would delete content on the **Windows host** irreversibly. The `mounted=1` guard must never be bypassed.

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

**Execution order (strict):**
1. Resolve `registry_uuid`. Resolve `wsl_uuid` via `resolve_wsl_uuid` with **`create_if_missing=True`**: insert **`wsls`** (`cli_command NULL`) if missing.
2. If **`uses`** already has `(wsl_uuid, registry_uuid)` → error.
3. **Create WSL directory**: `os.makedirs(WSL_PROJECTS/rel_path_wsl, exist_ok=True)` — creates all intermediate directories (`mkdir -p` semantics). This is a WSL-local directory that will serve as the mount point.
4. **`INSERT INTO uses (wsl_uuid, registry_uuid, mounted)`** with **`mounted = 0`**.

WSL target selectors are optional; if omitted, target WSL is resolved from runtime identity.

> **Data-safety rule:** the directory created here is a local WSL path only. No host (Windows) path is touched at this stage.

**Shortcuts:** `wsl4ai ua`.

Output contract:
- Always `output.result`
- No `output.data` (non-query operation)

---

## 4. `use remove`

**Execution order (strict):**
1. Resolve `wsl_uuid` (**no** auto-create) and `registry_uuid`.
2. If no **`uses`** row → error.
3. If **`mounted = 1`** → error (`use disable` first).
4. **Remove WSL directory**: `shutil.rmtree(WSL_PROJECTS/rel_path_wsl)` — removes the mount point directory created by `use add`.
5. **`DELETE`** that **`uses`** row from DB.

WSL target selectors are optional.

**Shortcuts:** `wsl4ai ur`.

Output contract:
- Always `output.result`
- No `output.data` (non-query operation)

---

## 5. `use enable`

Activates one `uses` link: bind-mounts the host path onto the existing WSL directory.

**Precondition:** `mounted = 0`. If `mounted = 1` → error (already mounted).

**Execution order (strict):**
1. Resolve `wsl_uuid` and `registry_uuid`; fetch `rel_path_host` and `rel_path_wsl` from `registries`.
2. If `mounted = 1` → error.
3. Resolve full paths from **`local.env`** (`HOST_PROJECTS` + `rel_path_host`, `WSL_PROJECTS` + `rel_path_wsl`).
4. **Mount**: `sudo mount --bind <host_path> <wsl_path>`. If mount fails → error (stop, DB unchanged).
5. **Update DB**: `UPDATE uses SET mounted = 1` — only on mount success.

> **Note:** the WSL directory must already exist (created by `use add`). `use enable` does **not** create directories.

If no `uses` row → error. Path resolution errors (missing `local.env` keys) → error.

WSL target selectors are optional.

**Shortcuts:** `wsl4ai ue`.

Output contract:
- Always `output.result`
- No `output.data` (non-query operation)

---

## 6. `use disable`

Deactivates one `uses` link: unmounts. **The WSL directory is not removed** — it is preserved as the mount point for future `enable` calls.

**Precondition:** `mounted = 1`. If `mounted = 0` → error (not mounted).

**Execution order (strict):**
1. Resolve `wsl_uuid` and `registry_uuid`; fetch `rel_path_wsl` from `registries`.
2. If `mounted = 0` → error.
3. Resolve full WSL path from **`local.env`** (`WSL_PROJECTS` + `rel_path_wsl`).
4. **Unmount**: `sudo umount <wsl_path>`. If unmount fails → error (stop, directory and DB unchanged).
5. **Update DB**: `UPDATE uses SET mounted = 0` — only on unmount success.

The WSL directory is **not removed** by `disable` — it remains as the mount point for future `enable` calls. Directory removal happens in `use remove`.

If no `uses` row → error.

WSL target selectors are optional.

**Shortcuts:** `wsl4ai ud`.

Output contract:
- Always `output.result`
- No `output.data` (non-query operation)

---

## 7. `use disableall`

Applies `use disable` logic to **all `mounted=1`** `uses` rows of the runtime WSL.

**Behavior:**
1. Resolve `wsl_uuid` from runtime identity (no WSL selector options).
2. Query **only `mounted=1`** `uses` rows for that `wsl_uuid`.
3. For each row, call `_disable_one` (umount → rmtree → update DB).
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
