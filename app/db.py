import os
import sqlite3
import time
from typing import Any, Dict, Iterable, Tuple


DB_DIR = os.path.join(os.getcwd(), "data")
DB_PATH = os.path.join(DB_DIR, "app.db")
IMAGES_DIR = os.path.join(DB_DIR, "images")


def _ensure_dirs() -> None:
    os.makedirs(DB_DIR, exist_ok=True)
    os.makedirs(IMAGES_DIR, exist_ok=True)


def get_db() -> sqlite3.Connection:
    _ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")
    except Exception:
        pass
    return conn


def get_images_dir() -> str:
    _ensure_dirs()
    return IMAGES_DIR


def init_db() -> None:
    conn = get_db()
    cur = conn.cursor()
    # profiles table: ssh/ftp targets
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            protocol TEXT NOT NULL DEFAULT 'ssh',
            host TEXT NOT NULL,
            port INTEGER NOT NULL DEFAULT 22,
            username TEXT,
            password TEXT,
            created_at INTEGER NOT NULL
        )
        """
    )
    # optional registered paths for a profile
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS profile_paths (
            id INTEGER PRIMARY KEY,
            profile_id INTEGER NOT NULL,
            path TEXT NOT NULL,
            grep_chain TEXT,
            cmd_suffix TEXT,
            type TEXT NOT NULL DEFAULT 'text',
            created_at INTEGER NOT NULL,
            FOREIGN KEY(profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        )
        """
    )
    # Backfill missing grep_chain column (migration for existing DBs)
    try:
        cur.execute("PRAGMA table_info(profile_paths)")
        cols = [r[1] for r in cur.fetchall()]
        if "grep_chain" not in cols:
            cur.execute("ALTER TABLE profile_paths ADD COLUMN grep_chain TEXT")
        if "cmd_suffix" not in cols:
            cur.execute("ALTER TABLE profile_paths ADD COLUMN cmd_suffix TEXT")
        if "type" not in cols:
            cur.execute("ALTER TABLE profile_paths ADD COLUMN type TEXT NOT NULL DEFAULT 'text'")
    except Exception:
        pass
    # records table for saved logs
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY,
            profile_id INTEGER,
            title TEXT,
            file_path TEXT,
            filter TEXT,
            content TEXT,
            situation TEXT,
            event_time INTEGER,
            description TEXT,
            created_at INTEGER NOT NULL,
            FOREIGN KEY(profile_id) REFERENCES profiles(id) ON DELETE SET NULL
        )
        """
    )
    # images associated to records
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS record_images (
            id INTEGER PRIMARY KEY,
            record_id INTEGER NOT NULL,
            path TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            FOREIGN KEY(record_id) REFERENCES records(id) ON DELETE CASCADE
        )
        """
    )
    # tag registry
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            created_at INTEGER NOT NULL
        )
        """
    )
    # record-tag mapping (many-to-many)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS record_tags (
            record_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            PRIMARY KEY(record_id, tag_id),
            FOREIGN KEY(record_id) REFERENCES records(id) ON DELETE CASCADE,
            FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE
        )
        """
    )
    conn.commit()
    # Records migration for new columns
    try:
        cur = get_db().cursor()
    except Exception:
        cur = conn.cursor()
    try:
        cur.execute("PRAGMA table_info(records)")
        cols = [r[1] for r in cur.fetchall()]
        if "situation" not in cols:
            cur.execute("ALTER TABLE records ADD COLUMN situation TEXT")
        if "event_time" not in cols:
            cur.execute("ALTER TABLE records ADD COLUMN event_time INTEGER")
        if "description" not in cols:
            cur.execute("ALTER TABLE records ADD COLUMN description TEXT")
        conn.commit()
    except Exception:
        pass
    conn.close()


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {k: row[k] for k in row.keys()}
