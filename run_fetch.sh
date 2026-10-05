#!/bin/bash
# Fetch POTA stations and publish the dashboard to the web root.
# Override the destination with PUBLISH_DIR=/some/path ./run_fetch.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PUBLISH_DIR="${PUBLISH_DIR:-/var/www/html}"
DASHBOARD="$SCRIPT_DIR/pota_active_stations.html"

# No virtualenv needed: fetch_pota.py only uses the standard library.
python3 "$SCRIPT_DIR/fetch_pota.py"

if [ -d "$PUBLISH_DIR" ] && [ -w "$PUBLISH_DIR" ]; then
    cp "$DASHBOARD" "$PUBLISH_DIR/"
    echo "Published to $PUBLISH_DIR/$(basename "$DASHBOARD")"
else
    echo "WARNING: $PUBLISH_DIR is not a writable directory, skipping publish" >&2
fi
