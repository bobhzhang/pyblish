"""
Storage helpers. Files are stored under web_server/storage_root:
- assets/{asset_id}/v{version}/{filename}
- thumbnails/{asset_id}_v{version}.jpg
All paths are relative to this module directory by default.
"""
from __future__ import annotations
import os
import shutil
from typing import Tuple

ROOT = os.path.join(os.path.dirname(__file__), "storage_root")
ASSETS_DIR = os.path.join(ROOT, "assets")
THUMBS_DIR = os.path.join(ROOT, "thumbnails")

for d in (ROOT, ASSETS_DIR, THUMBS_DIR):
    os.makedirs(d, exist_ok=True)


def asset_dir(asset_id: str, version: int) -> str:
    path = os.path.join(ASSETS_DIR, asset_id, f"v{int(version)}")
    os.makedirs(path, exist_ok=True)
    return path


def save_upload(asset_id: str, version: int, src_path: str, filename: str | None = None) -> Tuple[str, int]:
    """Move uploaded temp file into asset storage location.
    Returns (relative_path_for_db, size_bytes).
    """
    fname = filename or os.path.basename(src_path)
    dst_dir = asset_dir(asset_id, version)
    dst = os.path.join(dst_dir, fname)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.move(src_path, dst)
    size = os.path.getsize(dst)
    rel = os.path.relpath(dst, ROOT).replace("\\", "/")
    return rel, size


def absolute_from_rel(rel_path: str) -> str:
    return os.path.normpath(os.path.join(ROOT, rel_path))


def package_version(asset_id: str, version: int) -> str:
    """Create a zip package path (create on demand in app)."""
    out_dir = asset_dir(asset_id, version)
    zip_path = os.path.join(out_dir, f"{asset_id}_v{version}.zip")
    return zip_path




def delete_asset_storage(asset_id: str) -> None:
    """Remove all asset files and thumbnails for given asset_id."""
    # Remove asset directory
    import glob
    asset_path = os.path.join(ASSETS_DIR, asset_id)
    if os.path.isdir(asset_path):
        shutil.rmtree(asset_path, ignore_errors=True)
    # Remove thumbnails
    if os.path.isdir(THUMBS_DIR):
        for p in glob.glob(os.path.join(THUMBS_DIR, f"{asset_id}_*")):
            try:
                os.remove(p)
            except Exception:
                pass



def delete_version_storage(asset_id: str, version: int) -> None:
    """Remove a specific version directory and its thumbnail."""
    vdir = os.path.join(ASSETS_DIR, asset_id, f"v{int(version)}")
    if os.path.isdir(vdir):
        shutil.rmtree(vdir, ignore_errors=True)
    thumb = os.path.join(THUMBS_DIR, f"{asset_id}_v{int(version)}.jpg")
    try:
        if os.path.isfile(thumb):
            os.remove(thumb)
    except Exception:
        pass
