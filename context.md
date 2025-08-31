# Project Context (Living System Prompt)

Purpose: Canonical prompt for humans and AI tools working on this repo. It centralizes the intent, constraints, terminology, and links to ground-truth subdocs.

## 0) Quick Switchboard (User Config)

Config is defined in `docs/env.md` and duplicated here for visibility.

| Key | Default | Scope | Notes |
|---|---:|---|---|
| CTX_MAIN_TOPIC | "SSH Log Tools" | global | Human-readable theme/topic |
| CTX_PROFILE | dev | global | dev, staging, prod |
| CTX_LANG | en | global | docs/UI language |
| CTX_DIAGRAM_STYLE | default | docs | default, mono, sketch |
| CTX_MERMAID_THEME | neutral | docs | neutral, forest, dark |
| CTX_PRIORITY_MODE | recent-first | build | recent-first, usage-weighted, critical-path |

See `docs/datatag.md` for tag registry and selection criteria.

## 1) Mission & Non-Goals
- Mission: Provide a lightweight system-tray managed Flask web UI to browse, tail, and search registered SSH/log files across Windows/Linux paths, with simple APIs and a responsive single-page UI.
- Non-Goals:
  - Not a full SIEM or log shipper; no central ingestion.
  - No auth/multi-user until explicitly requested.
  - No schema-enforced parsing; operates on plain text logs.

## 2) Ground Truth Links
- Code map — `docs/code-architecture.md`
- Data tags — `docs/datatag.md`
- Sections & KB — `docs/sections.md`
- Module graph — `docs/module-architecture.md`
- System summary — `docs/system-summary.md`
- Environment config — `docs/env.md`

## 3) Operating Principles
- Single source of truth: this file + linked subdocs.
- Update cadence: change docs on any structural or contract changes.
- Diagrams are executable specs: code/tests must follow diagram changes.
- Keep interfaces small; prefer explicitness over hidden magic.

## 4) Runtime Config Contract (config.json)
All keys are optional; defaults are applied by `app/config.py`. Paths are resolved relative to the working directory unless absolute.

```json
{
  "host": "127.0.0.1",          // Flask bind host
  "port": 5000,                  // Flask bind port
  "logs": [                      // Files to expose in UI/APIs
    { "name": "ExampleSSH", "path": "C:/ProgramData/ssh/logs/sshd.log" }
  ],
  "logging": {                   // Application observability
    "enabled": true,             // Enable file logging
    "path": "logs",             // Directory for log files
    "filename": "{date}.log",   // Supports {date}, {datetime}, {pid}
    "max_bytes": 1048576,        // Rotate after this size (bytes)
    "backup_count": 3,           // Number of rotated files to keep
    "level": "INFO",            // Log level for file handler
    "format": "%(asctime)s %(levelname)s %(name)s: %(message)s", // Record format
    "console": true,             // Also emit to console
    "console_level": "WARNING"   // Console log level (e.g., INFO, DEBUG)
  }
  ,
  "ui": {                        // Startup control panel
    "show_on_start": false,      // Do not show at app start
    "message": "App is begin!!", // Diagnostic text
    "title": "SSH Log Tools",    // Window title
    "icon_path": ""              // Optional path to tray/window icon (.ico/.png)
  }
}
```

Notes:
- `logs` entries require `name` and `path`.
- Logging uses a rotating file handler; if directory creation fails, falls back to CWD.
- `console` controls a console handler (warnings and above) in addition to file logging.

## 5) Observability & Logging
- Startup: `main.py` calls `setup_logging()` and logs tray/server lifecycle events.
- Server: `app/server.py` logs start/stop and thread transitions.
- API: `app/routes.py` logs list/tail/search/download activity and basic parameters.
- Handlers: Rotating file handler respects `max_bytes` and `backup_count`; optional console handler with configurable level. Rotated files are prefixed with the index, e.g., `1-YYYY-MM-DD.log`.

## 6) Change Journal (append newest on top)
- 2025-08-31 — Extracted record form modal into reusable widget shared by Logs and Records pages; added record_form.js and template.
- 2025-08-30 — Switched to tray-only mode (no taskbar entry); control panel is shown/hidden via tray icon (default menu/double-click).
- 2025-08-30 — Control panel redesign: colorful theme, status indicator, Start/Stop buttons auto-enable/disable, optional custom icon via `ui.icon_path`.
- 2025-08-30 — Added optional startup control panel (diagnostic popup) with Start/Stop/Open/Minimize/Exit; configurable via `ui.*` in config.json.
- 2025-08-30 — Added logging config (file + console toggle), rotating handler, and instrumentation; updated docs.
- 2025-08-30 — Initial project context for SSH Log Tools; added subdocs and aligned env defaults.
