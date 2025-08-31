<!--
Synced context header from context.md
CTX_MAIN_TOPIC: SSH Log Tools
CTX_PROFILE: dev
CTX_LANG: en
CTX_DIAGRAM_STYLE: default
CTX_MERMAID_THEME: neutral
CTX_PRIORITY_MODE: recent-first
-->

# System Summary

SSH Log Tools is a local-first log browsing utility with a system tray controller and a Flask-based web UI.

## Purpose
- Quickly inspect SSH/log files configured in config.json: list, tail, search, and download.
- Provide a tiny, dependency-light tray + web surface that works across Windows/Linux paths.

## Architecture
- Tray (pystray, Pillow) launches/stops a local Flask server and opens the browser.
- Flask app registers API (app/routes.py) and view (app/views.py) blueprints.
- A threaded Werkzeug WSGI server provides clean start/stop lifecycle.
- Frontend is a simple SPA (templates/index.html + static/) calling REST endpoints.

## Key Behaviors
- Tail reads from the end of the file in blocks to collect N lines.
- Search streams lines, supports substring or regex, case toggle, and context_before.
- Config is read from config.json and normalized to name/path pairs.
- Profiles allow connecting to remote targets (SSH/FTP). SSH queries use remote `cat` with optional `grep` filter; FTP browsing lists directories.
- Remote registers support two types: text (tail last N lines per file) and images (list file paths). A file-expansion endpoint resolves globs on the remote host.
- Records persist selected log snippets with optional images; images are stored under `images/{profile_name}`.
  - Selecting images from the Logs page auto-imports the files via SFTP and attaches them to the new record.
  - Exporting records to Excel embeds the first image in-cell and resizes it using `export` settings.

## Constraints & Assumptions
- No authentication; server binds to 127.0.0.1 by default.
- UTF‑8 reading with replacement for mixed encodings.
- Large files are handled incrementally; operations remain memory-bounded.
- Remote image downloads are cached in-memory with TTL and total-size budget (configurable).

## Next Options
- Add SSE/WebSocket for live follow (tail -f).
- Add auth and CSRF if exposed beyond localhost.
- Package as a standalone executable (PyInstaller) and enable autostart.
