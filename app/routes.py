import os
import re
import time
import logging
import sqlite3
import json
from typing import List, Dict, Any, Optional
from flask import Blueprint, jsonify, request, send_file, abort, Response
from .config import load_config, get_log_by_name
from .db import get_db, row_to_dict, get_images_dir


bp = Blueprint("api", __name__, url_prefix="/api")
_log = logging.getLogger(__name__)


def _file_info(path: str) -> Dict[str, Any]:
    try:
        st = os.stat(path)
        return {
            "exists": True,
            "size": st.st_size,
            "mtime": int(st.st_mtime),
        }
    except FileNotFoundError:
        return {"exists": False, "size": 0, "mtime": 0}


@bp.get("/logs")
def list_logs():
    cfg = load_config()
    logs = []
    for item in cfg.get("logs", []):
        info = _file_info(item["path"])
        logs.append({
            "name": item["name"],
            "path": item["path"],
            **info,
        })
    _log.info("Listing logs: %d entries", len(logs))
    return jsonify({
        "host": cfg.get("host", "127.0.0.1"),
        "port": cfg.get("port", 5000),
        "logs": logs,
        "ts": int(time.time()),
    })


def _get_ssh_timeout() -> int:
    try:
        cfg = load_config()
        api_cfg = cfg.get("api") if isinstance(cfg.get("api"), dict) else {}
        return int(api_cfg.get("ssh_timeout", 15))
    except Exception:
        return 15


# ------------------ Path Type Inference ------------------
IMG_EXTS = [
    "jpg", "jpeg", "png", "gif", "bmp", "webp", "svg", "ico", "tif", "tiff"
]
TXT_EXTS = ["log", "txt", "md"]


def _infer_path_type(pattern: str) -> str:
    p = (pattern or "").lower()
    # Heuristic: if any known image/text extension appears explicitly, use it
    for ext in IMG_EXTS:
        if f"*.{ext}" in p or p.endswith(f".{ext}") or f".{ext}" in p:
            return "image"
    for ext in TXT_EXTS:
        if f"*.{ext}" in p or p.endswith(f".{ext}") or f".{ext}" in p:
            return "text"
    return "text"


def _split_path_and_chain(raw: str) -> tuple[str, List[str]]:
    """Split a registered path on '| grep' segments.

    Returns the base path and a list of grep patterns. Non-grep segments
    are ignored for safety.
    """
    if not raw:
        return "", []
    parts = [p.strip() for p in raw.split("|")]
    base = parts[0]
    chain: List[str] = []
    for seg in parts[1:]:
        seg = seg.strip()
        if seg.lower().startswith("grep"):
            pat = seg[4:].strip()
            if pat:
                chain.append(pat)
    return base, chain


def _tail_lines(path: str, lines: int = 200, encoding: str = "utf-8") -> List[str]:
    # Efficient tail implementation
    if lines <= 0:
        return []
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            end = f.tell()
            block = 1024
            data = b""
            line_count = 0
            while end > 0 and line_count <= lines:
                size = min(block, end)
                end -= size
                f.seek(end)
                chunk = f.read(size)
                data = chunk + data
                line_count = data.count(b"\n")
            text = data.decode(encoding, errors="replace")
            result = text.splitlines()[-lines:]
            return result
    except FileNotFoundError:
        return []


@bp.get("/logs/<name>/tail")
def tail_log(name: str):
    cfg = load_config()
    log = get_log_by_name(cfg, name)
    if not log:
        _log.warning("Tail request for unknown log: %s", name)
        abort(404)
    lines = int(request.args.get("lines", 200))
    result = _tail_lines(log["path"], lines=lines)
    _log.info("Tail %s: %d lines", name, len(result))
    return jsonify({"name": name, "lines": result})


@bp.get("/logs/<name>/download")
def download_log(name: str):
    cfg = load_config()
    log = get_log_by_name(cfg, name)
    if not log:
        _log.warning("Download request for unknown log: %s", name)
        abort(404)
    path = log["path"]
    if not os.path.exists(path):
        _log.warning("Download request for missing file: %s -> %s", name, path)
        abort(404)
    _log.info("Download %s from %s", name, path)
    return send_file(path, as_attachment=True)


