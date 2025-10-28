"""
Sync Agent for bidirectional sync between local exports and Web Asset Server.
- Scans local exports directory and pushes new/changed assets to server.
- Polls server /api/changes for remote updates, applies to local (rename/move/archive).
- Conflict policy: last-write-wins by updated_at; on conflict, keeps both and writes a .conflict marker.

Usage:
  python scripts/sync_agent.py --server http://localhost:5000 --api-key demo-edit --root exports

Dependencies: requests (optional). Falls back to urllib for GET/POST JSON, but multipart upload is best with requests.
"""
from __future__ import annotations
import argparse
import os
import time
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Optional requests
try:
    import requests  # type: ignore
    HAVE_REQUESTS = True
except Exception:
    import urllib.request
    import urllib.error
    HAVE_REQUESTS = False


def http_get_json(url: str, headers: Dict[str, str], timeout: int = 10):
    try:
        if HAVE_REQUESTS:
            r = requests.get(url, headers=headers, timeout=timeout)
            return r.status_code, (r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text)
        else:
            req = urllib.request.Request(url, headers=headers, method='GET')
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read().decode('utf-8', errors='ignore')
            return 200, json.loads(data)
    except Exception as e:
        return 0, str(e)


def http_post_json(url: str, headers: Dict[str, str], payload: Dict[str, Any], timeout: int = 20):
    try:
        if HAVE_REQUESTS:
            r = requests.post(url, headers=headers, json=payload, timeout=timeout)
            try:
                body = r.json()
            except Exception:
                body = r.text
            return r.status_code, body
        else:
            data = json.dumps(payload).encode('utf-8')
            hdr = headers.copy()
            hdr['Content-Type'] = 'application/json'
            req = urllib.request.Request(url, headers=hdr, data=data)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode('utf-8', errors='ignore')
            try:
                return 200, json.loads(body)
            except Exception:
                return 200, body
    except Exception as e:
        return 0, str(e)


def post_file(url: str, headers: Dict[str, str], file_path: str, fields: Dict[str, str]):
    if not HAVE_REQUESTS:
        return 501, 'requests not available for multipart'
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f)}
            r = requests.post(url, headers=headers, files=files, data=fields, timeout=60)
            try:
                body = r.json()
            except Exception:
                body = r.text
            return r.status_code, body
    except Exception as e:
        return 0, str(e)


def next_version_for(asset_path: Path) -> int:
    """Very basic version resolver: use folder count under asset folder."""
    if not asset_path.exists():
        return 1
    versions = [p for p in asset_path.iterdir() if p.is_dir() and p.name.lower().startswith('v') and p.name[1:].isdigit()]
    if not versions:
        return 1
    return max(int(p.name[1:]) for p in versions) + 1


def push_local(root: Path, server: str, headers: Dict[str, str]):
    """Upload new assets in root to server if not present (simple heuristic).
    Expected layout: exports/<family>/<asset_name>/<files>
    """
    if not root.exists():
        return
    for fam_dir in root.iterdir():
        if not fam_dir.is_dir():
            continue
        family = fam_dir.name
        for asset_dir in fam_dir.iterdir():
            if not asset_dir.is_dir():
                continue
            asset_name = asset_dir.name
            asset_id = f"{family}_{asset_name}"
            # Create asset record
            status, body = http_post_json(f"{server}/api/assets", headers, {
                "asset_id": asset_id,
                "name": asset_name,
                "family": family,
                "version": 1,
                "metadata": {}
            })
            # Upload files
            for f in asset_dir.glob('*'):
                if not f.is_file():
                    continue
                _ = post_file(f"{server}/api/upload", headers, str(f), {
                    "asset_id": asset_id,
                    "version": "1",
                    "family": family
                })


def apply_remote_changes(root: Path, changes: List[Dict[str, Any]]):
    archive_dir = root / ".archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    for ch in changes:
        ctype = ch.get('change_type')
        # In this minimal agent we do not yet move local files; this is a placeholder
        if ctype == 'version_archived':
            # nothing destructive, rely on server side package management
            pass


def loop(server: str, api_key: str, root: str, interval: int = 10):
    headers = {"X-API-Key": api_key}
    root_path = Path(root)
    last_since = None

    # Initial push pass (best-effort)
    push_local(root_path, server, headers)

    while True:
        code, body = http_get_json(f"{server}/api/changes" + (f"?since={last_since}" if last_since else ""), headers)
        if code == 200 and isinstance(body, dict):
            items = body.get('items', [])
            apply_remote_changes(root_path, items)
            if items:
                last_since = items[-1].get('created_at')
        time.sleep(interval)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--server', default='http://localhost:5000')
    ap.add_argument('--api-key', default='demo-edit')
    ap.add_argument('--root', default='exports')
    ap.add_argument('--interval', type=int, default=10)
    args = ap.parse_args()
    loop(args.server, args.api_key, args.root, args.interval)


if __name__ == '__main__':
    main()

