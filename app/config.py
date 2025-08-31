import json
import os
import sys
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, List


DEFAULT_CONFIG = {
    "host": "127.0.0.1",
    "port": 5000,
    "logs": [],
    "logging": {
        "enabled": True,
        "path": "logs",
        "filename": "{date}.log",
        "max_bytes": 1048576,  # 1 MiB
        "backup_count": 3,
        "level": "INFO",
        "format": "%(asctime)s %(levelname)s %(name)s: %(message)s",
        "console": True,
        "console_level": "INFO",
    },
    "ui": {
        "show_on_start": False,
        "message": "App is begin!!",
        "title": "SSH Log Tools",
        "icon_path": ""
    },
}


def _resolve_config_path(path: str) -> str | None:
    # Try common locations for config.json
    base = os.path.basename(path)
    candidates = [
        path,
        os.path.abspath(path),
        os.path.join(os.getcwd(), base),
        os.path.join(os.path.dirname(sys.argv[0] or ""), base),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), base),
    ]
    seen = set()
    for p in candidates:
        if not p or p in seen:
            continue
        seen.add(p)
        try:
            if os.path.exists(p):
                return p
        except Exception:
            continue
    return None


def load_config(path: str = "config.json") -> Dict[str, Any]:
    cfg = DEFAULT_CONFIG.copy()
    user_cfg: Dict[str, Any] = {}
    resolved = _resolve_config_path(path)
    if resolved and os.path.exists(resolved):
        try:
            with open(resolved, "r", encoding="utf-8") as f:
                raw = json.load(f)
                if isinstance(raw, dict):
                    user_cfg = raw
        except Exception:
            # If config is malformed, keep defaults
            user_cfg = {}

    # Shallow merge for known top-level keys
    for key in ("host", "port", "logs"):
        if key in user_cfg:
            cfg[key] = user_cfg[key]

    # Deep-merge logging block
    user_log = user_cfg.get("logging") if isinstance(user_cfg.get("logging"), dict) else {}
    merged_log = DEFAULT_CONFIG["logging"].copy()
    merged_log.update(user_log or {})
    cfg["logging"] = merged_log

    # Deep-merge ui block
    user_ui = user_cfg.get("ui") if isinstance(user_cfg.get("ui"), dict) else {}
    merged_ui = DEFAULT_CONFIG.get("ui", {}).copy()
    merged_ui.update(user_ui or {})
    cfg["ui"] = merged_ui
    # Normalize logs
    logs = []
    for item in cfg.get("logs", []) or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("id") or "")
        path = str(item.get("path") or "")
        if not name or not path:
            continue
        logs.append({"name": name, "path": path})
    cfg["logs"] = logs
    return cfg


_LOGGING_CONFIGURED = False


