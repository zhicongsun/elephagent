Output assets/terminal.gif

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
Sleep 4s

# Init in a project
Type "# Initialize in your project"
Enter
Sleep 500ms

Type "cd $(mktemp -d) && elephagent init"
Enter
Sleep 3s

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

# Import
Type "# Import existing skills from other platforms"
Enter
Sleep 500ms

Type "elephagent import"
Enter
Sleep 2.5s

Type ""
Enter
Type "# Claude Code, Cursor, and Codex now share the same memory."
Enter
Sleep 3s
