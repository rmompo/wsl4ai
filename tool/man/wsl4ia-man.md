# WSL4AI command reference

CLI reference only: what each subcommand does, flags, and examples. For installation and environment setup, see **`wsl4ia-setup.md`**.

Use `wsl4ai <command> --help` for argparse details.

---

## Runtime fields (automatic)

Handlers receive **`machine`**, **`user`**, and **`runtime_identity`** (includes **`wsl_name`** for WSL resolution) on `args`; they are **not** CLI flags. Semantics are documented in **`wsl4ia-setup.md`** and **`specs/tool/specs.md`** §1.6.

## Path bases (automatic)

`HOST_PROJECTS` and `WSL_PROJECTS` are read at runtime from **`local.env`** beside `wsl4ai.py` via `load_local_env_paths()`. They are used to resolve absolute paths for registry and use operations. No database `parameters` table is involved.

## Command shortcuts

Same behavior as the long form; see **`specs/tool/specs.md`** §4.

| Long | Under `registry` / `use` | Top-level |
| ----- | ------------------------ | --------- |
| `registry list` | `registry rl` | `wsl4ai rl` |
| `registry add` | `registry ra` | `wsl4ai ra` |
| `registry remove` | `registry rr` | `wsl4ai rr` |
| `use add` | `use ua` | `wsl4ai ua` |
| `use list` | `use ul` | `wsl4ai ul` |
| `use remove` | `use ur` | `wsl4ai ur` |
| `use enable` | `use ue` | `wsl4ai ue` |
| `use disable` | `use ud` | `wsl4ai ud` |
| `use disableall` | `use uda` | `wsl4ai uda` |
| `wsl list` | `wsl wl` | `wsl4ai wl` |
| `wsl set` | — | `wsl4ai ws` |
| `whoami` | — | `wsl4ai wai` |
| `install tool` | — | `wsl4ai it` |
| `install database` | — | `wsl4ai id` |
| `install alias` | — | `wsl4ai ia` |

---

## 1. Commands

### 1.a `whoami`

Prints the runtime **`machine`** and **`user`** strings. **No database required.**

```bash
wsl4ai whoami
```

Example output (shape only):

```text
machine: dcbb4f2e3e5f4a1b9c8d7e6f5a4b3c2d
user: alice
```

### 1.b `registry list`

Lists all **registries** with fully resolved paths (`HOST_PROJECTS + rel_path_host`, `WSL_PROJECTS + rel_path_wsl` from `local.env`) and linked `uses` + `wsls` information. On a TTY the registry title uses **red** background when linked (busy) and **green** when free.

```bash
wsl4ai registry list
```

### 1.c `registry add`

Inserts one row into **`registries`**. By default, both resolved paths must exist on disk. With **`--force`**, existence checks are skipped.

| Flag | Meaning |
| ---- | ------- |
| `--name` | Logical name; **unique case-insensitively**. Required. |
| `--host` | Path segment joined under `HOST_PROJECTS`. Required. |
| `--wsl` | Path segment joined under `WSL_PROJECTS`. Required. |
| `--force` | Skip path existence checks. Optional. |

```bash
wsl4ai registry add --name myproj --host projects/foo --wsl work/foo
wsl4ai registry add --name myproj --host projects/foo --wsl work/foo --force
```

### 1.d `registry remove`

Deletes one row from **`registries`** only if there are **no** `uses` rows for it. At least one of `--uuid` or `--name` required.

| Flag | Meaning |
| ---- | ------- |
| `--uuid` | Registry UUID. |
| `--name` | Logical name (case-insensitive). |

```bash
wsl4ai registry remove --name myproj
wsl4ai registry remove --uuid 550e8400-e29b-41d4-a716-446655440000
```

### 1.e `use`

Router for usage links between **`wsls`** and **`registries`**.

#### `use list`

Lists usage links. Default scope: runtime WSL. Optional `-a/--all` for global listing.

```bash
wsl4ai use list
wsl4ai use list -a
wsl4ai ul
```

#### `use add`

Creates a `uses` link (`mounted=0`). Creates `wsls` row if missing.

```bash
wsl4ai use add --registry-name myproj
wsl4ai ua --registry-name myproj
```

#### `use remove`

Removes a `uses` link. Requires `mounted=0` (run `use disable` first).

```bash
wsl4ai use remove --registry-name myproj
wsl4ai ur --registry-name myproj
```

#### `use enable`

**Order (strict):** creates WSL directory → bind-mounts host path → sets `mounted=1`.

Paths resolved from `local.env`: `HOST_PROJECTS + rel_path_host` and `WSL_PROJECTS + rel_path_wsl`.

```bash
wsl4ai use enable --registry-name myproj
wsl4ai ue --registry-name myproj
```

#### `use disable`

**Order (strict):** unmounts (`sudo umount`) → removes WSL directory → sets `mounted=0`.

```bash
wsl4ai use disable --registry-name myproj
wsl4ai ud --registry-name myproj
```

#### `use disableall`

Applies `use disable` logic to **all** `uses` of the runtime WSL, regardless of `mounted` state. Called automatically on session start with `--quiet`.

| Flag | Meaning |
| ---- | ------- |
| `-q` / `--quiet` | Suppress all output; return exit code only. |

```bash
wsl4ai use disableall
wsl4ai use disableall --quiet
wsl4ai uda
```

### 1.f `wsl list` / `wsl set`

- **`wsl list`**: show tracked `wsls` rows and their `cli_command`.
- **`wsl set`**: update `wsls.cli_command` for an existing WSL row (`--cli` required).

```bash
wsl4ai wsl list
wsl4ai wl
wsl4ai wsl set --cli "echo ok"
wsl4ai ws --cli "echo ok"
```

### 1.g `start`

Runs one concrete mounted `use` in the current terminal session.

- Selector required: `--registry-uuid` or `--registry-name`.
- Optional: `--wsl-uuid` / `--wsl-name` (default: runtime WSL).
- Security gate: only runs when `mounted=1`.
- Working directory: `WSL_PROJECTS + rel_path_wsl` (from `local.env`).
- Executes `wsls.cli_command` in foreground.

```bash
wsl4ai start --registry-name myproj
wsl4ai start --registry-uuid 550e8400-e29b-41d4-a716-446655440000 --wsl-name Ubuntu
```

### 1.h `tui`

Interactive text user interface. Runtime-local only; no global scope actions.

```bash
wsl4ai tui
```

---

## 2. Special commands (`install`)

### 2.a `install tool`

Verify tool layout. No options.

```bash
wsl4ai install tool
wsl4ai it
```

### 2.b `install database`

Create the SQLite database. With `-f/--force`, recreate (destructive).

```bash
wsl4ai install database
wsl4ai install database --force
wsl4ai id
```

### 2.c `install alias`

Add/remove aliases in shell profiles.

| Option | Meaning |
| ------ | ------- |
| `-a` / `--action` | `add` or `remove` |
| `-t` / `--type` | `ps` or `bash` |
| `-n` / `--name` | Alias name (repeatable) |

```bash
wsl4ai install alias -a add -t bash -n wsl4ai
wsl4ai ia -a remove -t ps -n wsl4ai
```
