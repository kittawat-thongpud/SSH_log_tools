<!--
Synced context header from context.md
CTX_MAIN_TOPIC: SSH Log Tools
CTX_PROFILE: dev
CTX_LANG: en
CTX_DIAGRAM_STYLE: default
CTX_MERMAID_THEME: neutral
CTX_PRIORITY_MODE: recent-first
-->

# Module Architecture (Mermaid Graph)

## Imports and Layers
```mermaid
graph TD
  subgraph Module Layer
    A[main.py]
    B[app/__init__.py]
    C[app/server.py]
    D[app/config.py]
    E[app/routes.py]
    F[app/views.py]
    G[app/db.py]
  end

  subgraph UI Layer
    T[templates/index.html]
    TP[templates/profiles.html]
    TR[templates/records.html]
    TF[templates/_record_form.html]
    S[static/app.js]
    RF[static/record_form.js]
    CSS[static/style.css]
  end

  A --> B
  A --> C
  A -->|reads| D
  B --> E
  B --> F
  B --> G
  E --> D
  E --> G
  F --> T
  F --> TP
  F --> TR
  T --> TF
  TR --> TF
  T --> S
  T --> RF
  T --> CSS
  TR --> RF
  TR --> CSS
  TP --> CSS

  subgraph Communication Layer
    API[/HTTP: /api/.../]
    WEB[/HTTP: GET \//]
  end

  E --> API
  F --> WEB
```

## Tag Mapping (Examples)
- module.entry — main.py
- module.api.routes — app/routes.py
- module.db — app/db.py (SQLite init and access)
- config.host, config.port — config.json
- logs.names, logs.paths — config.json
- computation.tail.block_size — routes.py (tail implementation)
- ui.record_form.grid — static/record_form.js (modal image grid)
- ui.logs.scan_table — static/app.js (match counts in register groups)

Keep this graph updated when imports or boundaries change.
