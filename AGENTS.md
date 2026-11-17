## LibreOffice: never run inside the sandbox

On this macOS host, LibreOffice crashes when launched inside the sandbox. Run every command
that can invoke LibreOffice outside the sandbox (`sandbox_permissions="require_escalated"`),
using the provided repository scripts. This includes PDF builds/exports and conversion tests.

## Temporary files

Use `_temp/` at the repository root for temporary scripts, renders, and review artifacts.

## Repository guidance

- [docs/REPO_STYLE.md](docs/REPO_STYLE.md) is the master repository guidance.
- docs/PYTHON_STYLE.md
- docs/MARKDOWN_STYLE.md
- docs/PYTEST_STYLE.md
- docs/DEVELOPMENT.md
- docs/INSTALL.md
- docs/USAGE.md
- docs/CHANGELOG.md
- docs/HUMAN_GUIDANCE.md
- docs/DESIGN_DECISIONS.md

## Python Environment
AI agents (Codex/Claude) must run Python using `source source_me.sh && python3` (use Python 3.12 only).
On this user's macOS (Homebrew Python 3.12), Python modules are installed to `/opt/homebrew/lib/python3.12/site-packages/`.
