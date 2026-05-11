#!/bin/bash
# Sourced by demo.tape to set up a clean demo environment.

export PS1='$ '

alias claude='bash scripts/fake_claude.sh'

pip() {
    if [ "$1" = "install" ]; then
        sleep 0.5
        echo "Successfully installed elephagent-0.3.0"
    else
        command pip "$@"
    fi
}
export -f pip

elephagent() {
    case "$1" in
        init)
            sleep 0.5
            echo "Created .agent/memory/ with starter files"
            sleep 0.2
            echo "Deployed 7 built-in skills"
            sleep 0.2
            echo "Generated CLAUDE.md, AGENTS.md, .cursor/rules/"
            sleep 0.2
            echo "Configured MCP server in .mcp.json"
            sleep 0.2
            echo ""
            echo "Agent kit ready."
            ;;
        *)
            command elephagent "$@"
            ;;
    esac
}
export -f elephagent
