#!/bin/bash
# Run POTA station fetcher - uses curl to bypass SSL issues

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

echo "Running POTA fetcher..."
python3 "$SCRIPT_DIR/fetch_pota.py"

cp "$SCRIPT_DIR"/*html /var/www/html