@bp.get("/logs/<name>/search")
def search_log(name: str):
    cfg = load_config()
    log = get_log_by_name(cfg, name)
    if not log:
        _log.warning("Search request for unknown log: %s", name)
        abort(404)
    q = request.args.get("q", "")
    use_regex = request.args.get("regex", "0") == "1"
    case_sensitive = request.args.get("case", "0") == "1"
    context = int(request.args.get("context", 0))
    limit = int(request.args.get("limit", 5000))
    path = log["path"]
    flags = 0 if case_sensitive else re.IGNORECASE

    matcher = None
    if q:
        if use_regex:
            try:
                matcher = re.compile(q, flags)
            except re.error:
                matcher = None
        else:
            # simple substring search later
            pass

    results: List[Dict[str, Any]] = []
    if not os.path.exists(path):
        return jsonify({"name": name, "matches": results, "truncated": False})

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            buf: List[str] = []
            idx = 0
            for raw_line in f:
                line = raw_line.rstrip("\n")
                matched = False
                if not q:
                    matched = True
                elif matcher is not None:
                    matched = matcher.search(line) is not None
                else:
                    cmp_a = line if case_sensitive else line.lower()
                    cmp_b = q if case_sensitive else q.lower()
                    matched = cmp_b in cmp_a

                buf.append(line)
                if matched:
                    start = max(0, len(buf) - 1 - context)
                    context_block = buf[start:]
                    results.append({
                        "line": idx + 1,
                        "text": line,
                        "context_before": context_block[:-1] if context > 0 else [],
                    })
                    if len(results) >= limit:
                        break
                if len(buf) > context + 1:
                    buf.pop(0)
                idx += 1
    except Exception:
        pass

    truncated = len(results) >= limit
    _log.info(
        "Search %s: query=%r regex=%s case=%s context=%d limit=%d results=%d truncated=%s",
        name,
        q,
        use_regex,
        case_sensitive,
        context,
        limit,
        len(results),
        truncated,
    )
    return jsonify({"name": name, "matches": results, "truncated": truncated})


# ------------------ Profiles & Remote Access ------------------

def _get_profile(pid: int) -> Optional[Dict[str, Any]]:
    conn = get_db()
    cur = conn.execute("SELECT * FROM profiles WHERE id=?", (pid,))
    row = cur.fetchone()
    conn.close()
    return row_to_dict(row) if row else None


def _list_paths(pid: int) -> List[Dict[str, Any]]:
    conn = get_db()
    cur = conn.execute("SELECT id, path, grep_chain, type, created_at FROM profile_paths WHERE profile_id=? ORDER BY id DESC", (pid,))
    rows: List[Dict[str, Any]] = []
    for r in cur.fetchall():
        item = row_to_dict(r)
        chain_raw = item.get("grep_chain")
        chain: List[str] = []
        if chain_raw:
            try:
                chain = json.loads(chain_raw)
                if not isinstance(chain, list):
                    chain = []
            except Exception:
                chain = []
        item["grep_chain"] = chain
        # Infer type automatically unless explicitly stored as image
        stored_t = (item.get("type") or "").lower()
        inferred_t = _infer_path_type(item.get("path") or "")
        item["type"] = "image" if stored_t == "image" else inferred_t
        rows.append(item)
    conn.close()
    return rows


@bp.post("/profiles")
def create_profile():
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    host = (data.get("host") or "").strip()
    protocol = (data.get("protocol") or "ssh").strip().lower()
    port = int(data.get("port") or (22 if protocol == "ssh" else 21))
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    if not name or not host:
        return jsonify({"error": "name and host are required"}), 400
    ts = int(time.time())
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO profiles(name, protocol, host, port, username, password, created_at) VALUES(?,?,?,?,?,?,?)",
            (name, protocol, host, port, username, password, ts),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "profile name already exists"}), 409
    cur = conn.execute("SELECT * FROM profiles WHERE name=?", (name,))
    row = cur.fetchone()
    conn.close()
    return jsonify(row_to_dict(row)), 201


@bp.get("/profiles")
def list_profiles():
    conn = get_db()
    cur = conn.execute("SELECT * FROM profiles ORDER BY id DESC")
    rows = [row_to_dict(r) for r in cur.fetchall()]
    for r in rows:
        r["paths"] = _list_paths(r["id"]) if r else []
    conn.close()
    return jsonify({"profiles": rows})


