<!--
Synced context header from context.md
CTX_MAIN_TOPIC: SSH Log Tools
CTX_PROFILE: dev
CTX_LANG: en
CTX_DIAGRAM_STYLE: default
CTX_MERMAID_THEME: neutral
CTX_PRIORITY_MODE: recent-first
-->

# Data Tags Registry

Purpose: Central registry of named tags used as context variables and selectors across docs, diagrams, and code reviews.

## Conventions
- Naming: `layer.scope.name` (e.g., `module.api.routes`, `env.CTX_MAIN_TOPIC`).
- Layers: `env`, `module`, `communication`, `computation`, `ui`, `config`.
- Priority: `critical` > `core` > `supplemental`.

## Selection Rules
1) Priority order: critical first, then core, then supplemental.
2) Within same priority, prefer `module` and `communication` for contracts; then `computation`; then `ui`.
3) `env.*` overrides document defaults when present.

## Tags
| Tag | Value / Source | Layer | Priority | Notes |
|---|---|---|---|---|
| env.CTX_MAIN_TOPIC | "SSH Log Tools" | env | critical | Main topic for this project |
| env.CTX_PROFILE | dev | env | supplemental | Execution profile |
| env.CTX_LANG | en | env | supplemental | Docs/UI language |
| env.CTX_MERMAID_THEME | neutral | env | supplemental | Diagram theme |
| config.host | config.json:host | config | core | Server bind host |
| config.port | config.json:port | config | core | Server bind port |
| logs.names | config.json:logs[*].name | config | core | Registered log identifiers |
| logs.paths | config.json:logs[*].path | config | core | Registered absolute paths |
| module.entry | main.py | module | critical | Tray entrypoint controlling server |
| module.api.routes | app/routes.py | module | critical | REST API contracts |
| module.web.ui | templates/index.html | ui | core | SPA surface |
| computation.tail.block_size | 1024 | computation | supplemental | Tail chunk size (bytes) |
| computation.search.limit.default | 5000 | computation | core | Default max results |
| computation.search.context.default | 0 | computation | supplemental | Default context lines |
| ui.default_tail_lines | 200 | ui | supplemental | UI default tail lines |

Update this table whenever contracts, defaults, or config shapes change.
