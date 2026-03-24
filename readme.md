# Gnome Paddle (Python OCR branch)

A lightweight GNOME screenshot OCR app using an in-process Python ONNX OCR engine.

This branch uses the Python OCR library directly in-process.

## Credits

OCR pipeline references and model ecosystem are inspired by:

- https://github.com/PT-Perkasa-Pilar-Utama/ppu-ocv
- https://github.com/PT-Perkasa-Pilar-Utama/ppu-paddle-ocr

## Prerequisites

### System libraries (GTK4 + Portal)

**Ubuntu/Debian**
```bash
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 gir1.2-xdportal-1.0 python3-venv
```

**Fedora**
```bash
sudo dnf install python3-gobject gtk4 libadwaita libportal-gtk4
```

**Arch Linux**
```bash
sudo pacman -S python-gobject gtk4 libadwaita libportal libportal-gtk4
```

## Installation

```bash
make setup
```

## Usage

```bash
make run
# or
./run.sh
```

## Model sources

Default model URLs are configured in `app.py` and cached to:

`~/.cache/ppu-paddle-ocr`

You can override with env vars:

- `OCR_DET_URL`
- `OCR_REC_URL`
- `OCR_DICT_URL`

## License

MIT (see `LICENSE`).
