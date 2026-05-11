Output assets/terminal.gif

Set Shell "bash"
Set FontSize 14
Set Width 860
Set Height 520
Set Padding 15
Set Theme "Catppuccin Mocha"
Set TypingSpeed 35ms

# Hidden setup
Hide
Type "source scripts/demo_env.sh"
Enter
Sleep 500ms
Show

Hide
Type "clear"
Enter
Sleep 300ms
Show

# --- CLI part ---

Type "# Install elephagent"
Enter
Sleep 500ms

Type "pip install elephagent"
Enter
Sleep 2s

Type "# Initialize in your project"
Enter
Sleep 500ms

Type "elephagent init"
Enter
Sleep 3s

# --- Claude Code part ---

Type "# Use skills inside Claude Code"
Enter
Sleep 500ms

Type "claude"
Enter
Sleep 2s

Type "/el-init-memory"
Enter
Sleep 3s

Type '/el-remember "Use pnpm. Redis required for API tests."'
Enter
Sleep 2.5s

Type "/el-handoff"
Enter
Sleep 4s

Type "/exit"
Enter
Sleep 1.5s

Type "# All agents now share the same memory."
Enter
Sleep 3s
