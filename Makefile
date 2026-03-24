# Makefile for gnome-paddle (Python-only variant)

# ==============================================================================
# Variables
# ==============================================================================

# Get the directory of the Makefile
APP_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

# Python
VENV_DIR = $(APP_DIR)/.venv
PYTHON = $(VENV_DIR)/bin/python
PIP = $(VENV_DIR)/bin/pip

# ==============================================================================
# Standard Targets
# ==============================================================================

.PHONY: all
all: setup

.PHONY: setup
setup: venv
	@echo "✅ Project setup complete. Run 'make run' to start."

.PHONY: run
run:
	@$(PYTHON) $(APP_DIR)/app.py

.PHONY: clean
clean:
	@echo "🧹 Cleaning up..."
	@rm -rf $(VENV_DIR)
	@echo "✅ Cleanup complete."

# ==============================================================================
# Internal Targets (used by other targets)
# ==============================================================================

.PHONY: venv
venv: $(VENV_DIR)/pyvenv.cfg

$(VENV_DIR)/pyvenv.cfg: requirements.txt
	@echo "🐍 Creating Python virtual environment..."
	@python3 -m venv --system-site-packages $(VENV_DIR)
	@echo "🐍 Installing Python dependencies..."
	@$(PIP) install -r requirements.txt
	@touch $(VENV_DIR)/pyvenv.cfg

.PHONY: help
help:
	@echo "Makefile for gnome-paddle (Python-only variant)"
	@echo ""
	@echo "Usage:"
	@echo "  make setup         - Create venv and install Python dependencies."
	@echo "  make run           - Run the application."
	@echo "  make clean         - Remove virtual environment."
	@echo "  make help          - Show this help message."
