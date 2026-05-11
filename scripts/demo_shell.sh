#!/bin/bash
# Shell wrapper for VHS demo recording.
# Pre-configures environment so nothing private leaks.

export PS1='$ '
export HOME=/tmp/demo-home
mkdir -p "$HOME"

# "claude" → fake REPL
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
alias claude="bash $SCRIPT_DIR/fake_claude.sh"

# "pip" → fake output for install line
pip() {
    if [[ "$1" == "install" && "$2" == "elephagent" ]]; then
        sleep 0.5
        echo "Successfully installed elephagent-0.3.0"
    else
        command pip "$@"
    fi
}
export -f pip

exec bash --norc --noprofile
