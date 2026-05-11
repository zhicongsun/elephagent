#!/bin/bash
# Wrapper script for VHS demo recording.
# Sets up a clean environment with "claude" aliased to the fake REPL,
# then records the demo tape.
#
# Usage: bash scripts/record_demo.sh

set -e
cd "$(dirname "$0")/.."

DEMO_DIR=$(mktemp -d)
SCRIPT_DIR=$(cd scripts && pwd)

# Create a "claude" shim in temp dir
cat > "$DEMO_DIR/claude" <<'SHIM'
#!/bin/bash
exec bash "SCRIPT_DIR_PLACEHOLDER/fake_claude.sh"
SHIM
sed -i '' "s|SCRIPT_DIR_PLACEHOLDER|$SCRIPT_DIR|" "$DEMO_DIR/claude"
chmod +x "$DEMO_DIR/claude"

export PATH="$DEMO_DIR:$PATH"
export PS1="$ "

echo "Recording demo..."
vhs demo.tape

echo "Combining intro + terminal..."
python3 scripts/make_demo.py

echo "Done! Output: assets/demo.gif"
rm -rf "$DEMO_DIR"
