"""PowerShell alias installation helpers for WSL4AI."""

from argparse import Namespace
from pathlib import Path
import subprocess
import sys

PS_BEGIN = "# >>> WSL4AI BEGIN >>>"
PS_END = "# <<< WSL4AI END <<<"


def profile_paths() -> list[Path]:
    """Return PowerShell profile paths for the current OS user.

    Returns:
        list[Path]: Unique ordered profile targets. Detection strategy:
            1) Query `$PROFILE` and `MyDocuments` from `powershell` and `pwsh`.
            2) Build profile paths under current-user documents root.
            3) Fallback to `%USERPROFILE%\\Documents` conventions.
    """
    candidates: list[Path] = []
    for shell_exe in ("powershell", "pwsh"):
        try:
            result = subprocess.run(
                [
                    shell_exe,
                    "-NoProfile",
                    "-Command",
                    "$PROFILE; [Environment]::GetFolderPath('MyDocuments')",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            if lines:
                # First line should be $PROFILE from that shell executable.
                candidates.append(Path(lines[0]))
            if len(lines) > 1:
                docs_root = Path(lines[1])
                if shell_exe == "powershell":
                    candidates.append(docs_root / "WindowsPowerShell" / "Microsoft.PowerShell_profile.ps1")
                else:
                    candidates.append(docs_root / "PowerShell" / "Microsoft.PowerShell_profile.ps1")
        except Exception:
            # Ignore detection failures and continue with remaining strategies.
            pass

    candidates.extend(
        [
            Path.home() / "Documents" / "WindowsPowerShell" / "Microsoft.PowerShell_profile.ps1",
            Path.home() / "Documents" / "PowerShell" / "Microsoft.PowerShell_profile.ps1",
            Path.home() / "OneDrive - GFI" / "Documentos" / "WindowsPowerShell" / "Microsoft.PowerShell_profile.ps1",
            Path.home() / "OneDrive - GFI" / "Documentos" / "PowerShell" / "Microsoft.PowerShell_profile.ps1",
        ]
    )

    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path).lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def wsl4ai_block() -> str:
    """Build the WSL4AI function block written into PowerShell profiles.

    Returns:
        str: Text block bounded by WSL4AI markers. The function forwards all
            arguments (`@args`) to `wsl4ai.py` using the current Python runtime.
    """
    script_path = str((Path(__file__).resolve().parent.parent / "wsl4ai.py"))
    python_exe = sys.executable
    return (
        f"{PS_BEGIN}\n"
        f"function wsl4ai {{\n"
        f"    & \"{python_exe}\" \"{script_path}\" @args\n"
        f"}}\n"
        f"{PS_END}\n"
    )


def upsert_block(content: str, block: str) -> tuple[str, bool]:
    """Insert or replace the WSL4AI profile block.

    Args:
        content (str): Existing profile content (can be empty).
        block (str): New block text that includes WSL4AI begin/end markers.

    Returns:
        tuple[str, bool]:
            - Updated full profile content.
            - `True` if a new block was inserted, `False` if an existing block
              was replaced.
    """
    begin_idx = content.find(PS_BEGIN)
    end_idx = content.find(PS_END)

    if begin_idx != -1 and end_idx != -1 and end_idx > begin_idx:
        end_idx += len(PS_END)
        updated = (content[:begin_idx].rstrip() + "\n\n" + block + content[end_idx:].lstrip())
        return updated, False

    suffix = "" if content.endswith(("\n", "\r")) or not content else "\n\n"
    return content + suffix + block, True


def cmd_alias_ps(_: Namespace) -> int:
    """Install or overwrite WSL4AI PowerShell aliases in supported profiles.

    Args:
        _ (Namespace): Parsed CLI namespace. No command-specific values are
            consumed.

    Returns:
        int: Exit code. `0` on success.
    """
    block = wsl4ai_block()
    for profile in profile_paths():
        profile.parent.mkdir(parents=True, exist_ok=True)
        existing = profile.read_text(encoding="utf-8") if profile.exists() else ""
        updated, created = upsert_block(existing, block)
        profile.write_text(updated, encoding="utf-8")
        state = "installed" if created else "updated"
        print(f"PowerShell profile {state}: {profile}")
    print("Restart terminal or run: . $PROFILE")
    return 0
