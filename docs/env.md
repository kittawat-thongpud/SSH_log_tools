<!--
Synced context header from context.md
CTX_MAIN_TOPIC: SSH Log Tools
CTX_PROFILE: dev
CTX_LANG: en
CTX_DIAGRAM_STYLE: default
CTX_MERMAID_THEME: neutral
CTX_PRIORITY_MODE: recent-first
-->

# Environment Variables (Context Driven)

This file replaces a traditional .env example by documenting environment variables and other context knobs for humans and AI tools.

## General Switches
| Key | Default | Scope | Notes |
|---|---:|---|---|
| CTX_MAIN_TOPIC | "SSH Log Tools" | global | Human‑readable theme/topic |
| CTX_PROFILE | dev | global | one of: dev, staging, prod |
| CTX_LANG | en | global | docs/UI language (en, th) |
| CTX_MERMAID_THEME | neutral | docs | Mermaid theme for diagrams |
| CTX_DIAGRAM_STYLE | default | docs | default, mono, sketch |
| CTX_PRIORITY_MODE | recent-first | build | selection rules for tags/sections |

## API and Cache (Config keys)
- `api.ssh_timeout` (seconds): Timeout for SSH commands (list/cat/sftp). Default 15.
- `api.client_timeout_ms` (ms): Frontend fetch timeout. Default 30000.
- `images_cache.ttl` (seconds): In-memory cache TTL for remote images. Default 60.
- `images_cache.max_bytes` (bytes): Max total cache size. Default 20971520 (20 MiB).
- `export.cell_width` (Excel units): Column width for the images column when exporting records. Default 18.
- `export.cell_height` (points): Row height for rows containing images. Default 96.
- `export.image_column` (letter): Column letter where images are placed. Default H.

## Runtime Values (Examples)
These are examples to inform context; the app primarily reads config.json at runtime.

| Key | Example | Notes |
|---|---|---|
| APP_HOST | 127.0.0.1 | Flask bind host (mirrors config.json) |
| APP_PORT | 5000 | Flask bind port (mirrors config.json) |
| LOGS_JSON | ./config.json | Path to log configuration file |
| UI_DEFAULT_TAIL | 200 | Default tail lines in UI |

## Notes
- Update docs/env.md to keep variables context‑aware and discoverable.
- Keep docs/datatag.md in sync for the canonical tag registry.
