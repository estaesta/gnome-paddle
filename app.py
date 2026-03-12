#!/usr/bin/env python3
"""
Simple OCR Desktop App
GTK4 + Libadwaita + PaddleOCR (via Bun sidecar)
Uses libportal (Xdp) for screenshots — same as Frog.
"""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Xdp", "1.0")

import json
import subprocess
import threading
import time
import signal
import sys
import os
import urllib.request
import urllib.error
import tempfile

from gi.repository import Gtk, Adw, Gdk, Gio, GLib, Xdp


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
OCR_SERVER_URL = "http://localhost:18765"
APP_DIR = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# OCR Server Manager
# ---------------------------------------------------------------------------
class OcrServerManager:
    """Manages the lifecycle of the Bun OCR server."""

    def __init__(self):
        self.process = None

    def _get_server_command(self):
        compiled_bin = os.environ.get("OCR_SERVER_BIN")
        if compiled_bin and os.path.isfile(compiled_bin):
            return [compiled_bin]
        else:
            return ["bun", "run", os.path.join(APP_DIR, "ocr_server.ts")]

    def start(self):
        if self.is_running():
            return True

        cmd = self._get_server_command()
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=APP_DIR,
            )
            for _ in range(120):
                time.sleep(1)
                if self.is_running():
                    try:
                        req = urllib.request.Request(f"{OCR_SERVER_URL}/health")
                        with urllib.request.urlopen(req, timeout=2) as resp:
                            data = json.loads(resp.read())
                            if data.get("status") == "ok":
                                return True
                    except Exception:
                        pass
            return False
        except FileNotFoundError:
            print(f"ERROR: Could not find: {cmd[0]}")
            return False

    def is_running(self):
        return self.process is not None and self.process.poll() is None

    def stop(self):
        if self.process and self.is_running():
            try:
                req = urllib.request.Request(
                    f"{OCR_SERVER_URL}/shutdown", method="POST", data=b""
                )
                urllib.request.urlopen(req, timeout=3)
            except Exception:
                pass
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception:
                self.process.kill()

    def send_image(self, image_path: str) -> dict:
        with open(image_path, "rb") as f:
            image_data = f.read()

        req = urllib.request.Request(
            f"{OCR_SERVER_URL}/ocr",
            method="POST",
            data=image_data,
            headers={"Content-Type": "application/octet-stream"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())


# ---------------------------------------------------------------------------
# Screenshot Service (same approach as Frog)
# ---------------------------------------------------------------------------
class ScreenshotService:
    """
    Uses libportal (Xdp.Portal) to take screenshots.
    This triggers the native GNOME screenshot UI.
    The screenshot is a temp file — not saved to ~/Pictures.
    """

    def __init__(self):
        self.portal = Xdp.Portal()
        self._callback = None

    def capture(self, callback):
        """
        Trigger interactive screenshot (region selection).
        callback(filepath: str | None, error: str | None)
        """
        self._callback = callback
        self.portal.take_screenshot(
            None,                             # parent window
            Xdp.ScreenshotFlags.INTERACTIVE,  # let user select region
            None,                             # cancellable
            self._on_screenshot_finish,       # callback
            None,                             # user_data
        )

    def _on_screenshot_finish(self, source_object, res, user_data):
        try:
            uri = self.portal.take_screenshot_finish(res)

            if not uri:
                GLib.idle_add(self._callback, None, "No screenshot URI returned")
                return

            # Convert file:// URI to path
            if uri.startswith("file://"):
                filepath = GLib.Uri.unescape_string(uri[7:])
            else:
                filepath = uri

            if os.path.exists(filepath):
                GLib.idle_add(self._callback, filepath, None)
            else:
                GLib.idle_add(self._callback, None, f"Screenshot file not found: {filepath}")

        except GLib.Error as e:
            if e.code == Gio.IOErrorEnum.CANCELLED:
                GLib.idle_add(self._callback, None, "Cancelled by user")
            else:
                GLib.idle_add(self._callback, None, f"Screenshot error: {e.message}")
        except Exception as e:
            GLib.idle_add(self._callback, None, f"Screenshot error: {e}")


# ---------------------------------------------------------------------------
# Main Application Window
# ---------------------------------------------------------------------------
class OcrWindow(Adw.ApplicationWindow):
    def __init__(self, app, server_manager):
        super().__init__(application=app, title="OCR")
        self.server_manager = server_manager
        self.screenshot_service = ScreenshotService()
        self.set_default_size(500, 400)

        # --- Header Bar ---
        header = Adw.HeaderBar()

        self.copy_btn = Gtk.Button(icon_name="edit-copy-symbolic")
        self.copy_btn.set_tooltip_text("Copy text to clipboard")
        self.copy_btn.connect("clicked", self.on_copy_clicked)
        self.copy_btn.set_sensitive(False)
        header.pack_end(self.copy_btn)

        # --- Main Layout ---
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

        # Status banner
        self.status_banner = Adw.Banner()
        self.status_banner.set_title("Starting OCR engine...")
        self.status_banner.set_revealed(True)
        content.append(self.status_banner)

        # Capture button
        self.capture_btn = Gtk.Button(label="📷  Capture & Recognize")
        self.capture_btn.add_css_class("suggested-action")
        self.capture_btn.add_css_class("pill")
        self.capture_btn.set_sensitive(False)
        self.capture_btn.connect("clicked", self.on_capture_clicked)
        content.append(self.capture_btn)

        # Spinner
        self.spinner = Gtk.Spinner()
        content.append(self.spinner)

        # Result text view
        scrolled = Gtk.ScrolledWindow(vexpand=True)
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.add_css_class("card")

        self.text_view = Gtk.TextView()
        self.text_view.set_editable(False)
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.text_view.set_left_margin(12)
        self.text_view.set_right_margin(12)
        self.text_view.set_top_margin(12)
        self.text_view.set_bottom_margin(12)
        scrolled.set_child(self.text_view)
        content.append(scrolled)

        main_box.append(content)
        self.set_content(main_box)

        # Start OCR server in background
        threading.Thread(target=self._start_server, daemon=True).start()

    def _start_server(self):
        success = self.server_manager.start()
        if success:
            GLib.idle_add(self._on_server_ready)
        else:
            GLib.idle_add(self._on_server_failed)

    def _on_server_ready(self):
        self.status_banner.set_title("✅ OCR engine ready")
        GLib.timeout_add_seconds(2, lambda: self.status_banner.set_revealed(False))
        self.capture_btn.set_sensitive(True)

    def _on_server_failed(self):
        self.status_banner.set_title("❌ Failed to start OCR engine. Is Bun installed?")

    def on_capture_clicked(self, btn):
        self.capture_btn.set_sensitive(False)
        self.spinner.start()

        # Minimize window so it doesn't appear in screenshot
        # self.minimize()

        # Small delay to let window minimize, then trigger screenshot
        GLib.timeout_add(400, self._trigger_screenshot)

    def _trigger_screenshot(self):
        self.screenshot_service.capture(self._on_screenshot_done)
        return False

    def _on_screenshot_done(self, filepath, error):
        if error or not filepath:
            self.spinner.stop()
            self.capture_btn.set_sensitive(True)
            self.status_banner.set_title(f"⚠️ {error or 'No image captured'}")
            self.status_banner.set_revealed(True)
            self.present()
            return

        self.status_banner.set_title("🔍 Recognizing text...")
        self.status_banner.set_revealed(True)
        self.present()

        def do_ocr():
            try:
                result = self.server_manager.send_image(filepath)
                GLib.idle_add(self._on_ocr_done, result)
            except Exception as e:
                GLib.idle_add(self._on_ocr_error, str(e))
            finally:
                # Clean up screenshot temp file
                try:
                    os.unlink(filepath)
                except Exception:
                    pass

        threading.Thread(target=do_ocr, daemon=True).start()

    def _on_ocr_done(self, result):
        self.spinner.stop()
        self.capture_btn.set_sensitive(True)

        if result.get("status") == "success":
            text = result.get("text", "")
            if text.strip():
                self.text_view.get_buffer().set_text(text)
                self.copy_btn.set_sensitive(True)
                self.status_banner.set_title("✅ Text recognized!")
                self.status_banner.set_revealed(True)
                GLib.timeout_add_seconds(2, lambda: self.status_banner.set_revealed(False))
            else:
                self.text_view.get_buffer().set_text("")
                self.copy_btn.set_sensitive(False)
                self.status_banner.set_title("⚠️ No text found in the selected region")
                self.status_banner.set_revealed(True)
        else:
            self._on_ocr_error(result.get("message", "Unknown error"))

    def _on_ocr_error(self, error_msg):
        self.spinner.stop()
        self.capture_btn.set_sensitive(True)
        self.status_banner.set_title(f"❌ OCR Error: {error_msg}")
        self.status_banner.set_revealed(True)

    def on_copy_clicked(self, btn):
        buffer = self.text_view.get_buffer()
        start, end = buffer.get_bounds()
        text = buffer.get_text(start, end, False)
        if text.strip():
            clipboard = Gdk.Display.get_default().get_clipboard()
            clipboard.set(text)
            self.status_banner.set_title("📋 Copied to clipboard!")
            self.status_banner.set_revealed(True)
            GLib.timeout_add_seconds(2, lambda: self.status_banner.set_revealed(False))


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
class OcrApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.github.ocrapp")
        self.server_manager = OcrServerManager()

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = OcrWindow(self, self.server_manager)
        win.present()

    def do_shutdown(self):
        self.server_manager.stop()
        Adw.Application.do_shutdown(self)


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
def main():
    app = OcrApp()
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app.run(sys.argv)


if __name__ == "__main__":
    main()
