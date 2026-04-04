"""``wsl4ai use`` subcommands and top-level shortcuts (``ua``, ``ur``, …)."""

import os
import shutil
import subprocess
from argparse import Namespace, _SubParsersAction
from collections.abc import Callable

from commands.api_json import OptionSpec, emit_envelope, options_from_args, row_from_pairs
from commands.common import DB_PATH, connect_db, expand_path_template, load_local_env_paths, require_database_file
from commands.help_md import help_summary_for_root, parser_description_from_manual
from commands.wsl_db import resolve_registry_target, resolve_wsl_uuid


def _resolve_full_paths(rel_host: str, rel_wsl: str) -> tuple[str, str, str]:
    """Return (host_full_path, wsl_full_path, error). Error is empty string on success."""
    base_host, base_wsl = load_local_env_paths()
    if not base_host:
        return "", "", "missing HOST_PROJECTS in local.env"
    if not base_wsl:
        return "", "", "missing WSL_PROJECTS in local.env"
    host_path = os.path.normpath(os.path.join(expand_path_template(base_host), rel_host))
    wsl_path = os.path.normpath(os.path.join(expand_path_template(base_wsl), rel_wsl))
    return host_path, wsl_path, ""


def _ri(args: Namespace):
    return args.runtime_identity


def cmd_use_add(args: Namespace) -> int:
    opts = options_from_args(
        args,
        [
            OptionSpec("--registry-uuid", "use_registry_uuid"),
            OptionSpec("--registry-name", "use_registry_name"),
            OptionSpec("--wsl-uuid", "use_wsl_uuid"),
            OptionSpec("--wsl-name", "use_wsl_name"),
        ],
    )
    if not require_database_file():
        return emit_envelope(args=args, command="use", subcommand="add", options=opts, status=1, message="database file not found")
    ri = _ri(args)
    with connect_db(DB_PATH) as con:
        reg_id, err = resolve_registry_target(
            con,
            registry_uuid=getattr(args, "use_registry_uuid", "") or "",
            registry_name=getattr(args, "use_registry_name", "") or "",
        )
        if err:
            return emit_envelope(args=args, command="use", subcommand="add", options=opts, status=1, message=err)
        wsl_id, err_w = resolve_wsl_uuid(
            con,
            wsl_uuid=getattr(args, "use_wsl_uuid", "") or "",
            wsl_name=getattr(args, "use_wsl_name", "") or "",
            runtime_user=ri.user,
            runtime_wsl_name=ri.wsl_name,
            create_if_missing=True,
        )
        if err_w:
            return emit_envelope(args=args, command="use", subcommand="add", options=opts, status=1, message=err_w)
        exists = con.execute(
            "SELECT 1 FROM uses WHERE wsl_uuid = ? AND registry_uuid = ?",
            (wsl_id, reg_id),
        ).fetchone()
        if exists:
            return emit_envelope(
                args=args,
                command="use",
                subcommand="add",
                options=opts,
                status=1,
                message="use add: link already exists for this wsl and registry",
            )
        rel_wsl = con.execute(
            "SELECT rel_path_wsl FROM registries WHERE uuid = ?", (reg_id,)
        ).fetchone()
        if rel_wsl:
            _, wsl_root = load_local_env_paths()
            if wsl_root:
                wsl_full = os.path.normpath(os.path.join(expand_path_template(wsl_root), rel_wsl[0]))
                try:
                    os.makedirs(wsl_full, exist_ok=True)
                except OSError as exc:
                    return emit_envelope(
                        args=args,
                        command="use",
                        subcommand="add",
                        options=opts,
                        status=1,
                        message=f"use add: could not create wsl path {wsl_full}: {exc}",
                    )
        con.execute(
            "INSERT INTO uses (wsl_uuid, registry_uuid, mounted) VALUES (?, ?, 0)",
            (wsl_id, reg_id),
        )
    return emit_envelope(
        args=args,
        command="use",
        subcommand="add",
        options=opts,
        status=0,
        message="use add: link created",
        rows=[row_from_pairs([("wslUuid", wsl_id), ("registryUuid", reg_id), ("mounted", "0")])],
    )


