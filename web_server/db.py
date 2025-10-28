"""
Lightweight SQLite helper for Web Asset Server.
- Standard library only (sqlite3), no ORM.
- Provides CRUD utilities for assets, versions, files, comments and change log.

Schema (simplified):
- assets(id TEXT PRIMARY KEY, name TEXT, family TEXT, description TEXT,
         tags TEXT, status TEXT, created_at TEXT, updated_at TEXT)
- versions(id INTEGER PRIMARY KEY AUTOINCREMENT, asset_id TEXT, version INTEGER,
           metadata_json TEXT, thumbnail_path TEXT, archived INTEGER DEFAULT 0,
           created_at TEXT, updated_at TEXT,
           UNIQUE(asset_id, version))
- files(id INTEGER PRIMARY KEY AUTOINCREMENT, asset_id TEXT, version INTEGER,
        filename TEXT, rel_path TEXT, format TEXT, size_bytes INTEGER)
- comments(id INTEGER PRIMARY KEY AUTOINCREMENT, asset_id TEXT, author TEXT,
          body TEXT, created_at TEXT)
- changes(id INTEGER PRIMARY KEY AUTOINCREMENT, change_type TEXT, asset_id TEXT,
          payload_json TEXT, created_at TEXT)
"""
from __future__ import annotations
import sqlite3
import json
import os
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

DB_FILE = os.path.join(os.path.dirname(__file__), "asset_server.sqlite3")


def utcnow() -> str:
    return datetime.utcnow().isoformat()


@contextmanager
def conn_rw():
    con = sqlite3.connect(DB_FILE, timeout=10, check_same_thread=False)
    try:
        con.execute("PRAGMA journal_mode=WAL;")
        con.execute("PRAGMA busy_timeout=5000;")
        yield con
        con.commit()
    finally:
        con.close()


@contextmanager
def conn_ro():
    con = sqlite3.connect(DB_FILE, timeout=10, check_same_thread=False)
    try:
        con.execute("PRAGMA journal_mode=WAL;")
        con.execute("PRAGMA busy_timeout=5000;")
        yield con
    finally:
        con.close()