@bp.put("/profiles/<int:pid>")
def update_profile(pid: int):
    data = request.get_json(force=True, silent=True) or {}
    fields = {}
    for key in ("name", "protocol", "host", "port", "username", "password"):
        if key in data:
            fields[key] = data[key]
    if not fields:
        return jsonify({"error": "no fields"}), 400
    if "protocol" in fields:
        fields["protocol"] = str(fields["protocol"]).lower()
    if "port" in fields:
        try:
            fields["port"] = int(fields["port"])
        except Exception:
            return jsonify({"error": "invalid port"}), 400
    sets = ",".join([f"{k}=?" for k in fields.keys()])
    vals = list(fields.values())
    vals.append(pid)
    conn = get_db()
    try:
        cur = conn.execute(f"UPDATE profiles SET {sets} WHERE id=?", vals)
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "profile name already exists"}), 409
    row = conn.execute("SELECT * FROM profiles WHERE id=?", (pid,)).fetchone()
    conn.close()
    if not row:
        abort(404)
    result = row_to_dict(row)
    result["paths"] = _list_paths(pid)
    return jsonify(result)


@bp.delete("/profiles/<int:pid>")
def delete_profile(pid: int):
    conn = get_db()
    cur = conn.execute("DELETE FROM profiles WHERE id=?", (pid,))
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    return jsonify({"ok": deleted > 0, "deleted": deleted})


@bp.get("/profiles/<int:pid>/paths")
def list_profile_paths(pid: int):
    prof = _get_profile(pid)
    if not prof:
        abort(404)
    return jsonify({"paths": _list_paths(pid)})


@bp.put("/profile_paths/<int:ppid>")
def update_profile_path(ppid: int):
    data = request.get_json(force=True, silent=True) or {}
    sets: List[str] = []
    vals: List[Any] = []
    if "path" in data:
        raw_path = (data.get("path") or "").strip()
        base, auto_chain = _split_path_and_chain(raw_path)
        if not base:
            return jsonify({"error": "path required"}), 400
        sets.append("path=?"); vals.append(base)
        # If type not explicitly provided, re-infer from base path
        if "type" not in data:
            inferred = _infer_path_type(base)
            sets.append("type=?"); vals.append(inferred)
        gc = data.get("grep_chain")
        if gc is None:
            chain = auto_chain
        else:
            if isinstance(gc, list):
                chain = [s for s in gc if s]
            elif isinstance(gc, str):
                chain = [s for s in gc.split(",") if s]
            else:
                chain = []
            chain.extend(auto_chain)
        sets.append("grep_chain=?"); vals.append(json.dumps(chain))
    elif "grep_chain" in data:
        gc = data.get("grep_chain")
        if isinstance(gc, list):
            chain = [s for s in gc if s]
        elif isinstance(gc, str):
            chain = [s for s in gc.split(",") if s]
        else:
            chain = []
        sets.append("grep_chain=?"); vals.append(json.dumps(chain))
    if "type" in data:
        t_raw = data.get("type")
        t = str(t_raw or "").lower().strip()
        if t == "auto":
            # infer using new_path if provided, otherwise fetch current path from DB
            path_for_infer = None
            if "path" in data:
                path_for_infer = (data.get("path") or "").strip()
            if not path_for_infer:
                try:
                    conn2 = get_db()
                    row = conn2.execute("SELECT path FROM profile_paths WHERE id=?", (ppid,)).fetchone()
                    conn2.close()
                    path_for_infer = row["path"] if row else ""
                except Exception:
                    path_for_infer = ""
            t = _infer_path_type(path_for_infer)
        if t not in ("text", "image"):
            t = "text"
        sets.append("type=?"); vals.append(t)
    if not sets:
        return jsonify({"error": "no fields"}), 400
    conn = get_db()
    cur = conn.execute(f"UPDATE profile_paths SET {', '.join(sets)} WHERE id=?", (*vals, ppid))
    conn.commit()
    updated = cur.rowcount
    conn.close()
    return jsonify({"ok": updated > 0, "updated": updated})


@bp.delete("/profile_paths/<int:ppid>")
def delete_profile_path(ppid: int):
    conn = get_db()
    cur = conn.execute("DELETE FROM profile_paths WHERE id=?", (ppid,))
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    return jsonify({"ok": deleted > 0, "deleted": deleted})


