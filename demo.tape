Output assets/demo.gif

Set Shell "bash"
Set FontSize 14
Set Width 860
Set Height 520
Set Padding 15
Set Theme "Catppuccin Mocha"
Set TypingSpeed 35ms

# Install
Type "# Install"
Enter
Sleep 500ms

Type "pip install elephagent"
Enter
Sleep 2s

# Init in a project
Type "# Initialize in your project"
Enter
Sleep 500ms

Type "mkdir my-project && cd my-project"
Enter
Sleep 600ms

Type "elephagent init"
Enter
Sleep 2.5s

# Show structure
Type "# What's inside .agent/"
Enter
Sleep 500ms

Type "tree .agent/"
Enter
Sleep 2.5s

# Remember
Type "# Save a note — all agents can read it"
Enter
Sleep 500ms

Type 'elephagent remember "Use pnpm. Redis required for API tests."'
Enter
Sleep 2s

# Doctor
Type "# Verify everything is in sync"
Enter
Sleep 500ms

Type "elephagent doctor"
Enter
Sleep 2.5s

Type ""
Enter
Type "# Claude Code, Cursor, and Codex now share the same memory."
Enter
Sleep 3s
