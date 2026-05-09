# Remember

Use this skill to save valuable information from the current conversation to shared agent memory.

## When to invoke

- The user says "help me remember", "save this", "记下来", or similar
- A decision, workflow, pitfall, or term worth preserving surfaces in conversation

## Steps

1. Identify the topic: `decisions`, `workflows`, `pitfalls`, `glossary`, or `log` (default)
2. Call MCP tool `agent_memory_append` with the note and topic
3. Run `python3 elephagent.py build` so all platform adapters are updated
4. Confirm to the user what was saved and where

## Topic guide

| Topic | When to use |
|-------|-------------|
| decisions | Architecture or tech choices |
| workflows | Repeatable processes |
| pitfalls | Mistakes to avoid |
| glossary | Project-specific terms |
| log | General observations (default) |