@bp.post("/profiles/<int:pid>/paths")
def add_profile_path(pid: int):
    prof = _get_profile(pid)
    if not prof:
        abort(404)
    data = request.get_json(force=True, silent=True) or {}
    raw_path = (data.get("path") or "").strip()
    base, auto_chain = _split_path_and_chain(raw_path)
    extra = data.get("grep_chain")
    if isinstance(extra, list):
        chain = [s for s in extra if s] + auto_chain
    elif isinstance(extra, str):
        chain = [s for s in extra.split(",") if s] + auto_chain
    else:
        chain = auto_chain
    raw_t = data.get("type")
    t = str(raw_t or "").lower().strip() if isinstance(raw_t, str) else None
    if not t or t == "auto":
        t = _infer_path_type(base)
    if t not in ("text", "image"):
        t = "text"
    gc_s = json.dumps(chain)
    if not base:
        return jsonify({"error": "path required"}), 400
    ts = int(time.time())
    conn = get_db()
    conn.execute(
        "INSERT INTO profile_paths(profile_id, path, grep_chain, type, created_at) VALUES(?,?,?,?,?)",
        (pid, base, gc_s, t, ts),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


def _ssh_exec(prof: Dict[str, Any], command: str, timeout: int = 15) -> Dict[str, Any]:
    try:
        import paramiko
    except Exception as e:
        return {"ok": False, "error": f"paramiko not available: {e}"}
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=prof["host"],
            port=int(prof.get("port") or 22),
            username=prof.get("username") or None,
            password=prof.get("password") or None,
            timeout=timeout,
            look_for_keys=False,
            allow_agent=False,
        )
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        code = stdout.channel.recv_exit_status()
        client.close()
        return {"ok": code == 0, "out": out, "err": err, "code": code}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@bp.get("/profiles/<int:pid>/cat")
def ssh_cat(pid: int):
    prof = _get_profile(pid)
    if not prof:
        abort(404)
    if (prof.get("protocol") or "ssh").lower() != "ssh":
        return jsonify({"error": "profile is not SSH"}), 400
    pattern = request.args.get("pattern", "")
    # Ignore any pipeline appended in the registered path (e.g., "| grep ...")
    if "|" in pattern:
        pattern = pattern.split("|", 1)[0].strip()
    # Support multiple grep parameters for chained filtering
    greps = request.args.getlist("grep")
    if not greps:
        chain = request.args.get("grep_chain", "")
        if chain:
            greps = [s for s in chain.split(",") if s]
    # Max lines (tail last N)
    try:
        max_lines = int(request.args.get("lines", 200))
    except Exception:
        max_lines = 200
    if max_lines < 1:
        max_lines = 1
    if max_lines > 5000:
        max_lines = 5000
    if not pattern:
        return jsonify({"error": "pattern required"}), 400
    # Build safe shell command using bash -lc so globbing works. Pattern left unquoted to expand.
    # Grep argument is safely single-quoted (with proper escaping of single quotes).
    def sh_q(s: str) -> str:
        return "'" + s.replace("'", "'\"'\"'") + "'"

    # Use tail to limit to the last N lines
    cmd_inner = f"tail -n {max_lines} -- {pattern}"
    for g in greps:
        cmd_inner += f" | grep -F -- {sh_q(g)}"
    cmd = f"bash -lc {sh_q(cmd_inner)}"
    res = _ssh_exec(prof, cmd, timeout=_get_ssh_timeout())
    if not res.get("ok"):
        return jsonify({"error": res.get("error") or res.get("err") or "ssh error"}), 502
    # Return capped lines to avoid overload (safety cap remains 5000)
    lines = (res.get("out") or "").splitlines()
    if len(lines) > 5000:
        lines = lines[:5000]
    return jsonify({"pattern": pattern, "grep": greps, "lines": lines})


@bp.get("/profiles/<int:pid>/ping")
def ssh_ping(pid: int):
    prof = _get_profile(pid)
    if not prof:
        abort(404)
    if (prof.get("protocol") or "ssh").lower() != "ssh":
        return jsonify({"ok": False, "error": "profile is not SSH"})
    # Execute a no-op command to verify connectivity
    res = _ssh_exec(prof, "bash -lc 'true'", timeout=_get_ssh_timeout())
    ok = bool(res.get("ok"))
    err = res.get("error") or res.get("err") or (None if ok else "unknown error")
    return jsonify({"ok": ok, "error": err})


