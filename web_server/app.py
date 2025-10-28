"""
Minimal Flask-based Web Asset Server for Pyblish pipeline.
- REST API for assets, files, thumbnails, package download, comments, status.
- Token auth via X-API-Key (see web_server/auth.py).
- SQLite storage (web_server/db.py) + filesystem storage (web_server/storage.py).

NOTE: Requires Flask (and Werkzeug). Ask to `pip install flask` before running.
Run:  python -m web_server.app  (or `flask --app web_server.app run`)
"""
from __future__ import annotations
import os
import io
import json
import zipfile
from datetime import datetime
from typing import Any, Dict

from flask import Flask, jsonify, request, send_file

from . import db
from .auth import require_role
from .storage import save_upload, absolute_from_rel, package_version, delete_asset_storage, delete_version_storage

app = Flask(__name__)


@app.get("/api/stats")
def stats():
    return jsonify({
        "ok": True,
        "time": datetime.utcnow().isoformat(),
        "version": "2.0.0"
    })


# ---- Asset create/upsert from integrate_web_pipeline ----
@app.post("/api/assets")
@require_role("editor")
def upsert_asset():
    payload = request.get_json(force=True, silent=True) or {}
    asset_id = payload.get("asset_id") or ""
    name = payload.get("name") or asset_id
    family = (payload.get("family") or "unknown").lower()
    description = payload.get("description") or ""
    tags = ",".join(payload.get("tags", [])) if isinstance(payload.get("tags"), list) else payload.get("tags", "")
    metadata = payload.get("metadata") or {}

    if not asset_id:
        return jsonify({"error": "asset_id required"}), 400

    # Persist asset + latest version pointer (we use timestamp as version if not provided)
    version = int(payload.get("version") or 1)

    db.ensure_asset(asset_id, name, family, description, tags)
    db.upsert_version(asset_id, version, metadata)

    return jsonify({"asset_id": asset_id, "version": version})


# Upload single file (multipart)
@app.post("/api/upload")
@require_role("editor")
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "file field missing"}), 400
    file = request.files["file"]
    asset_id = request.form.get("asset_id", "")
    version = int(request.form.get("version", "1") or 1)
    family = request.form.get("family", "")
    if not asset_id:
        return jsonify({"error": "asset_id required"}), 400

    # Save to temp then move under storage_root
    tmp_dir = os.path.join(os.path.dirname(__file__), "_tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    tmp_path = os.path.join(tmp_dir, file.filename)
    file.save(tmp_path)

    rel_path, size = save_upload(asset_id, version, tmp_path, file.filename)
    ext = os.path.splitext(file.filename)[1].lstrip(".").lower()
    db.add_file(asset_id, version, file.filename, rel_path, ext, size)

    return jsonify({"ok": True, "asset_id": asset_id, "version": version, "rel_path": rel_path})


# ---- Query/list ----
@app.get("/api/assets")
@require_role("viewer")
def list_assets():
    family = request.args.get("family")
    status = request.args.get("status")
    limit = int(request.args.get("limit", "50"))
    offset = int(request.args.get("offset", "0"))
    items = db.list_assets({"family": family, "status": status}, limit=limit, offset=offset)
    return jsonify({"items": items, "count": len(items)})


@app.get("/api/assets/<asset_id>")
@require_role("viewer")
def asset_detail(asset_id: str):
    a = db.get_asset(asset_id)
    if not a:
        return jsonify({"error": "not found"}), 404
    return jsonify(a)


@app.get("/api/assets/<asset_id>/download")
def download_file(asset_id: str):
    version = int(request.args.get("version", "1") or 1)
    fmt = (request.args.get("format") or "").lower().lstrip(".")
    a = db.get_asset(asset_id)
    if not a:
        return jsonify({"error": "not found"}), 404
    # Pick first file of requested format
    for f in a.get("files", []):
        if f["version"] == version and (fmt == "" or f["format"] == fmt):
            abs_path = absolute_from_rel(f["rel_path"])
            return send_file(abs_path, as_attachment=True, download_name=f["filename"])
    return jsonify({"error": "file not found for version/format"}), 404


@app.get("/api/assets/<asset_id>/package")
def download_package(asset_id: str):
    version = int(request.args.get("version", "1") or 1)
    a = db.get_asset(asset_id)
    if not a:
        return jsonify({"error": "not found"}), 404

    # Build zip in memory
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        meta = {"asset": {k: a[k] for k in ("id", "name", "family", "description", "tags", "status")},
                "version": version}
        zf.writestr("metadata.json", json.dumps(meta, indent=2))
        for f in a.get("files", []):
            if f["version"] == version:
                abs_path = absolute_from_rel(f["rel_path"])
                arc_name = os.path.join("files", f["filename"])
                if os.path.exists(abs_path):
                    zf.write(abs_path, arc_name)
    mem.seek(0)
    return send_file(mem, as_attachment=True, download_name=f"{asset_id}_v{version}.zip")


# ---- Edit metadata / status / comments ----
@app.patch("/api/assets/<asset_id>")
@require_role("editor")
def update_asset(asset_id: str):
    fields = (request.get_json(silent=True) or {})
    db.update_asset(asset_id, fields)
    return jsonify({"ok": True})


@app.post("/api/assets/<asset_id>/comment")
@require_role("viewer")
def add_comment(asset_id: str):
    payload = request.get_json(force=True, silent=True) or {}
    author = payload.get("author", "anonymous")
    body = payload.get("body", "")
    db.add_comment(asset_id, author, body)
    return jsonify({"ok": True})


@app.post("/api/assets/<asset_id>/status")
@require_role("editor")
def set_status(asset_id: str):
    payload = request.get_json(force=True, silent=True) or {}
    status = payload.get("status", "published")
    db.update_asset(asset_id, {"status": status})
    return jsonify({"ok": True})


@app.delete("/api/assets/<asset_id>/versions/<int:version>")
@require_role("admin")
def delete_version(asset_id: str, version: int):
    try:
        delete_version_storage(asset_id, version)
    except Exception:
        pass
    db.delete_version(asset_id, version)
    return jsonify({"ok": True})


# ---- Sync support ----

# ---- Delete asset ----
@app.delete("/api/assets/<asset_id>")
@require_role("admin")
def delete_asset_endpoint(asset_id: str):
    try:
        # remove files first (best-effort)
        delete_asset_storage(asset_id)
    except Exception:
        # ignore storage errors to not block DB deletion
        pass
    db.delete_asset(asset_id)
    return jsonify({"ok": True})

@app.get("/api/changes")
@require_role("viewer")
def list_changes():
    since = request.args.get("since")
    items = db.list_changes(since)
    return jsonify({"items": items})


# ---- Front page (very simple) ----
@app.get("/")
@require_role("viewer")
def home():
    # Simple JSON page to signal server alive; UI link provided
    return jsonify({"message": "Web Asset Server running", "browse": "/api/assets", "ui": "/ui"})


@app.get("/ui")
def ui():
    # Serve simple static index to browse assets
    path = os.path.join(os.path.dirname(__file__), "static_index.html")
    if os.path.exists(path):
        with open(path, "rb") as f:
            data = f.read()
        return app.response_class(data, mimetype="text/html")
    return jsonify({"error": "ui not found"}), 404


if __name__ == "__main__":
    # Allow overriding host/port via env
    host = os.environ.get("WEB_SERVER_HOST", "127.0.0.1")
    port = int(os.environ.get("WEB_SERVER_PORT", "5000"))
    app.run(host=host, port=port, debug=True)