def _resolve_pair(con, args: Namespace) -> tuple[str | None, str | None, str | None]:
    ri = _ri(args)
    reg_id, err = resolve_registry_target(
        con,
        registry_uuid=getattr(args, "use_registry_uuid", "") or "",
        registry_name=getattr(args, "use_registry_name", "") or "",
    )
    if err:
        return None, None, err
    wsl_id, err_w = resolve_wsl_uuid(
        con,
        wsl_uuid=getattr(args, "use_wsl_uuid", "") or "",
        wsl_name=getattr(args, "use_wsl_name", "") or "",
        runtime_user=ri.user,
        runtime_wsl_name=ri.wsl_name,
        create_if_missing=False,
    )
    if err_w:
        return None, None, err_w
    return wsl_id, reg_id, None


def cmd_use_remove(args: Namespace) -> int:
    opts = options_from_args(
        args,
        [
            OptionSpec("--registry-uuid", "use_registry_uuid"),
            OptionSpec("--registry-name", "use_registry_name"),
            OptionSpec("--wsl-uuid", "use_wsl_uuid"),
            OptionSpec("--wsl-name", "use_wsl_name"),
        ],
    )
    if not require_database_file():
        return emit_envelope(args=args, command="use", subcommand="remove", options=opts, status=1, message="database file not found")
    with connect_db(DB_PATH) as con:
        wsl_id, reg_id, err = _resolve_pair(con, args)
        if err:
            return emit_envelope(args=args, command="use", subcommand="remove", options=opts, status=1, message=err)
        row = con.execute(
            "SELECT mounted FROM uses WHERE wsl_uuid = ? AND registry_uuid = ?",
            (wsl_id, reg_id),
        ).fetchone()
        if not row:
            return emit_envelope(args=args, command="use", subcommand="remove", options=opts, status=1, message="use remove: link not found")
        if int(row[0]) != 0:
            return emit_envelope(args=args, command="use", subcommand="remove", options=opts, status=1, message="use remove: mounted=1; use disable first")
        rel_wsl = con.execute(
            "SELECT rel_path_wsl FROM registries WHERE uuid = ?", (reg_id,)
        ).fetchone()
        if rel_wsl:
            _, wsl_root = load_local_env_paths()
            if wsl_root:
                wsl_full = os.path.normpath(os.path.join(expand_path_template(wsl_root), rel_wsl[0]))
                try:
                    shutil.rmtree(wsl_full)
                except FileNotFoundError:
                    pass
                except OSError as exc:
                    return emit_envelope(args=args, command="use", subcommand="remove", options=opts, status=1, message=f"use remove: could not remove directory {wsl_full}: {exc}")
        con.execute(
            "DELETE FROM uses WHERE wsl_uuid = ? AND registry_uuid = ?",
            (wsl_id, reg_id),
        )
    return emit_envelope(
        args=args,
        command="use",
        subcommand="remove",
        options=opts,
        status=0,
        message="use remove: link removed",
        rows=[row_from_pairs([("wslUuid", wsl_id), ("registryUuid", reg_id)])],
    )


