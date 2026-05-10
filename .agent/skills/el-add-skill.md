# Add Skill

Use this skill to create a new shared agent skill that will be available across Claude Code, Cursor, and Codex.

## When to invoke

- The user says "add skill <name>", "create skill <name>", "new skill <name>", or similar

## Steps

1. Extract the skill name from the user's message (lowercase, hyphens for spaces)
2. Run `python3 elephagent.py skill add <name>` in the project root
3. Open `.agent/skills/<name>.md` and help the user fill in:
   - **When to invoke**: what phrases or situations trigger this skill
   - **Steps**: the exact actions the AI should take
   - **Notes**: edge cases or caveats
4. Run `python3 elephagent.py build` to generate platform files
5. Tell the user the skill is now available as `/<name>` in Claude Code

## Notes

- The skill name becomes the slash command in Claude Code (e.g. `my-tool` → `/my-tool`)
- Use `--force` to overwrite an existing skill: `python3 elephagent.py skill add <name> --force`
- After editing, always run `build` to keep Cursor and Codex in sync
