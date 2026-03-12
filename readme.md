# Simple OCR (Linux)

A lightweight, native-feeling Linux desktop application for quick OCR using PaddleOCR.

Built using the [ppu-paddle-ocr](https://github.com/PT-Perkasa-Pilar-Utama/ppu-paddle-ocr) library, this project leverages the power of PaddleOCR for accurate text recognition while providing blazingly fast and seamless user experience on Linux desktops.

## Prerequisites

Before installing, ensure you have the following system dependencies:

### 1. Bun
```bash
curl -fsSL https://bun.sh/install | bash
```

### 2. System Libraries (GTK4 & Portal)
**Ubuntu/Debian:**
```bash
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 gir1.2-xdportal-1.0 python3-venv
```

**Fedora:**
```bash
sudo dnf install python3-gobject gtk4 libadwaita libportal-gtk4
```

**Arch Linux:**
```bash
sudo pacman -S python-gobject gtk4 libadwaita libportal libportal-gtk4
```

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/estaesta/gnome-paddle.git
   cd gnome-paddle
   ```

2. **Run the setup script:**
   This will create a Python virtual environment and install the Bun dependencies.
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

## Usage

Run the application using the provided launcher:
```bash
./run.sh
```

## License
MIT. See [LICENSE](LICENSE) for details.
