<!--
Synced context header from context.md
CTX_MAIN_TOPIC: SSH Log Tools
CTX_PROFILE: dev
CTX_LANG: en
CTX_DIAGRAM_STYLE: default
CTX_MERMAID_THEME: neutral
CTX_PRIORITY_MODE: recent-first
-->

# Code Architecture (Code Map)

## Code Tree
```
./
├─ context.md
├─ README.md
├─ requirements.txt
├─ config.json
├─ main.py                      # Tray entrypoint
├─ app/
│  ├─ __init__.py              # Flask app factory, blueprint registration
│  ├─ config.py                # Load/normalize config.json, logging setup, helpers
│  ├─ server.py                # Threaded WSGI server start/stop utilities
│  ├─ routes.py                # REST API: logs, profiles, records, ftp
│  ├─ db.py                    # SQLite init/access (profiles, paths, records, images)
│  ├─ views.py                 # Web views: /, /profiles, /records
│  ├─ templates/
│  │  ├─ index.html            # Logs page (SPA shell)
│  │  ├─ profiles.html         # Profiles management (SSH/FTP)
│  │  ├─ records.html          # Records browse/upload
│  │  └─ _record_form.html     # Shared record modal partial
│  └─ static/
│     ├─ app.js                # Logs page UI logic
│     ├─ record_form.js        # Reusable record form widget
│     └─ style.css             # Styles
├─ docs/
│  ├─ env.md
│  ├─ code-architecture.md
│  ├─ datatag.md
│  ├─ sections.md
│  ├─ module-architecture.md
│  └─ system-summary.md
├─ data/
│  └─ app.db                   # SQLite database (created at runtime)
└─ images/
   └─ {profile}/...            # Uploaded images by profile
```

## Components
- main.py: System tray controller (pystray) with Start/Stop/Open actions.
- app/__init__.py: Flask app factory; registers API and view blueprints.
- app/server.py: Werkzeug WSGI server wrapped in a background thread.
- app/config.py: Reads config.json, validates/normalizes log entries, configures logging.
- app/routes.py: APIs
  - Logs: list, tail, search, download
  - Profiles: CRUD, paths CRUD, SSH cat+grep, FTP browse
  - Records: CRUD and image upload
- app/db.py: SQLite schema init and helpers (profiles, profile_paths, records, record_images).
 - app/views.py: Serves index.html, profiles.html, records.html.
 - templates + static: Simple pages calling REST endpoints.
 - _record_form.html + record_form.js: reusable modal for creating/updating records.

## External Dependencies
- Flask, Werkzeug: web server and routing
- pystray, Pillow: system tray icon and image handling
- paramiko: SSH client (profiles)

## Build / Run
- See README.md for virtualenv and `python main.py`. Tray menu controls server lifecycle.
