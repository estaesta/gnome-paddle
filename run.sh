#!/usr/bin/env bash

APP_DIR="$(cd "$(dirname "\$0")" && pwd)"
VENV_DIR="$APP_DIR/.venv"

# Check if venv exists
if [ ! -d "$VENV_DIR" ]; then
    echo "❌ Virtual environment not found."
    echo "   Run ./setup.sh first."
    exit 1
fi

# Activate venv and run
source "$VENV_DIR/bin/activate"
python3 "$APP_DIR/app.py" "$@"