@bp.get("/profiles/<int:pid>/ftp/list")
def ftp_list(pid: int):
    prof = _get_profile(pid)
    if not prof:
        abort(404)
    if (prof.get("protocol") or "ssh").lower() != "ftp":
        return jsonify({"error": "profile is not FTP"}), 400
    base = request.args.get("path", "/")
    try:
        from ftplib import FTP
        ftp = FTP()
        ftp.connect(prof["host"], int(prof.get("port") or 21), timeout=10)
        ftp.login(prof.get("username") or "anonymous", prof.get("password") or "")
        ftp.cwd(base)
        items: List[Dict[str, Any]] = []
        ftp.retrlines("LIST", lambda line: items.append({"raw": line}))
        ftp.quit()
        return jsonify({"path": base, "items": items})
    except Exception as e:
        return jsonify({"error": str(e)}), 502


# ------------------ Records & Images ------------------

@bp.post("/records")
def create_record():
    data = request.get_json(force=True, silent=True) or {}
    profile_id = data.get("profile_id")
    title = (data.get("title") or "").strip()
    file_path = (data.get("file_path") or "").strip()
    flt = (data.get("filter") or "").strip()
    content = data.get("content") or ""
    situation = (data.get("situation") or "").strip()
    event_time = data.get("event_time")
    try:
        event_time = int(event_time) if event_time is not None else None
    except Exception:
        event_time = None
    description = (data.get("description") or "").strip()
    ts = int(time.time())
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO records(profile_id, title, file_path, filter, content, situation, event_time, description, created_at) VALUES(?,?,?,?,?,?,?,?,?)",
        (profile_id, title, file_path, flt, content, situation, event_time, description, ts),
    )
    rid = cur.lastrowid
    conn.commit()
    cur = conn.execute("SELECT * FROM records WHERE id=?", (rid,))
    row = cur.fetchone()
    conn.close()
    return jsonify(row_to_dict(row)), 201


@bp.get("/records")
def list_records():
    conn = get_db()
    rows = [row_to_dict(r) for r in conn.execute("SELECT * FROM records ORDER BY id DESC").fetchall()]
    # attach images
    for r in rows:
        imgs = []
        for x in conn.execute("SELECT id, path, created_at FROM record_images WHERE record_id=? ORDER BY id DESC", (r["id"],)).fetchall():
            di = row_to_dict(x)
            p = di.get("path") or ""
            di["url"] = _public_image_url(p) if p else None
            imgs.append(di)
        r["images"] = imgs
    conn.close()
    return jsonify({"records": rows})


@bp.get("/media/<path:subpath>")
def media_file(subpath: str):
    # Only serve files under data/images
    base = get_images_dir()
    safe_rel = _sanitize_rel_path(subpath)
    abs_path = os.path.join(base, safe_rel)
    if not os.path.isfile(abs_path):
        abort(404)
    return send_file(abs_path, as_attachment=False)


@bp.get("/profiles/<int:pid>/image")
def ssh_image_preview(pid: int):
    """Fetch remote image bytes for preview; caches in memory (no DB write)."""
    prof = _get_profile(pid)
    if not prof:
        abort(404)
    if (prof.get("protocol") or "ssh").lower() != "ssh":
        return jsonify({"error": "profile is not SSH"}), 400
    rpath = (request.args.get("path") or "").strip()
    if "|" in rpath:
        rpath = rpath.split("|", 1)[0].strip()
    if not rpath:
        return jsonify({"error": "path required"}), 400
    content = _image_cache_get(int(pid), rpath)
    if content is None:
        try:
            import paramiko
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                hostname=prof["host"],
                port=int(prof.get("port") or 22),
                username=prof.get("username") or None,
                password=prof.get("password") or None,
                timeout=_get_ssh_timeout(),
                look_for_keys=False,
                allow_agent=False,
            )
            sftp = client.open_sftp()
            with sftp.open(rpath, "rb") as f:
                content = f.read()
            sftp.close(); client.close()
            if content:
                _image_cache_put(int(pid), rpath, content)
        except Exception as e:
            return jsonify({"error": str(e)}), 502
    if not content:
        abort(404)
    import mimetypes
    ctype = mimetypes.guess_type(rpath)[0] or "application/octet-stream"
    return Response(content, mimetype=ctype)


