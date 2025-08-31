# DB Relations and System Operations

```mermaid
erDiagram
  PROFILES ||--o{ PROFILE_PATHS : has
  PROFILES ||--o{ RECORDS : creates
  RECORDS ||--o{ RECORD_IMAGES : has
  RECORDS ||--o{ RECORD_TAGS : tagged
  TAGS ||--o{ RECORD_TAGS : referenced

  PROFILES {
    int id PK
    string name
    string protocol
    string host
    int port
    string username
    string password
    int created_at
  }

  PROFILE_PATHS {
    int id PK
    int profile_id FK
    string path
    string grep_chain
    string cmd_suffix
    string type
    int created_at
  }

  RECORDS {
    int id PK
    int profile_id FK
    string title
    string file_path
    string filter
    string content // Logs
    string situation
    int event_time // Situation Date
    string description
    int created_at // Create Date
  }

  RECORD_IMAGES {
    int id PK
    int record_id FK
    string path // relative under data/images
    int created_at
  }

  TAGS {
    int id PK
    string name
    int created_at
  }

  RECORD_TAGS {
    int record_id FK
    int tag_id FK
  }
```

```mermaid
flowchart TD
  A[Logs UI] -->|Create Record| B((POST /api/records))
  A -->|Attach Remote Image(s)| C((POST /api/records/:id/image_remote))
  A -->|Attach Local Image(s)| D((POST /api/records/:id/image))
  A -->|Preview Remote Image| E((GET /api/profiles/:pid/image))
  F[Records UI] -->|Delete Image| G((DELETE /record_images/:iid))
  F -->|Delete Record| H((DELETE /records/:id))
  H2[Tags UI] -->|Add Tag| I((POST /api/tags))
  H2 -->|Delete Tag| J((DELETE /api/tags/:id))

  B -->|insert| R[RECORDS]
  C -->|download to data/images & insert| RI[RECORD_IMAGES]
  D -->|save to data/images & insert| RI
  E -->|cache only| MEM[(Image Cache)]
  G -->|remove link| RI
  G -->|if last link, remove file| FS[data/images]
  H -->|remove record & links| R
  H -->|for each unreferenced file, remove| FS
  I -->|insert| T[TAGS]
  J -->|delete| T
```

Notes
- Image previews use in-memory cache only; records/images are persisted on Save.
- Deleting an image removes the file only if no other record references it.
- Deleting a record removes its image links and any orphaned files.

