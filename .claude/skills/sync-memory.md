# Sync Memory

Use this skill to commit and push the latest agent memory and tool changes to Git so teammates and other AI tools see the updates.

## When to invoke

- The user says "sync memory", "push memory", "share memory with team", or similar
- After a session where new memories were added and the user wants to persist them

## Steps

1. Run `python3 agentmem.py sync` in the project root
2. Report what was committed and whether the push succeeded
3. If `--no-push` is needed (e.g. no remote configured), run `python3 agentmem.py sync --no-push` instead

## Notes

- `sync` runs `build` first, then `git add`, `git pull --rebase`, `git commit`, and `git push`
- If there is nothing new to commit, the command exits cleanly with a message
- Merge conflicts in `.agent/memory/` files must be resolved manually before retrying
