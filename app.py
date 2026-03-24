import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Xdp", "1.0")

import threading
import time
import sys
import os
import signal
from typing import Optional, List, Dict, Callable, Any

# Local ONNX OCR wrapper
from paddle_py.ocr_server import PaddleOnnxOCR

from gi.repository import Gtk, Adw, Gdk, Gio, GLib, Xdp


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# OCR Server Manager (in-process ONNX OCR)
# ---------------------------------------------------------------------------
class OcrServerManager:
    """Manages an in-process Paddle ONNX OCR instance.

    This replaces the previous Bun/TypeScript server approach. The manager
    initializes a PaddleOnnxOCR instance and exposes send_image() which returns
    the same JSON-like dict structure the UI expects.
    """

    def __init__(self) -> None:
        # Read debug/config from environment
        debug_env = os.environ.get("OCR_DEBUG", "0").lower()
        debug_flag = debug_env in ("1", "true", "yes")
        beam_env = os.environ.get("OCR_BEAM", "0").lower()
        beam_flag = beam_env in ("1", "true", "yes")
        beam_width = int(os.environ.get("OCR_BEAM_WIDTH", "5"))

        # Default model URLs (hard-coded to the PP-OCRv5 mobile models and ppocrv5_dict)
        DEFAULT_DET_URL = "https://media.githubusercontent.com/media/PT-Perkasa-Pilar-Utama/ppu-paddle-ocr-models/main/detection/PP-OCRv5_mobile_det_infer.onnx"
        DEFAULT_REC_URL = "https://media.githubusercontent.com/media/PT-Perkasa-Pilar-Utama/ppu-paddle-ocr-models/main/recognition/PP-OCRv5_mobile_rec_infer.onnx"
        DEFAULT_DICT_URL = "https://raw.githubusercontent.com/PT-Perkasa-Pilar-Utama/ppu-paddle-ocr-models/main/recognition/ppocrv5_dict.txt"

        # Use environment overrides if present, otherwise use hard-coded defaults
        det_url = os.environ.get('OCR_DET_URL', DEFAULT_DET_URL)
        rec_url = os.environ.get('OCR_REC_URL', DEFAULT_REC_URL)
        dict_url = os.environ.get('OCR_DICT_URL', DEFAULT_DICT_URL)

        # Pass URLs to the OCR wrapper; it will download into ~/.cache/ppu-paddle-ocr if missing
        self.ocr: Optional[PaddleOnnxOCR] = PaddleOnnxOCR(
            det_model_path=det_url,
            rec_model_path=rec_url,
            dict_path=dict_url,
            debug=debug_flag,
            use_beam_search=beam_flag,
            beam_width=beam_width,
        )
        self.initialized: bool = False

    def start(self) -> bool:
        if self.initialized:
            return True
        try:
            self.ocr.initialize()
            self.initialized = True
            print("✅ OCR engine initialized.")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize OCR engine: {e}")
            return False

    def is_running(self) -> bool:
        return self.initialized

    def stop(self) -> None:
        if self.initialized and self.ocr:
            try:
                self.ocr.destroy()
            except Exception as e:
                print(f"Error destroying OCR engine: {e}")
            self.initialized = False
            print("✅ OCR engine stopped.")

    def send_image(self, image_path: str) -> Dict[str, Any]:
        try:
            with open(image_path, "rb") as f:
                image_data = f.read()

            # recognize directly using the ONNX wrapper
            result = self.ocr.recognize(image_data)

            return {
                "status": "success",
                "text": result.get("text", ""),
                "lines": result.get("lines", []),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}


