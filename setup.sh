#!/usr/bin/env bash
set -e

echo "================================"
echo "  OCR App Setup"
echo "================================"
echo ""

APP_DIR="$(cd "$(dirname "\$0")" && pwd)"
VENV_DIR="$APP_DIR/.venv"

# ---------------------------------------------------------------
# 1. Check system dependencies
# ---------------------------------------------------------------

if ! command -v bun &> /dev/null; then
    echo "❌ Bun is not installed."
    echo "   Install: curl -fsSL https://bun.sh/install | bash"
    exit 1
fi
echo "✅ Bun found: $(bun --version)"

if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed."
    exit 1
fi
echo "✅ Python3 found: $(python3 --version)"

# Check python3-venv
python3 -m venv --help &> /dev/null || {
    echo "❌ python3-venv not found."
    echo "   Ubuntu/Debian: sudo apt install python3-venv"
    exit 1
}
echo "✅ python3-venv found"

# Check GTK4 + Libadwaita + libportal
python3 -c "
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Xdp', '1.0')
from gi.repository import Gtk, Adw, Xdp
" 2>/dev/null || {
    echo ""
    echo "❌ Missing system GI packages (GTK4 / Libadwaita / libportal)."
    echo ""
    echo "   Ubuntu/Debian:"
    echo "     sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 gir1.2-xdportal-1.0"
    echo ""
    echo "   Fedora:"
    echo "     sudo dnf install python3-gobject gtk4 libadwaita libportal-gtk4"
    echo ""
    echo "   Arch:"
    echo "     sudo pacman -S python-gobject gtk4 libadwaita libportal libportal-gtk4"
    echo ""
    exit 1
}
echo "✅ GTK4 + Libadwaita + libportal found"

# ---------------------------------------------------------------
# 2. Create venv with system site packages
# ---------------------------------------------------------------
echo ""
echo "🐍 Creating Python virtual environment..."
python3 -m venv --system-site-packages "$VENV_DIR"
echo "✅ Virtual environment created at $VENV_DIR"

# ---------------------------------------------------------------
# 3. Install Bun dependencies
# ---------------------------------------------------------------
echo ""
echo "📦 Installing Bun dependencies..."
cd "$APP_DIR"
bun install

echo ""
echo "================================"
echo "  ✅ Setup complete!"
echo ""
echo "  Run the app with:"
echo "    ./run.sh"
echo "================================"