@bp.put("/records/<int:rid>")
def update_record(rid: int):
    data = request.get_json(force=True, silent=True) or {}
    fields = {}
    for key in ("title", "file_path", "filter", "content", "situation", "event_time", "description"):
        if key in data:
            fields[key] = data[key]
    if not fields:
        return jsonify({"error": "no fields"}), 400
    if "event_time" in fields:
        try:
            fields["event_time"] = int(fields["event_time"]) if fields["event_time"] is not None else None
        except Exception:
            fields["event_time"] = None
    sets = ",".join([f"{k}=?" for k in fields.keys()])
    vals = list(fields.values())
    vals.append(rid)
    conn = get_db()
    cur = conn.execute(f"UPDATE records SET {sets} WHERE id=?", vals)
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    return jsonify({"ok": ok})


@bp.delete("/records/<int:rid>")
def delete_record(rid: int):
    conn = get_db()
    # Gather image paths before deleting links
    img_rows = conn.execute("SELECT path FROM record_images WHERE record_id=?", (rid,)).fetchall()
    paths = [r["path"] for r in img_rows]
    # Remove links for this record
    conn.execute("DELETE FROM record_images WHERE record_id=?", (rid,))
    # Clean up orphaned files (no other links reference the same path)
    try:
        for p in paths:
            cnt_row = conn.execute("SELECT COUNT(1) FROM record_images WHERE path=?", (p,)).fetchone()
            cnt = cnt_row[0] if cnt_row is not None else 1
            if cnt == 0 and p:
                abs_path = p if os.path.isabs(p) else os.path.join(get_images_dir(), p)
                if os.path.exists(abs_path):
                    try:
                        os.remove(abs_path)
                    except Exception:
                        pass
    except Exception:
        pass
    # Finally delete the record
    cur = conn.execute("DELETE FROM records WHERE id=?", (rid,))
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    return jsonify({"ok": deleted > 0, "deleted": deleted})


def _secure_filename(name: str) -> str:
    import re as _re
    name = _re.sub(r"[^A-Za-z0-9_.-]", "_", name)
    return name.strip("._") or "file"


def _sanitize_rel_path(p: str) -> str:
    # Break by both separators and sanitize each component
    raw = p.replace("\\", "/").strip().lstrip("/")
    parts = [seg for seg in raw.split("/") if seg and seg != "." and seg != ".."]
    safe_parts = [_secure_filename(seg) for seg in parts]
    return "/".join(safe_parts)


def _public_image_url(rel_path: str) -> str:
    rel = rel_path.replace("\\", "/").lstrip("/")
    return f"/media/{rel}"


@bp.post("/records/<int:rid>/image")
def upload_record_image(rid: int):
    # expects form-data with 'file'
    conn = get_db()
    r = conn.execute("SELECT * FROM records WHERE id=?", (rid,)).fetchone()
    if not r:
        conn.close()
        abort(404)
    prof_name = None
    if r["profile_id"]:
        p = conn.execute("SELECT name FROM profiles WHERE id=?", (r["profile_id"],)).fetchone()
        if p:
            prof_name = p["name"]
    conn.close()

    f = request.files.get("file")
    if not f:
        return jsonify({"error": "file required"}), 400
    base = get_images_dir()
    reg_base = r["file_path"] or ""
    reg_dir = _sanitize_rel_path(os.path.dirname(reg_base)) if reg_base else ""
    folder = os.path.join(base, _secure_filename(prof_name or "_"), reg_dir)
    os.makedirs(folder, exist_ok=True)
    fname = _secure_filename(f.filename or f"img_{int(time.time())}.png")
    abs_path = os.path.join(folder, fname)
    f.save(abs_path)
    rel_path = os.path.relpath(abs_path, base).replace("\\", "/")
    conn = get_db()
    ts = int(time.time())
    conn.execute("INSERT INTO record_images(record_id, path, created_at) VALUES(?,?,?)", (rid, rel_path, ts))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "path": rel_path, "url": _public_image_url(rel_path)})