# ---------------------------------------------------------------------------
# Screenshot Service
# ---------------------------------------------------------------------------
class ScreenshotService:
    """
    Uses libportal (Xdp.Portal) to take screenshots.
    This triggers the native GNOME screenshot UI.
    The screenshot is a temp file — not saved to ~/Pictures.
    """

    def __init__(self) -> None:
        self.portal: Xdp.Portal = Xdp.Portal()
        self._callback: Optional[Callable[[Optional[str], Optional[str]], None]] = None

    def capture(self, callback: Callable[[Optional[str], Optional[str]], None]) -> None:
        """
        Trigger interactive screenshot (region selection).
        The callback will be invoked with (filepath, error).
        """
        self._callback = callback
        self.portal.take_screenshot(
            None,  # parent window
            Xdp.ScreenshotFlags.INTERACTIVE,  # let user select region
            None,  # cancellable
            self._on_screenshot_finish,  # callback
            None,  # user_data
        )

    def _on_screenshot_finish(self, source_object, res, user_data) -> None:
        if not self._callback:
            return

        try:
            uri = self.portal.take_screenshot_finish(res)

            if not uri:
                GLib.idle_add(self._callback, None, "Screenshot cancelled or failed.")
                return

            # Convert file:// URI to path
            filepath = GLib.Uri.unescape_string(uri[7:]) if uri.startswith("file://") else uri

            if os.path.exists(filepath):
                GLib.idle_add(self._callback, filepath, None)
            else:
                GLib.idle_add(self._callback, None, f"Screenshot file not found: {filepath}")

        except GLib.Error as e:
            if e.code == Gio.IOErrorEnum.CANCELLED:
                GLib.idle_add(self._callback, None, "Cancelled by user.")
            else:
                GLib.idle_add(self._callback, None, f"Portal error: {e.message}")
        except Exception as e:
            GLib.idle_add(self._callback, None, f"Unexpected error: {e}")