def cmd_use_enable(args: Namespace) -> int:
    opts = options_from_args(
        args,
        [
            OptionSpec("--registry-uuid", "use_registry_uuid"),
            OptionSpec("--registry-name", "use_registry_name"),
            OptionSpec("--wsl-uuid", "use_wsl_uuid"),
            OptionSpec("--wsl-name", "use_wsl_name"),
        ],
    )
    if not require_database_file():
        return emit_envelope(args=args, command="use", subcommand="enable", options=opts, status=1, message="database file not found")

    with connect_db(DB_PATH) as con:
        wsl_id, reg_id, err = _resolve_pair(con, args)
        if err:
            return emit_envelope(args=args, command="use", subcommand="enable", options=opts, status=1, message=err)
        row = con.execute(
            "SELECT u.mounted, r.rel_path_host, r.rel_path_wsl FROM uses u JOIN registries r ON r.uuid = u.registry_uuid WHERE u.wsl_uuid = ? AND u.registry_uuid = ?",
            (wsl_id, reg_id),
        ).fetchone()
        if not row:
            return emit_envelope(args=args, command="use", subcommand="enable", options=opts, status=1, message="use enable: link not found")
        if int(row[0]) == 1:
            return emit_envelope(args=args, command="use", subcommand="enable", options=opts, status=1, message="use enable: already mounted")
        _, rel_host, rel_wsl = row

    host_path, wsl_path, path_err = _resolve_full_paths(rel_host, rel_wsl)
    if path_err:
        return emit_envelope(args=args, command="use", subcommand="enable", options=opts, status=1, message=f"use enable: {path_err}")

    # mount
    try:
        subprocess.run(["sudo", "mount", "--bind", host_path, wsl_path], check=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        try:
            os.rmdir(wsl_path)
        except OSError:
            pass
        return emit_envelope(args=args, command="use", subcommand="enable", options=opts, status=1, message=f"use enable: mount failed: {exc.stderr.decode().strip() if exc.stderr else exc}")

    # 3. update DB
    with connect_db(DB_PATH) as con:
        con.execute("UPDATE uses SET mounted = 1 WHERE wsl_uuid = ? AND registry_uuid = ?", (wsl_id, reg_id))

    return emit_envelope(
        args=args,
        command="use",
        subcommand="enable",
        options=opts,
        status=0,
        message=f"use enable: mounted {wsl_path}",
        rows=[row_from_pairs([("wslUuid", wsl_id), ("registryUuid", reg_id), ("mounted", "1"), ("wslPath", wsl_path)])],
    )


def _disable_one(wsl_id: str, reg_id: str, rel_host: str, rel_wsl: str) -> tuple[bool, str]:
    """Unmount, remove folder and update DB for one use. Returns (success, message)."""
    _, wsl_path, path_err = _resolve_full_paths(rel_host, rel_wsl)
    if path_err:
        return False, f"use disable: {path_err}"

    try:
        subprocess.run(["sudo", "umount", wsl_path], check=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        return False, f"use disable: umount failed: {exc.stderr.decode().strip() if exc.stderr else exc}"

    with connect_db(DB_PATH) as con:
        con.execute("UPDATE uses SET mounted = 0 WHERE wsl_uuid = ? AND registry_uuid = ?", (wsl_id, reg_id))

    return True, f"use disable: unmounted {wsl_path}"


def cmd_use_disable(args: Namespace) -> int:
    opts = options_from_args(
        args,
        [
            OptionSpec("--registry-uuid", "use_registry_uuid"),
            OptionSpec("--registry-name", "use_registry_name"),
            OptionSpec("--wsl-uuid", "use_wsl_uuid"),
            OptionSpec("--wsl-name", "use_wsl_name"),
        ],
    )
    if not require_database_file():
        return emit_envelope(args=args, command="use", subcommand="disable", options=opts, status=1, message="database file not found")

    with connect_db(DB_PATH) as con:
        wsl_id, reg_id, err = _resolve_pair(con, args)
        if err:
            return emit_envelope(args=args, command="use", subcommand="disable", options=opts, status=1, message=err)
        row = con.execute(
            "SELECT u.mounted, r.rel_path_host, r.rel_path_wsl FROM uses u JOIN registries r ON r.uuid = u.registry_uuid WHERE u.wsl_uuid = ? AND u.registry_uuid = ?",
            (wsl_id, reg_id),
        ).fetchone()
        if not row:
            return emit_envelope(args=args, command="use", subcommand="disable", options=opts, status=1, message="use disable: link not found")
        if int(row[0]) == 0:
            return emit_envelope(args=args, command="use", subcommand="disable", options=opts, status=1, message="use disable: not mounted")
        _, rel_host, rel_wsl = row

    ok, msg = _disable_one(wsl_id, reg_id, rel_host, rel_wsl)
    if not ok:
        return emit_envelope(args=args, command="use", subcommand="disable", options=opts, status=1, message=msg)
    return emit_envelope(
        args=args,
        command="use",
        subcommand="disable",
        options=opts,
        status=0,
        message=msg,
        rows=[row_from_pairs([("wslUuid", wsl_id), ("registryUuid", reg_id), ("mounted", "0")])],
    )


def cmd_use_disableall(args: Namespace) -> int:
    opts = options_from_args(args, [OptionSpec("--quiet", "quiet", is_flag=True)])
    quiet = bool(getattr(args, "quiet", False))
    if not require_database_file():
        if not quiet:
            return emit_envelope(args=args, command="use", subcommand="disableall", options=opts, status=1, message="database file not found")
        return 1
    ri = _ri(args)
    with connect_db(DB_PATH) as con:
        wsl_id, err_w = resolve_wsl_uuid(
            con,
            wsl_uuid="",
            wsl_name="",
            runtime_user=ri.user,
            runtime_wsl_name=ri.wsl_name,
            create_if_missing=False,
        )
        if err_w:
            if not quiet:
                return emit_envelope(args=args, command="use", subcommand="disableall", options=opts, status=1, message=err_w)
            return 1
        mounted_uses = con.execute(
            """
            SELECT u.registry_uuid, r.rel_path_host, r.rel_path_wsl
            FROM uses u
            JOIN registries r ON r.uuid = u.registry_uuid
            WHERE u.wsl_uuid = ? AND u.mounted = 1
            """,
            (wsl_id,),
        ).fetchall()

    errors = []
    disabled = []
    for reg_id, rel_host, rel_wsl in mounted_uses:
        ok, msg = _disable_one(wsl_id, reg_id, rel_host, rel_wsl)
        if ok:
            disabled.append(row_from_pairs([("wslUuid", wsl_id), ("registryUuid", reg_id), ("mounted", "0")]))
        else:
            errors.append(msg)

    if quiet:
        return 1 if errors else 0

    if errors:
        return emit_envelope(
            args=args,
            command="use",
            subcommand="disableall",
            options=opts,
            status=1,
            message=f"use disableall: {len(disabled)} disabled, {len(errors)} failed: {'; '.join(errors)}",
            rows=disabled,
        )
    return emit_envelope(
        args=args,
        command="use",
        subcommand="disableall",
        options=opts,
        status=0,
        message=f"use disableall: {len(disabled)} use(s) disabled",
        rows=disabled,
    )


def cmd_use_list(args: Namespace) -> int:
    """List all usage links between wsls and registries."""
    opts = options_from_args(
        args,
        [
            OptionSpec("--all", "use_all", is_flag=True),
            OptionSpec("--wsl-uuid", "use_wsl_uuid"),
            OptionSpec("--wsl-name", "use_wsl_name"),
        ],
    )
    use_all = bool(getattr(args, "use_all", False))
    use_wsl_uuid = (getattr(args, "use_wsl_uuid", "") or "").strip()
    use_wsl_name = (getattr(args, "use_wsl_name", "") or "").strip()
    if use_all and (use_wsl_uuid or use_wsl_name):
        return emit_envelope(
            args=args,
            command="use",
            subcommand="list",
            options=opts,
            status=1,
            message="use list: --all cannot be combined with --wsl-uuid/--wsl-name",
        )
    if not require_database_file():
        return emit_envelope(args=args, command="use", subcommand="list", options=opts, status=1, message="database file not found")
    with connect_db(DB_PATH) as con:
        where_sql = ""
        params: tuple[str, ...] = ()
        if not use_all:
            ri = _ri(args)
            wsl_id, err_w = resolve_wsl_uuid(
                con,
                wsl_uuid=use_wsl_uuid,
                wsl_name=use_wsl_name,
                runtime_user=ri.user,
                runtime_wsl_name=ri.wsl_name,
                create_if_missing=False,
            )
            if err_w:
                return emit_envelope(args=args, command="use", subcommand="list", options=opts, status=1, message=err_w)
            where_sql = "WHERE u.wsl_uuid = ?"
            params = (wsl_id,)
        rows = con.execute(
            f"""
            SELECT u.wsl_uuid,
                   w.name,
                   w.user,
                   u.registry_uuid,
                   r.name,
                   u.mounted
            FROM uses u
            JOIN wsls w ON w.uuid = u.wsl_uuid
            JOIN registries r ON r.uuid = u.registry_uuid
            {where_sql}
            ORDER BY w.name COLLATE NOCASE,
                     w.user COLLATE NOCASE,
                     r.name COLLATE NOCASE
            """,
            params,
        ).fetchall()
        if not rows:
            return emit_envelope(args=args, command="use", subcommand="list", options=opts, status=0, message="no usage links found", rows=[])
        out_rows: list[dict[str, list[dict[str, str]]]] = []
        for w_uuid, w_name, w_user, reg_uuid, reg_name, mounted in rows:
            out_rows.append(
                row_from_pairs(
                    [
                        ("wslUuid", w_uuid),
                        ("wslName", w_name),
                        ("wslUser", w_user),
                        ("registryUuid", reg_uuid),
                        ("registryName", reg_name),
                        ("mounted", str(int(mounted))),
                    ]
                )
            )
    return emit_envelope(
        args=args,
        command="use",
        subcommand="list",
        options=opts,
        status=0,
        message=f"listed {len(out_rows)} usage link(s)",
        rows=out_rows,
    )


def _add_registry_pair(p) -> None:
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument(
        "-ru",
        "--registry-uuid",
        dest="use_registry_uuid",
        default="",
        metavar="UUID",
        help="Mount definition UUID",
    )
    g.add_argument(
        "-rn",
        "--registry-name",
        dest="use_registry_name",
        default="",
        help="Mount definition name",
    )


def _add_wsl_triple(p) -> None:
    g = p.add_mutually_exclusive_group(required=False)
    g.add_argument(
        "-wu",
        "--wsl-uuid",
        dest="use_wsl_uuid",
        default="",
        metavar="UUID",
        help="WSL UUID (optional; omit to use runtime WSL)",
    )
    g.add_argument(
        "-wn",
        "--wsl-name",
        dest="use_wsl_name",
        default="",
        help="WSL name (omit to use the current workspace)",
    )


def _add_wsl_only(p) -> None:
    g = p.add_mutually_exclusive_group(required=False)
    g.add_argument(
        "-wu",
        "--wsl-uuid",
        dest="use_wsl_uuid",
        default="",
        metavar="UUID",
        help="WSL row UUID (optional; default is runtime WSL)",
    )
    g.add_argument(
        "-wn",
        "--wsl-name",
        dest="use_wsl_name",
        default="",
        help="WSL name (default: runtime WSL)",
    )


def register_use_command(subparsers: _SubParsersAction) -> None:
    """Register ``use`` with real subcommand handlers."""
    use_fb = "Connect WSL workspaces with mount definitions or break those ties."
    use_desc = parser_description_from_manual("use", use_fb)
    help_line = help_summary_for_root("use", "Link WSLs to mount definitions")
    use = subparsers.add_parser(
        "use",
        help=help_line,
        description=use_desc,
    )
    use_sub = use.add_subparsers(
        dest="use_command",
        required=True,
        metavar="SUBCOMMAND",
        help="list | add|ua | remove|ur | enable|ue | disable|ud | disableall|uda",
    )

    list_help = "Show usage links (runtime WSL by default, use --all for every WSL)"
    lst = use_sub.add_parser("list", aliases=["ul"], help=list_help, description=list_help)
    _add_wsl_only(lst)
    lst.add_argument(
        "-a",
        "--all",
        dest="use_all",
        action="store_true",
        help="List links for all WSLs (ignore runtime/default WSL filter)",
    )
    lst.set_defaults(func=cmd_use_list)

    add_help = "Record that a WSL workspace should use a mount definition"
    add = use_sub.add_parser(
        "add",
        aliases=["ua"],
        help=add_help,
        description=add_help,
    )
    _add_registry_pair(add)
    _add_wsl_triple(add)
    add.set_defaults(func=cmd_use_add)

    for name, aliases, h, fn in (
        ("remove", ("ur",), "Stop a WSL from using a mount definition", cmd_use_remove),
        ("enable", ("ue",), "Turn this attachment on again", cmd_use_enable),
        ("disable", ("ud",), "Turn this attachment off for now", cmd_use_disable),
    ):
        p = use_sub.add_parser(name, aliases=list(aliases), help=h, description=h)
        _add_registry_pair(p)
        _add_wsl_triple(p)
        p.set_defaults(func=fn)

    da_help = "Turn off every mount attachment for this WSL"
    da = use_sub.add_parser("disableall", aliases=["uda"], help=da_help, description=da_help)
    _add_wsl_only(da)
    da.add_argument("-q", "--quiet", dest="quiet", action="store_true", help="Suppress all output")
    da.set_defaults(func=cmd_use_disableall)


def register_use_root_shortcuts(subparsers: _SubParsersAction) -> None:
    """Top-level shortcuts for `use` subcommands."""
    mapping: tuple[tuple[str, str, Callable[..., int]], ...] = (
        ("ul", "use list", cmd_use_list),
        ("ua", "use add", cmd_use_add),
        ("ur", "use remove", cmd_use_remove),
        ("ue", "use enable", cmd_use_enable),
        ("ud", "use disable", cmd_use_disable),
        ("uda", "use disableall", cmd_use_disableall),
    )
    for short, full, fn in mapping:
        sh = f"Shorthand for {full}"
        p = subparsers.add_parser(short, help=sh, description=sh)
        if short == "ul":
            _add_wsl_only(p)
            p.add_argument(
                "-a",
                "--all",
                dest="use_all",
                action="store_true",
                help="List links for all WSLs (ignore runtime/default WSL filter)",
            )
        elif short == "uda":
            _add_wsl_only(p)
            p.add_argument("-q", "--quiet", dest="quiet", action="store_true", help="Suppress all output")
        else:
            _add_registry_pair(p)
            _add_wsl_triple(p)
        p.set_defaults(func=fn)