@bp.post("/records/<int:rid>/image_remote")
def upload_record_image_remote(rid: int):
    data = request.get_json(force=True, silent=True) or {}
    pid = data.get("profile_id")
    rpath = (data.get("path") or "").strip()
    if not pid or not rpath:
        return jsonify({"error": "profile_id and path required"}), 400
    prof = _get_profile(int(pid))
    if not prof:
        abort(404)
    # fetch data from cache or via SFTP
    content = _image_cache_get(int(pid), rpath)
    if content is None:
        try:
            import paramiko
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                hostname=prof["host"],
                port=int(prof.get("port") or 22),
                username=prof.get("username") or None,
                password=prof.get("password") or None,
                timeout=_get_ssh_timeout(),
                look_for_keys=False,
                allow_agent=False,
            )
            sftp = client.open_sftp()
            with sftp.open(rpath, "rb") as f:
                content = f.read()
            sftp.close()
            client.close()
            if content is None:
                return jsonify({"error": "empty file"}), 502
            if len(content) > 10 * 1024 * 1024:
                return jsonify({"error": "file too large"}), 413
            _image_cache_put(int(pid), rpath, content)
        except Exception as e:
            return jsonify({"error": str(e)}), 502
    # persist to disk and DB
    conn = get_db()
    row = conn.execute("SELECT * FROM records WHERE id=?", (rid,)).fetchone()
    if not row:
        conn.close(); abort(404)
    prof_name = None
    if row["profile_id"]:
        p = conn.execute("SELECT name FROM profiles WHERE id=?", (row["profile_id"],)).fetchone()
        if p:
            prof_name = p["name"]
    images_base = get_images_dir()
    reg_base = row.get("file_path") if isinstance(row, dict) else row["file_path"]
    reg_dir = _sanitize_rel_path(os.path.dirname(reg_base or ""))
    folder = os.path.join(images_base, _secure_filename(prof_name or "_"), reg_dir)
    os.makedirs(folder, exist_ok=True)
    # derive filename from remote path
    filename_base = os.path.basename(rpath) or f"img_{int(time.time())}.bin"
    fname = _secure_filename(filename_base)
    abs_path = os.path.join(folder, fname)
    with open(abs_path, "wb") as f:
        f.write(content)
    ts = int(time.time())
    rel_path = os.path.relpath(abs_path, images_base).replace("\\", "/")
    conn.execute("INSERT INTO record_images(record_id, path, created_at) VALUES(?,?,?)", (rid, rel_path, ts))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "path": rel_path, "url": _public_image_url(rel_path)})


@bp.delete("/record_images/<int:iid>")
def delete_record_image(iid: int):
    conn = get_db()
    row = conn.execute("SELECT path FROM record_images WHERE id=?", (iid,)).fetchone()
    if not row:
        conn.close(); return jsonify({"ok": False, "deleted": 0})
    rel_path = row["path"]
    cur = conn.execute("DELETE FROM record_images WHERE id=?", (iid,))
    conn.commit()
    deleted = cur.rowcount
    # remove file only if no other link references it
    try:
        cnt = conn.execute("SELECT COUNT(1) FROM record_images WHERE path=?", (rel_path,)).fetchone()[0]
        if deleted and rel_path and cnt == 0:
            # Support both relative and absolute stored paths (backward compatibility)
            abs_path = rel_path if os.path.isabs(rel_path) else os.path.join(get_images_dir(), rel_path)
            if os.path.exists(abs_path):
                os.remove(abs_path)
    except Exception:
        pass
    conn.close()
    return jsonify({"ok": deleted > 0, "deleted": deleted})