# ---------------------------------------------------------------------------
# Main Application Window
# ---------------------------------------------------------------------------
class OcrWindow(Adw.ApplicationWindow):
    def __init__(self, app: "OcrApp", server_manager: OcrServerManager):
        super().__init__(application=app, title="gnome-paddle")
        self.server_manager = server_manager
        self.screenshot_service = ScreenshotService()
        self.set_default_size(500, 400)

        self._init_ui()

        # Start OCR engine in background
        threading.Thread(target=self._start_server, daemon=True).start()

    # --------------------------------------------------------------------
    # UI Initialization
    # --------------------------------------------------------------------
    def _init_ui(self) -> None:
        """Create and arrange all widgets for the window."""
        header = Adw.HeaderBar()
        self.copy_btn = Gtk.Button(icon_name="edit-copy-symbolic")
        self.copy_btn.set_tooltip_text("Copy text to clipboard")
        self.copy_btn.connect("clicked", self.on_copy_clicked)
        self.copy_btn.set_sensitive(False)
        header.pack_end(self.copy_btn)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_box.append(header)

        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            margin_start=16,
            margin_end=16,
            margin_top=16,
            margin_bottom=16,
        )

        self.status_banner = Adw.Banner()
        self._set_status("Starting OCR engine...", revealed=True)
        content.append(self.status_banner)

        self.capture_btn = Gtk.Button(label="📷  Capture & Recognize")
        self.capture_btn.add_css_class("suggested-action")
        self.capture_btn.add_css_class("pill")
        self.capture_btn.set_sensitive(False)
        self.capture_btn.connect("clicked", self.on_capture_clicked)
        content.append(self.capture_btn)

        self.spinner = Gtk.Spinner(vexpand=False, halign=Gtk.Align.CENTER)
        content.append(self.spinner)

        scrolled = Gtk.ScrolledWindow(vexpand=True)
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.add_css_class("card")

        self.text_view = Gtk.TextView(
            editable=False,
            wrap_mode=Gtk.WrapMode.WORD_CHAR,
            left_margin=12,
            right_margin=12,
            top_margin=12,
            bottom_margin=12,
        )
        scrolled.set_child(self.text_view)
        content.append(scrolled)

        main_box.append(content)
        self.set_content(main_box)

    # --------------------------------------------------------------------
    # Status & State Management
    # --------------------------------------------------------------------
    def _set_status(self, title: str, revealed: bool = True, autohide: bool = False) -> None:
        self.status_banner.set_title(title)
        self.status_banner.set_revealed(revealed)
        if autohide:
            GLib.timeout_add_seconds(3, lambda: self.status_banner.set_revealed(False))

    def _set_ui_busy(self, busy: bool) -> None:
        self.capture_btn.set_sensitive(not busy)
        if busy:
            self.spinner.start()
        else:
            self.spinner.stop()

    # --------------------------------------------------------------------
    # Server Handling
    # --------------------------------------------------------------------
    def _start_server(self) -> None:
        success = self.server_manager.start()
        GLib.idle_add(self._on_server_ready if success else self._on_server_failed)

    def _on_server_ready(self) -> None:
        self._set_status("✅ OCR engine ready", autohide=True)
        self.capture_btn.set_sensitive(True)

    def _on_server_failed(self) -> None:
        self._set_status("❌ Failed to start OCR engine. Is onnxruntime and models installed?")

    # --------------------------------------------------------------------
    # Screenshot & OCR Flow
    # --------------------------------------------------------------------
    def on_capture_clicked(self, btn: Gtk.Button) -> None:
        self._set_ui_busy(True)
        # Small delay to let window minimize, then trigger screenshot
        GLib.timeout_add(250, self._trigger_screenshot)

    def _trigger_screenshot(self) -> bool:
        self.screenshot_service.capture(self._on_screenshot_done)
        return False  # Do not repeat

    def _on_screenshot_done(self, filepath: Optional[str], error: Optional[str]) -> None:
        self.present()  # Bring window back to front

        if error or not filepath:
            self._set_status(f"⚠️ {error or 'No image captured'}")
            self._set_ui_busy(False)
            return

        self._set_status("🔍 Recognizing text...")
        threading.Thread(target=self._do_ocr, args=(filepath,), daemon=True).start()

    def _do_ocr(self, filepath: str) -> None:
        try:
            result = self.server_manager.send_image(filepath)
            GLib.idle_add(self._on_ocr_done, result)
        except Exception as e:
            GLib.idle_add(self._on_ocr_error, f"An unexpected error occurred: {e}")
        finally:
            try:
                os.unlink(filepath)
            except OSError as e:
                print(f"Warning: Failed to delete temp screenshot: {e}")

    def _on_ocr_done(self, result: Dict) -> None:
        self._set_ui_busy(False)

        if result.get("status") == "success":
            text = result.get("text", "").strip()
            if text:
                self.text_view.get_buffer().set_text(text)
                self.copy_btn.set_sensitive(True)
                self._set_status("✅ Text recognized!", autohide=True)
            else:
                self.text_view.get_buffer().set_text("")
                self.copy_btn.set_sensitive(False)
                self._set_status("⚠️ No text found in the selected region.")
        else:
            self._on_ocr_error(result.get("message", "Unknown OCR error"))

    def _on_ocr_error(self, error_msg: str) -> None:
        self._set_ui_busy(False)
        self._set_status(f"❌ OCR Error: {error_msg}")

    # --------------------------------------------------------------------
    # Event Handlers
    # --------------------------------------------------------------------
    def on_copy_clicked(self, btn: Gtk.Button) -> None:
        buffer = self.text_view.get_buffer()
        text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)
        if text.strip():
            Gdk.Display.get_default().get_clipboard().set(text)
            self._set_status("📋 Copied to clipboard!", autohide=True)


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
class OcrApp(Adw.Application):
    """Main GTK application for gnome-paddle."""

    def __init__(self, application_id: str):
        super().__init__(application_id=application_id)
        self.server_manager = OcrServerManager()

    def do_activate(self) -> None:
        """Called when the application is activated."""
        win = self.props.active_window
        if not win:
            win = OcrWindow(self, self.server_manager)
        win.present()

    def do_shutdown(self) -> None:
        """Called when the application is shutting down."""
        self.server_manager.stop()
        Adw.Application.do_shutdown(self)


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
APP_ID = "com.github.esta.gnome-paddle"

def handle_sigint(sig, frame):
    """SIGINT handler to ensure clean shutdown."""
    app = Gio.Application.get_default()
    if app:
        app.quit()

def main() -> int:
    """Application entry point."""
    app = OcrApp(application_id=APP_ID)
    signal.signal(signal.SIGINT, handle_sigint)
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
