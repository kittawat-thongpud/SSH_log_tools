<!--
Synced context header from context.md
CTX_MAIN_TOPIC: SSH Log Tools
CTX_PROFILE: dev
CTX_LANG: en
CTX_DIAGRAM_STYLE: default
CTX_MERMAID_THEME: neutral
CTX_PRIORITY_MODE: recent-first
-->

SSH Log Tools — Tray + Flask Web UI

Overview
- System tray application controlling a local Flask web server.
- Browse, tail, and search SSH/log files registered in `config.json`.
- Manage remote SSH/FTP profiles, run remote queries, and save records with images.
- Tray menu: Start server, Stop server, Open Web UI, Exit.

Quick Start
1) Create a virtualenv and install requirements:
   - Windows (PowerShell):
     `python -m venv .venv && .venv\\Scripts\\Activate.ps1 && pip install -r requirements.txt`
   - macOS/Linux:
     `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`

2) Configure logs in `config.json` (sample below).

3) Run the tray app: `python main.py`

4) Use the tray icon to Start/Stop the server or Open Web UI.

Remote features
- SSH via `paramiko` (included). If you see "paramiko not available", ensure you installed requirements inside your venv.
- FTP via Python `ftplib` (stdlib).

Config
Create/edit `config.json` at the project root:

{
  "host": "127.0.0.1",          // Flask bind host
  "port": 5000,                  // Flask bind port
  "logs": [                      // Local files (optional feature)
    { "name": "OpenSSH", "path": "C:/ProgramData/ssh/logs/sshd.log" },
    { "name": "AuthLog", "path": "/var/log/auth.log" }
  ],
  "logging": {                   // Application observability
    "enabled": true,
    "path": "logs",
    "filename": "{date}.log",   // supports {date}, {datetime}, {pid}
    "max_bytes": 1048576,
    "backup_count": 3,
    "level": "INFO",
    "format": "%(asctime)s %(levelname)s %(name)s: %(message)s",
    "console": true,
    "console_level": "WARNING"
  },
  "ui": {                        // Startup control panel (Tkinter)
    "show_on_start": false,
    "message": "App is begin!!",
    "title": "SSH Log Tools",
    "icon_path": "",
    "author_name": "",
    "author_email": ""
  },
  "api": {                       // API behavior
    "ssh_timeout": 15,           // Seconds for SSH commands (list/cat/sftp)
    "client_timeout_ms": 30000   // Frontend fetch timeout (ms)
  },
  "images_cache": {              // Remote images in-memory cache
    "ttl": 60,                   // Seconds before re-fetch over SFTP
    "max_bytes": 20971520        // Total cache budget (20 MiB)
  }
}

Logging
- Rotating file handler with `max_bytes` and `backup_count`.
- File path from `logging.path` and `logging.filename`; supports `{date}`, `{datetime}`, `{pid}`.
- Rotated files are prefixed with the index, for example `1-YYYY-MM-DD.log`.
- Default file level from `logging.level`; console logging toggled by `logging.console` with `logging.console_level`.

Startup UI
- Tray-only by default (no taskbar entry). Toggle panel with tray icon.
- Panel shows server status and enables Start/Stop/Open actions.
- Control via `ui.show_on_start`, `ui.message`, `ui.title`, `ui.icon_path` (.ico/.png).

API Overview
- Logs
  - GET `/api/logs` — list configured logs + metadata
  - GET `/api/logs/<name>/tail?lines=200` — last N lines
  - GET `/api/logs/<name>/search?q=&regex=0|1&case=0|1&context=0&limit=5000` — search
  - GET `/api/logs/<name>/download` — download file
- Profiles (SSH/FTP)
  - GET `/api/profiles` — list profiles
  - POST `/api/profiles` — create profile
  - PUT `/api/profiles/<id>` — update profile
  - DELETE `/api/profiles/<id>` — delete profile
  - GET `/api/profiles/<id>/paths` — list registered paths
  - POST `/api/profiles/<id>/paths` — add path
  - PUT `/api/profile_paths/<ppid>` — update path or grep_chain
  - DELETE `/api/profile_paths/<ppid>` — delete path
  - GET `/api/profiles/<id>/cat?pattern=&grep=` — remote tail (last N lines) with optional grep
  - GET `/api/profiles/<id>/list?pattern=&type=auto|text|image&limit=200` — expand glob to files; filters by type
  - GET `/api/profiles/<id>/ping` — connectivity check
  - GET `/api/profiles/<id>/ftp/list?path=/` — list FTP directory
- Records
  - POST `/api/records` — create a record
  - GET `/api/records` — list records (with images)
  - PUT `/api/records/<id>` — update metadata
  - DELETE `/api/records/<id>` — delete record
  - POST `/api/records/<id>/image` — upload image
  - POST `/api/records/<id>/image_remote` — fetch and attach remote image via SFTP (uses images_cache)
  - DELETE `/record_images/<iid>` — delete an image from a record

Notes
- Uses Werkzeug WSGI server in a background thread for clean start/stop.
- UI under `app/templates/` + `app/static/` with routes in `app/views.py`.
- Tray uses `pystray` and `Pillow`.

Profiles & Records
- Manage SSH/FTP targets under `/profiles`. Register multiple path patterns and optional grep chains.
- Query SSH logs via remote `cat` (+safe quoted `grep -F` chain) and browse FTP directories.
- Save records from the Logs page and attach images; images stored under `images/{profile_name}`.

More docs
- `context.md` — living system prompt (ground truth)
- `docs/code-architecture.md` — code map
- `docs/module-architecture.md` — module imports graph
- `docs/sections.md` — flows and API contracts
- `docs/system-summary.md` — system overview