def init_db():
    with conn_rw() as con:
        cur = con.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS assets (
              id TEXT PRIMARY KEY,
              name TEXT,
              family TEXT,
              description TEXT,
              tags TEXT,
              status TEXT,
              created_at TEXT,
              updated_at TEXT
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS versions (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              asset_id TEXT,
              version INTEGER,
              metadata_json TEXT,
              thumbnail_path TEXT,
              archived INTEGER DEFAULT 0,
              created_at TEXT,
              updated_at TEXT,
              UNIQUE(asset_id, version)
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS files (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              asset_id TEXT,
              version INTEGER,
              filename TEXT,
              rel_path TEXT,
              format TEXT,
              size_bytes INTEGER
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS comments (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              asset_id TEXT,
              author TEXT,
              body TEXT,
              created_at TEXT
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS changes (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              change_type TEXT,
              asset_id TEXT,
              payload_json TEXT,
              created_at TEXT
            );
            """
        )


def ensure_asset(asset_id: str, name: str, family: str, description: str = "", tags: str = ""):
    now = utcnow()
    with conn_rw() as con:
        cur = con.cursor()
        cur.execute("SELECT id FROM assets WHERE id=?", (asset_id,))
        if cur.fetchone():
            cur.execute(
                "UPDATE assets SET name=?, family=?, updated_at=? WHERE id=?",
                (name, family, now, asset_id),
            )
        else:
            cur.execute(
                "INSERT INTO assets(id, name, family, description, tags, status, created_at, updated_at)"
                " VALUES(?,?,?,?,?,?,?,?)",
                (asset_id, name, family, description, tags, "published", now, now),
            )
        # inline change log to avoid nested write-locks
        cur.execute(
            "INSERT INTO changes(change_type, asset_id, payload_json, created_at) VALUES(?,?,?,?)",
            ("asset_upsert", asset_id, json.dumps({"name": name, "family": family}), now),
        )


def upsert_version(asset_id: str, version: int, metadata: Dict[str, Any], thumbnail_path: str = ""):
    now = utcnow()
    with conn_rw() as con:
        cur = con.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO versions(asset_id, version, metadata_json, thumbnail_path, archived, created_at, updated_at)"
            " VALUES(?,?,?,?,0,?,?)",
            (asset_id, version, json.dumps(metadata), thumbnail_path, now, now),
        )
        cur.execute(
            "UPDATE versions SET metadata_json=?, thumbnail_path=?, updated_at=? WHERE asset_id=? AND version=?",
            (json.dumps(metadata), thumbnail_path, now, asset_id, version),
        )
        cur.execute(
            "INSERT INTO changes(change_type, asset_id, payload_json, created_at) VALUES(?,?,?,?)",
            ("version_upsert", asset_id, json.dumps({"version": version}), now),
        )


def add_file(asset_id: str, version: int, filename: str, rel_path: str, fmt: str, size_bytes: int):
    with conn_rw() as con:
        cur = con.cursor()
        cur.execute(
            "INSERT INTO files(asset_id, version, filename, rel_path, format, size_bytes) VALUES(?,?,?,?,?,?)",
            (asset_id, version, filename, rel_path, fmt, size_bytes),
        )
        cur.execute(
            "INSERT INTO changes(change_type, asset_id, payload_json, created_at) VALUES(?,?,?,?)",
            ("file_added", asset_id, json.dumps({"version": version, "filename": filename}), utcnow()),
        )


def list_assets(filters: Dict[str, Any], limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    where = []
    params: List[Any] = []
    if fam := filters.get("family"):
        where.append("family = ?")
        params.append(fam)
    if status := filters.get("status"):
        where.append("status = ?")
        params.append(status)
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    order = " ORDER BY updated_at DESC"
    sql = f"SELECT id, name, family, description, tags, status, created_at, updated_at FROM assets{where_sql}{order} LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    with conn_ro() as con:
        cur = con.cursor()
        rows = cur.execute(sql, params).fetchall()
    out = []
    for r in rows:
        out.append({
            "id": r[0], "name": r[1], "family": r[2], "description": r[3],
            "tags": r[4], "status": r[5], "created_at": r[6], "updated_at": r[7]
        })
    return out


def get_asset(asset_id: str) -> Optional[Dict[str, Any]]:
    with conn_ro() as con:
        cur = con.cursor()
        a = cur.execute("SELECT id, name, family, description, tags, status, created_at, updated_at FROM assets WHERE id=?", (asset_id,)).fetchone()
        if not a:
            return None
        versions = cur.execute(
            "SELECT version, metadata_json, thumbnail_path, archived, created_at, updated_at FROM versions WHERE asset_id=? ORDER BY version DESC",
            (asset_id,),
        ).fetchall()
        files = cur.execute(
            "SELECT version, filename, rel_path, format, size_bytes FROM files WHERE asset_id=?",
            (asset_id,),
        ).fetchall()
    v_list = [
        {
            "version": v[0], "metadata": json.loads(v[1] or "{}"), "thumbnail_path": v[2],
            "archived": bool(v[3]), "created_at": v[4], "updated_at": v[5]
        } for v in versions
    ]
    f_list = [
        {"version": f[0], "filename": f[1], "rel_path": f[2], "format": f[3], "size_bytes": f[4]} for f in files
    ]
    return {
        "id": a[0], "name": a[1], "family": a[2], "description": a[3], "tags": a[4], "status": a[5],
        "created_at": a[6], "updated_at": a[7], "versions": v_list, "files": f_list
    }


def update_asset(asset_id: str, fields: Dict[str, Any]):
    allow = {"name", "description", "tags", "status"}
    sets = []
    params: List[Any] = []
    for k, v in fields.items():
        if k in allow:
            sets.append(f"{k} = ?")
            params.append(v)
    if not sets:
        return
    now = utcnow()
    params.append(now)
    params.append(asset_id)
    sql = f"UPDATE assets SET {', '.join(sets)}, updated_at=? WHERE id=?"
    with conn_rw() as con:
        con.execute(sql, params)
        con.execute(
            "INSERT INTO changes(change_type, asset_id, payload_json, created_at) VALUES(?,?,?,?)",
            ("asset_update", asset_id, json.dumps({k: v for k, v in fields.items() if k in allow}), now),
        )


def archive_version(asset_id: str, version: int):
    now = utcnow()
    with conn_rw() as con:
        con.execute("UPDATE versions SET archived=1, updated_at=? WHERE asset_id=? AND version=?", (now, asset_id, version))
        con.execute(
            "INSERT INTO changes(change_type, asset_id, payload_json, created_at) VALUES(?,?,?,?)",
            ("version_archived", asset_id, json.dumps({"version": version}), now),
        )



def delete_version(asset_id: str, version: int):
    """Hard delete a specific version and its file rows."""
    now = utcnow()
    with conn_rw() as con:
        cur = con.cursor()
        cur.execute("DELETE FROM files WHERE asset_id=? AND version=?", (asset_id, version))
        cur.execute("DELETE FROM versions WHERE asset_id=? AND version=?", (asset_id, version))
        cur.execute(
            "INSERT INTO changes(change_type, asset_id, payload_json, created_at) VALUES(?,?,?,?)",
            ("version_deleted", asset_id, json.dumps({"version": version}), now),
        )



def delete_asset(asset_id: str):
    """Hard delete an asset and all related rows.
    Note: Storage files are removed by storage layer; this only touches DB.
    """
    now = utcnow()
    with conn_rw() as con:
        cur = con.cursor()
        cur.execute("DELETE FROM files WHERE asset_id=?", (asset_id,))
        cur.execute("DELETE FROM versions WHERE asset_id=?", (asset_id,))
        cur.execute("DELETE FROM comments WHERE asset_id=?", (asset_id,))
        cur.execute("DELETE FROM assets WHERE id=?", (asset_id,))
        cur.execute(
            "INSERT INTO changes(change_type, asset_id, payload_json, created_at) VALUES(?,?,?,?)",
            ("asset_deleted", asset_id, json.dumps({}), now),
        )


def add_comment(asset_id: str, author: str, body: str):
    now = utcnow()
    with conn_rw() as con:
        con.execute("INSERT INTO comments(asset_id, author, body, created_at) VALUES(?,?,?,?)", (asset_id, author, body, now))
        con.execute(
            "INSERT INTO changes(change_type, asset_id, payload_json, created_at) VALUES(?,?,?,?)",
            ("comment", asset_id, json.dumps({"author": author}), now),
        )


def list_changes(since_iso: Optional[str], limit: int = 100) -> List[Dict[str, Any]]:
    with conn_ro() as con:
        cur = con.cursor()
        if since_iso:
            rows = cur.execute("SELECT change_type, asset_id, payload_json, created_at FROM changes WHERE created_at > ? ORDER BY created_at ASC LIMIT ?", (since_iso, limit)).fetchall()
        else:
            rows = cur.execute("SELECT change_type, asset_id, payload_json, created_at FROM changes ORDER BY created_at ASC LIMIT ?", (limit,)).fetchall()
    return [{"change_type": r[0], "asset_id": r[1], "payload": json.loads(r[2] or "{}"), "created_at": r[3]} for r in rows]


def log_change(change_type: str, asset_id: str, payload: Dict[str, Any]):
    with conn_rw() as con:
        con.execute("INSERT INTO changes(change_type, asset_id, payload_json, created_at) VALUES(?,?,?,?)", (change_type, asset_id, json.dumps(payload), utcnow()))


# Initialize DB on module import
init_db()

