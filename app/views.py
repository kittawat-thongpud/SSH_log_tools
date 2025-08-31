from flask import Blueprint, render_template, send_file, abort
from .config import load_config
from .db import get_images_dir


bp = Blueprint("views", __name__)


def _client_cfg():
    cfg = load_config()
    api = cfg.get("api") if isinstance(cfg.get("api"), dict) else {}
    try:
        timeout_ms = int(api.get("client_timeout_ms", 30000))
    except Exception:
        timeout_ms = 30000
    # Debug flag from UI config (default True for troubleshooting)
    ui = cfg.get("ui") if isinstance(cfg.get("ui"), dict) else {}
    debug = bool(ui.get("debug", True))
    return {"apiTimeoutMs": timeout_ms, "debug": debug}


def _sanitize_rel_path(p: str) -> str:
    import re
    raw = (p or "").replace("\\", "/").strip().lstrip("/")
    parts = [seg for seg in raw.split("/") if seg and seg != "." and seg != ".."]
    safe = []
    for seg in parts:
        seg = re.sub(r"[^A-Za-z0-9_.-]", "_", seg).strip("._") or "_"
        safe.append(seg)
    return "/".join(safe)


@bp.get("/")
def index():
    return render_template("index.html", app_cfg=_client_cfg())


@bp.get("/profiles")
def profiles_page():
    return render_template("profiles.html", app_cfg=_client_cfg())


@bp.get("/records")
def records_page():
    return render_template("records.html", app_cfg=_client_cfg())


@bp.get("/media/<path:subpath>")
def media_file(subpath: str):
    base = get_images_dir()
    rel = _sanitize_rel_path(subpath)
    import os
    abs_path = os.path.join(base, rel)
    if not os.path.isfile(abs_path):
        abort(404)
    return send_file(abs_path, as_attachment=False)
