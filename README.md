# Agent Kit

Agent Kit is a repo-local compatibility layer for AI coding agents. It keeps shared memory, project instructions, and MCP tool definitions in one Git-synced `.agent/` directory, then renders the files that Codex, Claude Code, and Cursor already know how to read.

The goal is simple: your project memory and tools should belong to the repository, not to one AI platform.

## Why

AI coding tools are useful, but each one stores project context differently:

- Codex reads `AGENTS.md` and can use project-scoped MCP config.
- Claude Code reads `CLAUDE.md` and supports project-scoped `.mcp.json`.
- Cursor reads `.cursor/rules/*.mdc`, `AGENTS.md`, and `.cursor/mcp.json`.

Agent Kit gives you one source of truth:

```text
.agent/
  memory/
    index.md
    decisions.md
    workflows.md
    pitfalls.md
    glossary.md
  tools/
    registry.json
    mcp_server.py
```

From that source, it generates:

```text
AGENTS.md
CLAUDE.md
.cursor/rules/agent-memory.mdc
.mcp.json
.cursor/mcp.json
.codex/config.toml
```

## Features

- Git-synced project memory that works across machines.
- Generated adapters for Codex, Claude Code, and Cursor.
- Local MCP server for reading, searching, and appending repository memory.
- Shared MCP registry that renders per-client config files.
- No runtime dependencies beyond Python 3.
- Secret-safe defaults: local-only files and env-based token references.

## Quick Start

Create the layout:

```bash
python3 agent_kit.py init
```

Add a durable memory note:

```bash
python3 agent_kit.py remember "This repo uses pnpm and requires Redis for API tests."
```

Regenerate platform adapter files:

```bash
python3 agent_kit.py build
```

Check the setup:

```bash
python3 agent_kit.py doctor
```

## Commands

```bash
python3 agent_kit.py init
```

Creates `.agent/`, default memory files, MCP registry, and generated platform adapters.

```bash
python3 agent_kit.py remember "..."
```

Appends a note to `.agent/memory/log/YYYY-MM-DD.md`, updates the memory index, and rebuilds generated files.

```bash
python3 agent_kit.py build
```

Renders all platform-specific files from `.agent/`.

```bash
python3 agent_kit.py tool list
```

Lists MCP servers in `.agent/tools/registry.json`.

```bash
python3 agent_kit.py tool add context7 --command npx --arg -y --arg @upstash/context7-mcp
```

Adds a stdio MCP server and regenerates client config.

```bash
python3 agent_kit.py tool add figma --url https://mcp.figma.com/mcp --bearer-token-env-var FIGMA_OAUTH_TOKEN
```

Adds an HTTP MCP server that reads its bearer token from an environment variable.

```bash
python3 agent_kit.py sync -m "Sync agent memory"
```

Runs `build`, pulls with rebase, commits shared agent files, and pushes.

## MCP Tools

Agent Kit includes a small MCP server at `.agent/tools/mcp_server.py`.

It exposes:

- `agent_memory_read`: read one memory file or all memory.
- `agent_memory_search`: search shared memory.
- `agent_memory_append`: append a durable memory note.
- `agent_tool_registry`: read the shared MCP registry.

Supported MCP resource URIs look like:

```text
agent-memory://.agent/memory/index.md
```

## Git Sync

Initialize a repository and push to GitHub:

```bash
git init
git add .
git commit -m "Initial Agent Kit project"
git branch -M main
git remote add origin https://github.com/YOUR_USER/agent-kit.git
git push -u origin main
```

After that, use:

```bash
python3 agent_kit.py sync -m "Sync agent memory"
```

## Security

Do not commit secrets into `.agent/`.

Use environment variable references instead:

```bash
python3 agent_kit.py tool add internal-api \
  --url https://example.com/mcp \
  --bearer-token-env-var INTERNAL_API_TOKEN
```

`.agent/.gitignore` excludes local scratch data and secret-looking files by default.

## Project Status

This is an early MVP. The current implementation is intentionally small and file-based so it is easy to inspect, fork, and adapt.

Planned improvements:

- More robust MCP protocol coverage.
- Importers for existing Claude/Cursor/Codex project memories.
- Conflict-friendly memory compaction.
- Release packaging for `pipx` or Homebrew.
- Optional GitHub Action to validate generated files.

## Contributing

Issues and pull requests are welcome. Before submitting changes, run:

```bash
python3 agent_kit.py build
python3 agent_kit.py doctor
python3 - <<'PY'
from pathlib import Path
for path in ["agent_kit.py", ".agent/tools/mcp_server.py"]:
    compile(Path(path).read_text(), path, "exec")
    print(path, "ok")
PY
```

## License

MIT License