def setup_logging(config: Dict[str, Any]) -> None:
    """Configure application logging based on config.json.

    Uses a RotatingFileHandler with parameters from the "logging" block:
    - path: directory where logs are stored
    - filename: log file name
    - max_bytes: max size per log file before rotation
    - backup_count: number of rotated files to keep
    - level: logging level name (e.g., INFO, DEBUG)
    - format: record format string
    """
    
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return

    # --- 1) พิมพ์ incoming config (สั้น/ชัวร์) ไป STDERR ก่อนตั้ง handler ---
    try:
        print("[setup_logging] incoming config:", file=sys.stderr)
        print(json.dumps(config, indent=2, ensure_ascii=False), file=sys.stderr)
    except Exception:
        # เผื่อ json.dumps พลาดก็ยังบอกชนิดได้
        print(f"[setup_logging] incoming config type={type(config)}", file=sys.stderr)


    log_cfg = (config or {}).get("logging", {}) if isinstance(config, dict) else {}
    enabled = bool(log_cfg.get("enabled", True))
    console_enabled = bool(log_cfg.get("console", True))

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)  # เปิดทางให้ DEBUG ผ่านถึง handler

    if not enabled:
        # Optional console logging when file logging disabled
        if console_enabled:
            has_console = any(
                isinstance(h, logging.StreamHandler)
                and not isinstance(h, logging.FileHandler)
                and getattr(h, "stream", None) in (sys.stdout, sys.stderr)
                for h in root.handlers
            )
            if not has_console:
                ch = logging.StreamHandler()
                # Respect console_level when file logging disabled
                console_level_name = str(log_cfg.get("console_level") or "WARNING").upper()
                console_level = getattr(logging, console_level_name, logging.WARNING)
                ch.setLevel(console_level)
                ch.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
                root.addHandler(ch)
        _LOGGING_CONFIGURED = True

        try:
            summary = {
                "file_logging_enabled": enabled,
                "console_enabled": console_enabled,
                "root_level": logging.getLevelName(root.level),
                "handlers": [
                    {
                        "type": h.__class__.__name__,
                        "level": logging.getLevelName(getattr(h, "level", logging.NOTSET)),
                        "stream": ("stdout" if getattr(h, "stream", None) is sys.stdout else
                                "stderr" if getattr(h, "stream", None) is sys.stderr else None),
                        "baseFilename": getattr(h, "baseFilename", None),
                    }
                    for h in root.handlers
                ],
            }
            print("[setup_logging] effective logging summary:", file=sys.stderr)
            print(json.dumps(summary, indent=2, ensure_ascii=False), file=sys.stderr)
        except Exception:
            pass

        return

    dir_path = str(log_cfg.get("path") or "logs")
    raw_filename = str(log_cfg.get("filename") or "app.log")
    # Support placeholders in filename
    now = datetime.now()
    filename = (
        raw_filename
        .replace("{date}", now.strftime("%Y-%m-%d"))
        .replace("{datetime}", now.strftime("%Y-%m-%d_%H-%M-%S"))
        .replace("{pid}", str(os.getpid()))
    )
    try:
        max_bytes = int(log_cfg.get("max_bytes") or 1048576)
    except Exception:
        max_bytes = 1048576
    try:
        backup_count = int(log_cfg.get("backup_count") or 3)
    except Exception:
        backup_count = 3
    level_name = str(log_cfg.get("level") or "INFO").upper()
    console_level_name = str(log_cfg.get("console_level") or level_name).upper()
    fmt = str(log_cfg.get("format") or "%(asctime)s %(levelname)s %(name)s: %(message)s")

    # Resolve path (relative to CWD)
    dir_abs = os.path.abspath(os.path.join(os.getcwd(), dir_path))
    try:
        os.makedirs(dir_abs, exist_ok=True)
    except Exception:
        # Fallback to current directory if cannot create
        dir_abs = os.path.abspath(os.getcwd())

    file_path = os.path.join(dir_abs, filename)

    # Avoid duplicate handlers if called twice
    exists = False
    for h in root.handlers:
        if isinstance(h, RotatingFileHandler):
            try:
                if getattr(h, "baseFilename", None) == file_path:
                    exists = True
                    break
            except Exception:
                pass

    if not exists:
        fh = RotatingFileHandler(file_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
        # Prefix the rotated filename with the index: e.g., 1-YYYY-MM-DD.log
        def _namer(default_name: str) -> str:
            d, n = os.path.split(default_name)
            base, num = (n.rsplit(".", 1) + [""])[:2]
            if num.isdigit():
                return os.path.join(d, f"{num}-{base}")
            return default_name
        try:
            fh.namer = _namer  # type: ignore[attr-defined]
        except Exception:
            pass
        try:
            level = getattr(logging, level_name, logging.INFO)
        except Exception:
            level = logging.INFO
        fh.setLevel(level)
        fh.setFormatter(logging.Formatter(fmt))
        root.addHandler(fh)

        # Make Flask/Werkzeug loggers propagate to root
        logging.getLogger("werkzeug").setLevel(logging.INFO)
        logging.getLogger("werkzeug").propagate = True
        logging.getLogger("flask.app").propagate = True

    # Add console handler if requested and not already present
    if console_enabled:
        has_console = any(
            isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.FileHandler)
            and getattr(h, "stream", None) in (sys.stdout, sys.stderr)
            for h in root.handlers
        )
        if not has_console:
            ch = logging.StreamHandler()
            try:
                console_level = getattr(logging, console_level_name, logging.WARNING)
            except Exception:
                console_level = logging.WARNING
            ch.setLevel(console_level)
            ch.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
            root.addHandler(ch)

    # Summary log
    try:
        logging.getLogger(__name__).info(
            "Logging configured: file=%s level=%s console=%s console_level=%s",
            file_path,
            level_name,
            console_enabled,
            console_level_name,
        )
        # Reduce Pillow debug noise unless user explicitly wants DEBUG
        try:
            pil_log = logging.getLogger("PIL")
            if pil_log.level == logging.NOTSET:
                pil_log.setLevel(logging.WARNING)
        except Exception:
            pass
    except Exception:
        pass

    _LOGGING_CONFIGURED = True


def get_log_by_name(config: Dict[str, Any], name: str) -> Dict[str, str] | None:
    for item in config.get("logs", []):
        if item.get("name") == name:
            return item
    return None