@bp.get("/profiles/<int:pid>/list")
def ssh_list(pid: int):
    """List files matching a pattern on SSH host.
    Query params:
      - pattern: glob pattern (required)
      - type: 'image' or 'text' (optional; affects extension filtering)
      - limit: max files to return (default 200)
    """
    prof = _get_profile(pid)
    if not prof:
        abort(404)
    if (prof.get("protocol") or "ssh").lower() != "ssh":
        return jsonify({"error": "profile is not SSH"}), 400
    pattern = request.args.get("pattern", "").strip()
    if "|" in pattern:
        pattern = pattern.split("|", 1)[0].strip()
    kind = (request.args.get("type") or "").strip().lower()
    try:
        limit = int(request.args.get("limit", 200))
    except Exception:
        limit = 200
    if limit < 1:
        limit = 1
    if limit > 5000:
        limit = 5000
    if not pattern:
        return jsonify({"error": "pattern required"}), 400

    # Determine type automatically if requested or missing
    if not kind or kind == "auto":
        kind = _infer_path_type(pattern)
    def sh_q(s: str) -> str:
        return "'" + s.replace("'", "'\"'\"'") + "'"

    filter_case = ""
    # no-op here; filtering is handled below with case patterns

    # Expand via glob and list files; then filter by extension in Python
    script = (
        "shopt -s nullglob dotglob; "
        f"for f in {pattern}; do [ -f \"$f\" ] && echo \"$f\"; done | head -n {limit}"
    )
    cmd = f"bash -lc {sh_q(script)}"
    res = _ssh_exec(prof, cmd, timeout=_get_ssh_timeout())
    if not res.get("ok"):
        return jsonify({"error": res.get("error") or res.get("err") or "ssh error"}), 502
    files = (res.get("out") or "").splitlines()
    if kind == "image":
        files = [f for f in files if any(f.lower().endswith("."+e) for e in IMG_EXTS)]
    elif kind == "text":
        files = [f for f in files if any(f.lower().endswith("."+e) for e in TXT_EXTS)]
    return jsonify({"pattern": pattern, "type": kind or None, "files": files[:limit]})
# ------------------ Image Cache (for remote image fetch) ------------------
IMAGE_CACHE: Dict[str, Dict[str, Any]] = {}
IMAGE_CACHE_TTL = 60  # seconds
IMAGE_CACHE_MAX_BYTES = 20 * 1024 * 1024  # 20 MB


def _image_cache_key(prof_id: int, path: str) -> str:
    return f"{prof_id}:{path}"


def _image_cache_get(prof_id: int, path: str) -> Optional[bytes]:
    # Refresh limits from config
    try:
        cfg = load_config()
        img_cfg = (cfg.get("images_cache") or {}) if isinstance(cfg.get("images_cache"), dict) else {}
        global IMAGE_CACHE_TTL, IMAGE_CACHE_MAX_BYTES
        if "ttl" in img_cfg:
            IMAGE_CACHE_TTL = int(img_cfg.get("ttl") or IMAGE_CACHE_TTL)
        if "max_bytes" in img_cfg:
            IMAGE_CACHE_MAX_BYTES = int(img_cfg.get("max_bytes") or IMAGE_CACHE_MAX_BYTES)
    except Exception:
        pass
    key = _image_cache_key(prof_id, path)
    item = IMAGE_CACHE.get(key)
    if not item:
        return None
    if time.time() - item.get("ts", 0) > IMAGE_CACHE_TTL:
        IMAGE_CACHE.pop(key, None)
        return None
    return item.get("data")


def _image_cache_put(prof_id: int, path: str, data: bytes) -> None:
    # Refresh limits from config
    try:
        cfg = load_config()
        img_cfg = (cfg.get("images_cache") or {}) if isinstance(cfg.get("images_cache"), dict) else {}
        global IMAGE_CACHE_TTL, IMAGE_CACHE_MAX_BYTES
        if "ttl" in img_cfg:
            IMAGE_CACHE_TTL = int(img_cfg.get("ttl") or IMAGE_CACHE_TTL)
        if "max_bytes" in img_cfg:
            IMAGE_CACHE_MAX_BYTES = int(img_cfg.get("max_bytes") or IMAGE_CACHE_MAX_BYTES)
    except Exception:
        pass
    key = _image_cache_key(prof_id, path)
    IMAGE_CACHE[key] = {"ts": time.time(), "data": data, "size": len(data)}
    # Evict if over size
    total = sum(v.get("size", 0) for v in IMAGE_CACHE.values())
    if total <= IMAGE_CACHE_MAX_BYTES:
        return
    # Evict oldest until under budget
    for k, v in sorted(IMAGE_CACHE.items(), key=lambda kv: kv[1].get("ts", 0)):
        IMAGE_CACHE.pop(k, None)
        total -= v.get("size", 0)
        if total <= IMAGE_CACHE_MAX_BYTES:
            break
