# Specification: `wsl4ai use ...`

Core (non-special) commands. Align with **[`specs.md`](specs.md)** §2. Implementation: [`commands/use_commands.py`](../commands/use_commands.py), [`commands/wsl_db.py`](../commands/wsl_db.py). WSL resolution uses **`RuntimeIdentity`** (`args.runtime_identity`: `machine`, `user`, `wsl_name` from `WSL_DISTRO_NAME` or `default`).

---

## 1. Shared flags

- **Registry (required** for `add`, `remove`, `enable`, `disable`**):** exactly one of **`--registry-uuid`** or **`--registry-name`** (case-insensitive name).
- **WSL (optional):** at most one of **`--wsl-uuid`** or **`--wsl-name`**. If neither is set, the target `wsls` row is resolved by **`wsl_name` + `user`** from runtime identity (same `user` as `wsls.user`, `wsls.name` from `WSL_DISTRO_NAME` or `default`).
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
  - If neither `--wsl-uuid` nor `--wsl-name` nor `--all` is passed, list is scoped to runtime WSL (`RuntimeIdentity` -> resolved `wsl_uuid`).
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

WSL target selectors (`--wsl-uuid` / `--wsl-name`) are optional; if omitted, target WSL is resolved from runtime identity.

**Shortcuts:** `wsl4ai ua` (same flags).

Output contract:

- Always `output.result`
- No `output.data` (non-query operation)

---

## 4. `use remove`

1. Resolve `wsl_uuid` (**no** auto-create) and `registry_uuid`.
2. If no **`uses`** row → error.
3. If **`mounted = 1`** → error (`use disable` first).
4. Else **`DELETE`** that **`uses`** row.

WSL target selectors (`--wsl-uuid` / `--wsl-name`) are optional; if omitted, target WSL is resolved from runtime identity.

**Shortcuts:** `wsl4ai ur`.

Output contract:

- Always `output.result`
- No `output.data` (non-query operation)

---

## 5. `use enable` / `use disable`

Resolve the same pair as `use remove`. **`UPDATE uses SET mounted = 1`** (enable) or **`= 0`** (disable). If no row → error.

WSL target selectors (`--wsl-uuid` / `--wsl-name`) are optional; if omitted, target WSL is resolved from runtime identity.

**Shortcuts:** `wsl4ai ue`, `wsl4ai ud`.

Output contract:

- Always `output.result`
- No `output.data` (non-query operation)

---

## 6. `use disableall`

Resolve **`wsl_uuid`** only (same WSL flags as above, no registry). **`UPDATE uses SET mounted = 0 WHERE wsl_uuid = ?`**.

WSL target selectors (`--wsl-uuid` / `--wsl-name`) are optional; if omitted, target WSL is resolved from runtime identity.

**Shortcuts:** `wsl4ai uda`.

Output contract:

- Always `output.result`
- No `output.data` (non-query operation)

---

## 7. Implementation reference

- `commands/use_commands.py` — handlers and argparse.
- `commands/wsl_db.py` — `resolve_wsl_uuid`, `resolve_registry_target`, `ensure_wsls_row`.
