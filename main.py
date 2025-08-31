import io
import os
import threading
import webbrowser
import logging
from typing import Optional

from PIL import Image, ImageDraw
import pystray

from app import create_app
from app.config import load_config, setup_logging
from app.server import ServerThread
from app.control_panel import ControlPanel


class TrayApp:
    def __init__(self):
        self.cfg = load_config()
        setup_logging(self.cfg)
        self.log = logging.getLogger(__name__)
        self._maybe_hide_console()
        
        self.log.info("TrayApp initialized with host=%s port=%s", self.cfg.get("host"), self.cfg.get("port"))
        self.app = create_app()
        self.server = ServerThread(
            self.app, self.cfg.get("host", "127.0.0.1"), int(self.cfg.get("port", 5000))
        )
        self._icon: Optional[pystray.Icon] = None
        self._panel: Optional[ControlPanel] = None

    def _create_icon_image(self):
        # Simple generated icon
        img = Image.new("RGB", (64, 64), color=(17, 24, 39))
        d = ImageDraw.Draw(img)
        d.ellipse((12, 12, 52, 52), fill=(56, 189, 248))
        return img

    def _maybe_hide_console(self) -> None:
        # On Windows, hide the console window so only the system tray icon remains
        try:
            if os.name == "nt":
                import ctypes
                hwnd = ctypes.windll.kernel32.GetConsoleWindow()
                if hwnd:
                    ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
                    # Detach console so the taskbar icon from the console host disappears
                    try:
                        ctypes.windll.kernel32.FreeConsole()
                    except Exception:
                        pass
        except Exception:
            pass

    def start_server(self, icon=None, item=None):
        if not self.server.is_running():
            self.log.info("Starting server")
            self.server.start()
            self.update_menu()
        else:
            self.log.debug("Start requested but server already running")

    def stop_server(self, icon=None, item=None):
        if self.server.is_running():
            self.log.info("Stopping server")
            self.server.stop()
            self.update_menu()
        else:
            self.log.debug("Stop requested but server not running")

    def open_ui(self, icon=None, item=None):
        # Ensure server is running before opening UI
        if not self.server.is_running():
            self.log.info("Server not running; starting before opening UI")
            self.server.start()
        url = f"http://127.0.0.1:{int(self.cfg.get('port',5000))}/"
        self.log.info("Opening UI at %s", url)
        webbrowser.open(url)

    def open_api_docs(self, icon=None, item=None):
        url = f"http://127.0.0.1:{int(self.cfg.get('port',5000))}/docs"
        self.log.info("Opening API Docs at %s", url)
        webbrowser.open(url)

    def open_panel(self, icon=None, item=None):
        if not self._panel:
            ui = self.cfg.get("ui", {})
            self._panel = ControlPanel(
                title=str(ui.get("title") or "SSH Log Tools"),
                message=str(ui.get("message") or ""),
                author_name=str(ui.get("author_name") or ""),
                author_email=str(ui.get("author_email") or ""),
                get_status=lambda: self.server.is_running(),
                on_start=self.start_server,
                on_stop=self.stop_server,
                on_open_ui=self.open_ui,
                on_open_docs=self.open_api_docs,
                on_exit=self.quit,
            )
        self._panel.show()

    def quit(self, icon=None, item=None):
        try:
            self.log.info("Quitting application")
            self.stop_server()
        finally:
            if self._icon:
                self._icon.stop()

    def build_menu(self):
        running = self.server.is_running()
        return (
            pystray.MenuItem(
                "Start Server", self.start_server, enabled=not running
            ),
            pystray.MenuItem("Stop Server", self.stop_server, enabled=running),
            # Control Panel on double-click
            pystray.MenuItem("Open Control Panel", self.open_panel, default=True),
            pystray.MenuItem("Open Web UI", self.open_ui),
            pystray.MenuItem("Open API Docs", self.open_api_docs),
            pystray.MenuItem("Exit", self.quit),
        )

    def update_menu(self):
        if self._icon:
            self._icon.menu = pystray.Menu(*self.build_menu())
            self._icon.update_menu()

    def run(self):
        image = self._create_icon_image()
        icon = pystray.Icon("ssh_log_tools", image, "SSH Log Tools", menu=pystray.Menu(*self.build_menu()))
        self._icon = icon
        self.log.info("Tray icon initialized; running event loop")
        try:
            ui = self.cfg.get("ui", {})
            if bool(ui.get("show_on_start", False)):
                self.open_panel()
        except Exception:
            pass
        icon.run()


if __name__ == "__main__":
    TrayApp().run()
