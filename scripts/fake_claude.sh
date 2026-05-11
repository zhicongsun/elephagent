#!/bin/bash
# Simulated Claude Code REPL for demo GIF recording.
# Usage: bash scripts/fake_claude.sh (or alias to "claude" in demo.tape)

BLUE='\033[1;34m'
GREEN='\033[32m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

echo ""
printf "${BLUE}╭─────────────────────────────────────────────────────╮${RESET}\n"
printf "${BLUE}│${RESET}  ${BOLD}✻ Welcome to Claude Code!${RESET}                           ${BLUE}│${RESET}\n"
printf "${BLUE}│${RESET}                                                     ${BLUE}│${RESET}\n"
printf "${BLUE}│${RESET}  ${DIM}Type a message or use / for slash commands${RESET}         ${BLUE}│${RESET}\n"
printf "${BLUE}╰─────────────────────────────────────────────────────╯${RESET}\n"
echo ""

prompt() { printf "${BOLD}>${RESET} "; }

prompt
while IFS= read -r input; do
    echo ""
    case "$input" in
        "/el-init-memory")
            printf "I'll set up the shared memory system for your project.\n"
            echo ""
            sleep 0.3
            printf "  ${GREEN}✓${RESET} Created .agent/memory/ with starter files\n"
            sleep 0.15
            printf "  ${GREEN}✓${RESET} Deployed 7 built-in skills\n"
            sleep 0.15
            printf "  ${GREEN}✓${RESET} Generated CLAUDE.md, AGENTS.md, .cursor/rules/\n"
            sleep 0.15
            printf "  ${GREEN}✓${RESET} Configured MCP server in .mcp.json\n"
            echo ""
            printf "Memory system is ready — all agents now share the same memory.\n"
            ;;
        /el-remember*)
            printf "Saved to shared memory.\n"
            echo ""
            sleep 0.3
            printf "  ${GREEN}✓${RESET} Appended to .agent/memory/log.md\n"
            sleep 0.15
            printf "  ${GREEN}✓${RESET} Rebuilt all platform adapter files\n"
            echo ""
            printf "Claude Code, Cursor, and Codex will all see this note.\n"
            ;;
        "/el-handoff")
            printf "I'll summarize this session for the next agent.\n"
            echo ""
            sleep 0.3
            printf "  ${GREEN}✓${RESET} Reviewed conversation history\n"
            sleep 0.15
            printf "  ${GREEN}✓${RESET} Saved handoff note to .agent/memory/log.md\n"
            echo ""
            printf "  ${BOLD}Handoff Summary${RESET}\n"
            printf "  ${DIM}Worked on:${RESET}  Project setup and configuration\n"
            printf "  ${DIM}Status:${RESET}     Memory initialized, first note saved\n"
            printf "  ${DIM}Next steps:${RESET} Continue development in Cursor or Codex\n"
            echo ""
            printf "Ready to switch — the next agent picks up right where you left off.\n"
            ;;
        "/exit"|"exit")
            echo "  Goodbye!"
            echo ""
            exit 0
            ;;
        "")
            ;;
        *)
            printf "Unknown command: %s\n" "$input"
            ;;
    esac
    echo ""
    prompt
done
