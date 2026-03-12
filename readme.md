# Gnome Paddle

A lightweight, native-feeling Linux desktop application for quick OCR using PaddleOCR.

Built using the [ppu-paddle-ocr](https://github.com/PT-Perkasa-Pilar-Utama/ppu-paddle-ocr) library, this project leverages the power of PaddleOCR for accurate text recognition while providing a blazingly fast and seamless user experience on Linux desktops.

## Prerequisites

Before installing, ensure you have the following system dependencies. The setup command will check for these and guide you if any are missing.

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

2. **Run the setup command:**
   This will create a Python virtual environment and install all dependencies.
   ```bash
   make setup
   ```

## Usage

You can run the application using the `make` command (recommended):
```bash
make run
```
Alternatively, you can use the `run.sh` script:
```bash
./run.sh
```

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
