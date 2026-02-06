#!/bin/zsh
set -e

SCRIPT_DIR="$(dirname "$0:A")"
CLINE_DIR="$SCRIPT_DIR/agent-service/cline"

cd "$CLINE_DIR"

echo "Starting agent service..."
./cli/bin/cline-host --port 26041 &
cd dist-standalone
node cline-core.js --port 26040 --host-bridge-port 26041
