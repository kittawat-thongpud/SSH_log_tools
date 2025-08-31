# DB Relations and System Operations

```mermaid
erDiagram
  PROFILES ||--o{ PROFILE_PATHS : has
  PROFILES ||--o{ RECORDS : creates
  RECORDS ||--o{ RECORD_IMAGES : has

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
```

```mermaid
flowchart TD
  A[Logs UI] -->|Create Record| B((POST /api/records))
  A -->|Attach Remote Image(s)| C((POST /api/records/:id/image_remote))
  A -->|Attach Local Image(s)| D((POST /api/records/:id/image))
  A -->|Preview Remote Image| E((GET /api/profiles/:pid/image))
  F[Records UI] -->|Delete Image| G((DELETE /record_images/:iid))
  F -->|Delete Record| H((DELETE /records/:id))

  B -->|insert| R[RECORDS]
  C -->|download to data/images & insert| RI[RECORD_IMAGES]
  D -->|save to data/images & insert| RI
  E -->|cache only| MEM[(Image Cache)]
  G -->|remove link| RI
  G -->|if last link, remove file| FS[data/images]
  H -->|remove record & links| R
  H -->|for each unreferenced file, remove| FS
```

Notes
- Image previews use in-memory cache only; records/images are persisted on Save.
- Deleting an image removes the file only if no other record references it.
- Deleting a record removes its image links and any orphaned files.

