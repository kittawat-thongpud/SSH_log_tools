import io
import os
import sys
import threading
import webbrowser
import logging
from typing import Optional
import tempfile


class SingleInstanceError(RuntimeError):
    """Raised when another instance of the app is already running."""
    pass


def acquire_app_lock(name: str = "ssh_log_tools.lock"):
    """Ensure only one running instance by locking a file in temp dir."""
    lock_path = os.path.join(tempfile.gettempdir(), name)
    if os.name == "nt":
        import msvcrt
        try:
            fd = os.open(lock_path, os.O_RDWR | os.O_CREAT)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            return fd
        except OSError as e:
            raise SingleInstanceError("Another instance is already running") from e
    else:
        import fcntl
        fd = os.open(lock_path, os.O_RDWR | os.O_CREAT)
        try:
            fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fd
        except OSError as e:
            raise SingleInstanceError("Another instance is already running") from e

from PIL import Image, ImageDraw, ImageOps
import pystray

from app import create_app
from app.config import load_config, setup_logging
from app.server import ServerThread
from app.control_panel import ControlPanel


def resource_path(rel: str) -> str:
    """Support dev & PyInstaller onefile."""
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, rel)


class TrayApp:
    def __init__(self):
        self.cfg = load_config()
        setup_logging(self.cfg)
        self.log = logging.getLogger(__name__)

        # ---- resolve icon paths/images once ----
        self.icon_path_fs, self.icon_image = self._resolve_icon()

        # ---- maybe hide console by config ----
        self._maybe_hide_console()

        self.log.info(
            "TrayApp initialized with host=%s port=%s icon=%s",
            self.cfg.get("host"), self.cfg.get("port"), self.icon_path_fs or "<generated>"
        )

        self.app = create_app()
        self.server = ServerThread(
            self.app, self.cfg.get("host", "127.0.0.1"), int(self.cfg.get("port", 5000))
        )
        self._icon: Optional[pystray.Icon] = None
        self._panel: Optional[ControlPanel] = None

        # ---- (Windows) set an explicit AppUserModelID so taskbar uses our app grouping/icon ----
        self._set_windows_appid("com.kittawat.sshlogtools")

    # ------------- icon handling -------------
    def _resolve_icon(self) -> tuple[Optional[str], Image.Image]:
        """
        Returns (filesystem_icon_path_or_None, PIL.Image for tray).
        If config has ui.icon_path and file exists, use it.
        Else, fall back to generated vector-like icon.
        """
        ui = self.cfg.get("ui", {}) if isinstance(self.cfg.get("ui"), dict) else {}
        raw_path = (ui.get("icon_path") or "").strip()

        def _mk_fallback() -> Image.Image:
            # minimal terminal style: dark bg + cyan circle + '>_' prompt
            img = Image.new("RGBA", (256, 256), (17, 24, 39, 255))
            d = ImageDraw.Draw(img)
            d.ellipse((56, 56, 200, 200), fill=(56, 189, 248, 255))
            # prompt
            d.text((90, 112), ">_", fill=(17, 24, 39, 255))
            return img

        if raw_path:
            # support PyInstaller bundle relative path
            cand = raw_path
            if not os.path.isabs(cand):
                cand = resource_path(raw_path)
            if os.path.isfile(cand):
                try:
                    img = Image.open(cand).convert("RGBA")
                    # For ICO: choose the largest size; for others keep aspect
                    # Scale to nice tray size (~64)
                    img_tray = ImageOps.contain(img, (64, 64))
                    return cand, img_tray
                except Exception as e:
                    self.log.warning("Failed to load icon from '%s': %s. Using fallback.", cand, e)

        # fallback generated icon
        return None, ImageOps.contain(self._create_icon_image(), (64, 64))

    def _create_icon_image(self) -> Image.Image:
        # simple generated icon (used as fallback)
        img = Image.new("RGBA", (256, 256), color=(17, 24, 39, 255))
        d = ImageDraw.Draw(img)
        d.ellipse((56, 56, 200, 200), fill=(56, 189, 248, 255))
        d.text((96, 112), "SSH", fill=(17, 24, 39, 255))
        return img

    # ------------- console & taskbar -------------
    def _maybe_hide_console(self) -> None:
        # hide based on config ui.hide_console (default False)
        try:
            ui = self.cfg.get("ui", {}) if isinstance(self.cfg.get("ui"), dict) else {}
            hide = bool(ui.get("hide_console", False))
            if not hide:
                return
            if os.name == "nt":
                import ctypes
                hwnd = ctypes.windll.kernel32.GetConsoleWindow()
                if hwnd:
                    ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
                    try:
                        ctypes.windll.kernel32.FreeConsole()
                    except Exception:
                        pass
        except Exception:
            pass

    def _set_windows_appid(self, appid: str) -> None:
        if os.name != "nt":
            return
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appid)
        except Exception:
            # non-fatal
            pass

    # ------------- server controls -------------
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

    # ------------- actions -------------
    def open_ui(self, icon=None, item=None):
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
                icon_path=self.icon_path_fs or "",   # <-- pass icon path to Tkinter panel
            )
        self._panel.show()

    def quit(self, icon=None, item=None):
        try:
            self.log.info("Quitting application")
            self.stop_server()
        finally:
            if self._icon:
                self._icon.stop()

    # ------------- tray menu -------------
    def build_menu(self):
        running = self.server.is_running()
        return (
            pystray.MenuItem("Start Server", self.start_server, enabled=not running),
            pystray.MenuItem("Stop Server", self.stop_server, enabled=running),
            pystray.MenuItem("Open Control Panel", self.open_panel, default=True),
            pystray.MenuItem("Open Web UI", self.open_ui),
            pystray.MenuItem("Open API Docs", self.open_api_docs),
            pystray.MenuItem("Exit", self.quit),
        )

    def update_menu(self):
        if self._icon:
            self._icon.menu = pystray.Menu(*self.build_menu())
            self._icon.update_menu()

    # ------------- main loop -------------
    def run(self):
        # Use resolved image for tray (from config or fallback)
        icon_img = self.icon_image
        icon = pystray.Icon(
            "ssh_log_tools",
            icon_img,
            "SSH Log Tools",
            menu=pystray.Menu(*self.build_menu())
        )
        self._icon = icon
        self.log.info("Tray icon initialized; running event loop")
        try:
            ui = self.cfg.get("ui", {})
            if bool(ui.get("show_on_start", False)):
                self.open_panel()
        except Exception:
            pass
        try:
            icon.run()
        finally:
            # ensure the web server thread is stopped when the icon loop exits
            self.stop_server()


if __name__ == "__main__":
    try:
        _lock_fd = acquire_app_lock()
    except SingleInstanceError:
        print("Another instance of SSH Log Tools is already running.")
        sys.exit(1)
    try:
        TrayApp().run()
    finally:
        try:
            os.close(_lock_fd)
        except Exception:
            pass
