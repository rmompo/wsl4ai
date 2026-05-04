"""Shared constants and DB helpers for WSL4AI commands."""

from dataclasses import dataclass
from pathlib import Path
import getpass
import os
import platform
import re
import sqlite3
import sys

APP_DIR = Path(__file__).resolve().parent.parent
CONF_DIR = APP_DIR.parent / "conf"
MAN_DIR = APP_DIR / "man"


def _resolve_ddbb_dir() -> Path:
    """Return DDBB directory from WSL_DDBB in local.env; fallback to file-relative path."""
    env_file = CONF_DIR / "local.env"
    if env_file.is_file():
        try:
            for raw in env_file.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                if key.strip() == "WSL_DDBB":
                    p = val.strip().rstrip("/")
                    if p:
                        return Path(p)
        except OSError:
            pass
    return CONF_DIR / "ddbb"


DDBB_DIR = _resolve_ddbb_dir()
DB_PATH = DDBB_DIR / "wsl4ai.db"


def load_local_env_paths() -> tuple[str, str]:
    """Return ``(base_path_host, base_path_wsl)`` read directly from ``local.env`` beside ``wsl4ai.py``.

    Reads ``HOST_PROJECTS`` and ``WSL_PROJECTS``; converts Windows paths (``C:/...``) to ``/mnt/...``.
    Returns empty strings if the file is missing or keys are absent.
    """
    env_file = APP_DIR.parent / "conf" / "local.env"
    env: dict[str, str] = {}
    if env_file.is_file():
        try:
            for raw in env_file.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                env[key.strip()] = val.strip()
        except OSError:
            pass

    def _ensure_slash(p: str) -> str:
        return p if p.endswith("/") else p + "/"

    def _win_to_mnt(p: str) -> str:
        p = p.replace("\\", "/").rstrip("/")
        m = re.match(r"^([A-Za-z]):/(.*)$", p)
        if not m:
            return _ensure_slash(p)
        rest = m.group(2).strip("/")
        base = f"/mnt/{m.group(1).lower()}"
        return f"{base}/{rest}/" if rest else f"{base}/"

    host_raw = env.get("HOST_PROJECTS", "").strip()
    wsl_raw = env.get("WSL_PROJECTS", "").strip()

    if host_raw:
        if len(host_raw) >= 2 and host_raw[1] == ":":
            base_host = _win_to_mnt(host_raw)
        else:
            base_host = _ensure_slash(host_raw)
    else:
        base_host = ""

    base_wsl = _ensure_slash(wsl_raw) if wsl_raw else ""

    return base_host, base_wsl


def expand_path_template(value: str) -> str:
    """Expand path templates: ``$HOME`` / ``${HOME}``, ``%VAR%`` (Windows), ``~``.

    POSIX configs often use ``$HOME``; :func:`os.path.expandvars` on Windows only expands ``%NAME%``.
    Replacing ``$HOME`` with ``HOME`` or ``USERPROFILE`` lets the CLI run on the Windows host while
    still resolving WSL-style ``parameters`` rows.
    """
    s = (value or "").strip()
    if not s:
        return s
    home = (os.environ.get("HOME") or os.environ.get("USERPROFILE") or "").strip()
    if home:
        s = s.replace("${HOME}", home)
        s = s.replace("$HOME", home)
    s = os.path.expandvars(s)
    s = os.path.expanduser(s)
    return s


def require_database_file() -> bool:
    """Return True if ``DB_PATH`` exists; otherwise print an error to stderr and return False."""
    if DB_PATH.is_file():
        return True
    print(
        "No database file; run: wsl4ai install database",
        file=sys.stderr,
    )
    return False


_MACHINE_ID_FILES = (
    Path("/etc/machine-id"),
    Path("/var/lib/dbus/machine-id"),
)


def _read_machine_id_from_files() -> str:
    """Return first non-empty line from standard Linux machine-id files.

    Each WSL instance has its own root filesystem, so this value is stable
    and unique even when ``WSL_DISTRO_NAME`` is the same for two registrations.

    Returns:
        str: Lowercase hex identifier, or empty string if unreadable / missing.
    """
    for path in _MACHINE_ID_FILES:
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="ascii", errors="ignore")
        except OSError:
            continue
        for line in text.splitlines():
            token = line.strip()
            if token:
                return token.lower()
    return ""


