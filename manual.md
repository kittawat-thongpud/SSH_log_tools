<!--
Synced context header from context.md
CTX_MAIN_TOPIC: SSH Log Tools
CTX_PROFILE: dev
CTX_LANG: en
CTX_DIAGRAM_STYLE: default
CTX_MERMAID_THEME: neutral
CTX_PRIORITY_MODE: recent-first
-->

# User Manual

## Setup
1. Create and activate a virtual environment.
2. Install dependencies: `pip install -r requirements.txt`.
3. Run the tray application: `python main.py`.

## Configuration
Edit `config.json` to tune the application.

- `logs`: list of objects with `name` and `path` for local logs.
- `logging`: controls file/console logging (path, level, rotation).
- `ui`: tray control panel behavior and appearance.
- `api`: timeouts for SSH and client requests.
- `images_cache`: in-memory cache for remote images.
- `export`: Excel export options
  - `cell_width`: column width for images column.
  - `cell_height`: row height (points) for rows containing images.
  - `image_column`: column letter where images are placed.

## Usage
- Use the tray icon to start or stop the server and open the web UI.
- Closing the Control Panel window hides it to the system tray; exit via the panel's Exit button or the tray menu.
- Browse logs, search, and create records from the web UI.
- Export records via `/api/records/export`; images are inserted into the configured column and resized to fit.

