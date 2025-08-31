import os
import sys
import threading
import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable


class ControlPanel:
    """Modern card-style Tkinter control panel.

    - Light theme, fills window (no card border)
    - Centered header and status with colored dot
    - Responsive button grid that wraps to next row
    - Author at the bottom with clickable email
    - NEW: Supports window/taskbar icon via icon_path (.ico on Windows, PNG/ICO on others)
    """

    def __init__(self,
                 title: str,
                 message: str,
                 author_name: Optional[str],
                 author_email: Optional[str],
                 get_status: Callable[[], bool],
                 on_start: Callable[[], None],
                 on_stop: Callable[[], None],
                 on_open_ui: Callable[[], None],
                 on_open_docs: Callable[[], None],
                 on_exit: Callable[[], None],
                 icon_path: str = ""):   # ← NEW
        self._title = title or "App Control Panel"
        self._message = message or ""
        self._author_name = author_name or ""
        self._author_email = author_email or ""
        self._get_status = get_status
        self._on_start = on_start
        self._on_stop = on_stop
        self._on_open_ui = on_open_ui
        self._on_open_docs = on_open_docs
        self._on_exit = on_exit
        self._icon_path = (icon_path or "").strip()  # ← NEW

        self._thread: Optional[threading.Thread] = None
        self._root: Optional[tk.Tk] = None
        self._status_var: Optional[tk.StringVar] = None

        # cache for Tk PhotoImage to prevent GC
        self._tk_icon_img = None

    def show(self) -> None:
        if self._root is not None:
            try:
                self._root.after(0, self._raise)
                return
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _raise(self) -> None:
        if not self._root:
            return
        try:
            self._root.deiconify()
            self._root.lift()
            self._root.focus_force()
        except Exception:
            pass

    # ---------- helpers ----------
    @staticmethod
    def _resource_path(rel_path: str) -> str:
        """Support dev & PyInstaller onefile path resolution."""
        base = getattr(sys, "_MEIPASS", os.path.abspath("."))
        return os.path.join(base, rel_path)

    def _apply_window_icon(self, root: tk.Tk) -> None:
        """Apply window/taskbar icon using self._icon_path.
        - On Windows: prefer .ico via iconbitmap()
        - On others: PNG/ICO via iconphoto()
        Fallback: silently skip if missing/invalid.
        """
        path = self._icon_path
        if not path:
            return

        # resolve relative path for PyInstaller onefile
        if not os.path.isabs(path):
            path = self._resource_path(path)

        if not os.path.isfile(path):
            return

        try:
            ws = root.tk.call('tk', 'windowingsystem')
        except Exception:
            ws = ''

        try:
            # Windows: iconbitmap requires .ico
            if os.name == "nt":
                if path.lower().endswith(".ico"):
                    root.iconbitmap(path)  # taskbar/titlebar icon
                else:
                    # Non-ico on Windows → use iconphoto (won't affect taskbar in some cases)
                    self._tk_icon_img = tk.PhotoImage(file=path)
                    root.iconphoto(True, self._tk_icon_img)
            else:
                # macOS/Linux → PNG/ICO via iconphoto
                self._tk_icon_img = tk.PhotoImage(file=path)
                root.iconphoto(True, self._tk_icon_img)
        except Exception:
            # icon is optional; ignore errors
            pass

    def _run(self) -> None:
        self._root = tk.Tk()
        root = self._root
        root.title(self._title)
        try:
            # small quality-of-life scaling for HiDPI on Windows
            if os.name == "nt":
                root.tk.call('tk', 'scaling', 1.25)
        except Exception:
            pass

        # apply window icon (title bar / taskbar)
        self._apply_window_icon(root)

        try:
            root.geometry("520x320")
            root.resizable(True, False)
        except Exception:
            pass

        # Hint the OS to not show a taskbar button for this window (tray-only UX)
        try:
            ws = root.tk.call('tk', 'windowingsystem')
            if ws == 'win32':
                try:
                    import ctypes
                    hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
                    GWL_EXSTYLE = -20
                    WS_EX_TOOLWINDOW = 0x00000080
                    WS_EX_APPWINDOW = 0x00040000
                    style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                    style = (style | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW
                    ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
                    SWP_NOMOVE = 0x0002; SWP_NOSIZE = 0x0001; SWP_FRAMECHANGED = 0x0020
                    ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_FRAMECHANGED)
                except Exception:
                    try:
                        root.wm_attributes('-toolwindow', True)
                    except Exception:
                        pass
            elif ws == 'x11':
                try:
                    root.wm_attributes('-type', 'splash')
                except Exception:
                    pass
        except Exception:
            pass

        # Colors
        BG = "#F3F4F6"       # background
        TEXT = "#111827"     # primary text
        MUTED = "#6B7280"    # muted text
        PRIMARY = "#2563EB"  # open web ui
        SUCCESS = "#16A34A"  # start
        DANGER = "#DC2626"   # stop
        INFO = "#0EA5E9"     # docs
        DARK = "#374151"     # exit

        root.configure(bg=BG)

        body = tk.Frame(root, bg=BG)
        body.pack(fill=tk.BOTH, expand=True, padx=14, pady=14)

        # Header (centered)
        tk.Label(body, text=self._title, font=("Helvetica", 16, "bold"),
                 bg=BG, fg=TEXT, justify="center").pack(fill=tk.X)
        if self._message:
            tk.Label(body, text=self._message, bg=BG, fg=MUTED,
                     font=("Helvetica", 11), justify="center").pack(fill=tk.X, pady=(2, 12))

        # Status centered with dot
        status_row = tk.Frame(body, bg=BG)
        status_row.pack()
        tk.Label(status_row, text="Status:", bg=BG, fg=TEXT,
                 font=("Helvetica", 11, "bold")).pack(side=tk.LEFT)
        dot = tk.Canvas(status_row, width=10, height=10, highlightthickness=0, bg=BG)
        dot.pack(side=tk.LEFT, padx=(8, 6))
        self._status_var = tk.StringVar(value="Unknown")
        tk.Label(status_row, textvariable=self._status_var, bg=BG, fg=TEXT,
                 font=("Helvetica", 11)).pack(side=tk.LEFT)

        # Buttons grid (responsive)
        btns = tk.Frame(body, bg=BG)
        btns.pack(fill=tk.X, pady=(12, 14))

        def mkbtn(text, cmd, bg, fg="#FFFFFF"):
            return tk.Button(
                btns, text=text, command=cmd,
                bg=bg, fg=fg, activebackground=bg, activeforeground=fg,
                bd=0, padx=12, pady=8, font=("Helvetica", 10, "bold")
            )

        btn_list = [
            mkbtn("Start", self._on_start, SUCCESS),
            mkbtn("Stop", self._on_stop, DANGER),
            mkbtn("Open Web UI", self._on_open_ui, PRIMARY),
            mkbtn("Open API Docs", self._on_open_docs, INFO),
            mkbtn("Exit", self._on_exit, DARK),
        ]

        # layout buttons responsively based on available width
        _pending = {"after": None}

        def layout_buttons():
            for w in btn_list:
                w.grid_forget()
            w = btns.winfo_width() or root.winfo_width() or 520
            min_cell = 140
            cols = max(1, w // min_cell)
            for i in range(cols):
                btns.grid_columnconfigure(i, weight=1, uniform="btns")
            for idx, b in enumerate(btn_list):
                r = idx // cols
                c = idx % cols
                b.grid(row=r, column=c, sticky="ew", padx=6, pady=6)

        def on_resize(_e=None):
            if _pending["after"]:
                try:
                    root.after_cancel(_pending["after"])  # type: ignore[arg-type]
                except Exception:
                    pass
            _pending["after"] = root.after(50, layout_buttons)

        layout_buttons()
        root.bind("<Configure>", on_resize)

        # Spacer
        tk.Frame(body, bg=BG).pack(fill=tk.BOTH, expand=True)

        # Author footer centered
        if self._author_name or self._author_email:
            a = tk.Frame(body, bg=BG)
            a.pack(fill=tk.X)
            tk.Label(a, text="Author:", bg=BG, fg=MUTED, font=("Helvetica", 10)).pack(side=tk.LEFT)
            import webbrowser as _wb
            if self._author_name:
                tk.Label(a, text=f"  {self._author_name}  ", bg=BG, fg=TEXT,
                         font=("Helvetica", 10, "bold")).pack(side=tk.LEFT)
            if self._author_email:
                link = tk.Label(a, text=self._author_email, bg=BG, fg=PRIMARY,
                                font=("Helvetica", 10, "underline"), cursor="hand2")
                link.bind("<Button-1>", lambda e: _wb.open(f"mailto:{self._author_email}"))
                link.pack(side=tk.LEFT)

        # Periodic status update
        def tick():
            try:
                running = bool(self._get_status())
                if self._status_var is not None:
                    self._status_var.set("Running" if running else "Stopped")
                try:
                    dot.delete("all")
                    color = "#16A34A" if running else "#DC2626"
                    dot.create_oval(0, 0, 10, 10, fill=color, outline=color)
                except Exception:
                    pass
            finally:
                try:
                    root.after(800, tick)
                except Exception:
                    pass
        tick()

        # Hide instead of destroy
        def on_close():
            try:
                root.withdraw()
            except Exception:
                pass
        root.protocol("WM_DELETE_WINDOW", on_close)

        try:
            root.mainloop()
        finally:
            self._root = None