def _resolve_machine_fallback() -> str:
    """Last-resort machine key when no machine-id file exists (e.g. Windows host)."""
    wsl_distro = (os.environ.get("WSL_DISTRO_NAME") or "").strip()
    node = (platform.node() or "").strip()
    if wsl_distro and node:
        return f"wsl:{wsl_distro.lower()}:{node.lower()}"
    if wsl_distro:
        return f"wsl:{wsl_distro.lower()}"
    pc = (os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME") or "").strip()
    if pc:
        return f"win:{pc.strip().lower()}"
    if node:
        return node.lower()
    return "unknown"


def resolve_machine_identifier() -> str:
    """Stable, unique-ish machine key for this runtime environment.

    Prefer Linux ``/etc/machine-id`` inside WSL (unique per instance); falls
    back to composites on Windows or minimal images.

    Returns:
        str: Non-empty machine identifier string.
    """
    mid = _read_machine_id_from_files()
    if mid:
        return mid
    return _resolve_machine_fallback()


def resolve_runtime_context() -> tuple[str, str]:
    """Detect machine id and user for the running process.

    Returns:
        tuple[str, str]: ``(machine, user)``.
    """
    ri = resolve_runtime_identity()
    return ri.machine, ri.user


DEFAULT_WSL_NAME = "default"


@dataclass(frozen=True)
class RuntimeIdentity:
    """Runtime identity for CLI handlers: machine, OS user, and WSL distro label for ``wsls.name``."""

    machine: str
    user: str
    wsl_name: str


def resolve_runtime_identity() -> RuntimeIdentity:
    """Resolve machine, login user, and WSL distro name (for ``wsls`` when not passed explicitly)."""
    machine = resolve_machine_identifier()
    user = getpass.getuser()
    wsl_name = (os.environ.get("WSL_DISTRO_NAME") or "").strip() or DEFAULT_WSL_NAME
    return RuntimeIdentity(machine=machine, user=user, wsl_name=wsl_name)


# Column bodies for ``wsls`` / ``uses`` (shared by ``TABLE_DDL``).
WSLS_TABLE_BODY = """  uuid TEXT NOT NULL PRIMARY KEY,
  name TEXT NOT NULL,
  user TEXT NOT NULL,
  cli_command TEXT,
  UNIQUE(name, user)"""

USES_TABLE_BODY = """  wsl_uuid TEXT NOT NULL,
  registry_uuid TEXT NOT NULL,
  mounted INTEGER NOT NULL DEFAULT 0 CHECK (mounted IN (0,1)),
  last_error TEXT,
  PRIMARY KEY (wsl_uuid, registry_uuid),
  FOREIGN KEY (wsl_uuid) REFERENCES wsls(uuid) ON DELETE RESTRICT ON UPDATE RESTRICT,
  FOREIGN KEY (registry_uuid) REFERENCES registries(uuid) ON DELETE RESTRICT ON UPDATE RESTRICT"""


def _sql_create_wsls(*, if_not_exists: bool) -> str:
    prefix = "CREATE TABLE IF NOT EXISTS wsls" if if_not_exists else "CREATE TABLE wsls"
    return f"{prefix} (\n{WSLS_TABLE_BODY}\n)"


def _sql_create_uses(*, if_not_exists: bool) -> str:
    prefix = "CREATE TABLE IF NOT EXISTS uses" if if_not_exists else "CREATE TABLE uses"
    return f"{prefix} (\n{USES_TABLE_BODY}\n)"


TABLE_DDL = f"""
CREATE TABLE IF NOT EXISTS registries (
  uuid TEXT NOT NULL PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  rel_path_host TEXT NOT NULL,
  rel_path_wsl TEXT NOT NULL
);

{_sql_create_wsls(if_not_exists=True)};

{_sql_create_uses(if_not_exists=True)};

CREATE INDEX IF NOT EXISTS idx_uses_registry
  ON uses(registry_uuid);
CREATE INDEX IF NOT EXISTS idx_uses_wsl
  ON uses(wsl_uuid);
"""


def connect_db(db_path: Path) -> sqlite3.Connection:
    """Open a SQLite connection configured for WSL4AI usage.

    Uses DELETE journal mode (not WAL) for compatibility with shared v9fs mounts
    (Windows-backed filesystems accessed from multiple WSL machines).  WAL requires
    a working ``-shm`` shared-memory file which v9fs does not support reliably.

    Args:
        db_path (Path): Absolute or relative path to the SQLite database file.
            Parent directories are created if missing.

    Returns:
        sqlite3.Connection: Open connection with PRAGMAs applied:
            - journal_mode=DELETE
            - synchronous=NORMAL
            - ``foreign_keys=ON``
            - busy_timeout=5000
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path), timeout=5.0)
    con.execute("PRAGMA journal_mode=DELETE;")
    con.execute("PRAGMA synchronous=NORMAL;")
    con.execute("PRAGMA foreign_keys=ON;")
    con.execute("PRAGMA busy_timeout=5000;")
    return con
