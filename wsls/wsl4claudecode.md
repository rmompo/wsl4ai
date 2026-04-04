# WSL setup: Claude Code

Target: Linux / Ubuntu WSL distro.

---

## 1. Install Claude Code

Use the official native installer:

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

The native installer requires no dependencies (no Node.js or npm needed), and auto-updates Claude Code in the background.

Verify:

```bash
claude --version
```

---

## 2. Authenticate

On first run, Claude Code will open a browser window to complete authentication:

```bash
claude
```

Follow the prompts to log in with your Anthropic account.

---

## 3. Apply changes

Reload your shell if needed:

```bash
source ~/.bashrc
```

Or exit and reopen the WSL terminal.

---

## Notes

- Ubuntu 20.04+ is supported.
- The installer auto-updates Claude Code on each session.
- Run `claude doctor` for diagnostics if something does not work.
- The npm method (`npm install -g @anthropic-ai/claude-code`) is deprecated — use the native installer instead.
