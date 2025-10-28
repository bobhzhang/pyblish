# Pyblish Web Assets (v1.0.0)

A lightweight web asset manager for a Pyblish-based Maya pipeline.

- Web server (Flask) for browsing, downloading, deleting assets
- Pyblish plugins for publishing from Maya
- Simple sync agent skeleton for future two-way sync

## What’s new in 2.0.0
- Clear usage model: upload via Maya plugin only; download via browser (public endpoints)
- Browser auth UX: Apply button validates X-API-Key and shows result (no persistence)
- Hard deletion: admin can delete entire assets or specific versions
- Cleaned layout and archived legacy standalone web implementation

## Project structure
```
web_server/         # Flask web service (API + UI)
plugins/            # Pyblish plugins (collect/validate/extract/integrate)
scripts/            # Tools (e.g. sync_agent.py)
config/             # Families and settings
utils/              # Helper modules for pipeline
archive/            # Archived legacy (e.g. web_integration/, README_STANDALONE.md)
exports/            # Local exports (ignored in Git)
thumbnails/         # Local thumbnails (ignored in Git)
```

## Authentication & roles
- Header: `X-API-Key`
- Built-in keys (dev/demo):
  - `bob_key`: admin (delete allowed)

Notes
- Browser will not store the key. Enter it each visit and click Apply to validate.
- Public (no auth): package/file downloads
- Protected (requires key): list/detail/comments/status/edit/delete

## Usage
### Run the server
```bash
# From repository root
python -m web_server.app  # or: set WEB_SERVER_PORT=5000 and run
# Browse UI
http://127.0.0.1:5000/ui
```

### Browser (download only; list/detail need key)
- Enter API Key (e.g. `bob_key`) and click Apply → UI shows ✓/✗
- Download ZIP from Actions → "download zip"

### Maya publish (upload only)
- Set environment variables before launching Maya:
```bash
set WEB_SERVER_URL=http://127.0.0.1:5000
set WEB_API_KEY=bob_key
```
- Use Pyblish to publish → the integrate plugin calls the web API with headers

## Endpoints (selected)
- GET `/api/assets` (viewer+) → list assets
- GET `/api/assets/<asset_id>` (viewer+) → detail
- GET `/api/assets/<asset_id>/package?version=N` (public) → zip package
- DELETE `/api/assets/<asset_id>` (admin) → hard delete asset
- DELETE `/api/assets/<asset_id>/versions/<version>` (admin) → hard delete version

## Development
- Python 3.9+
- Install Flask (and requests for local tests)

```bash
pip install flask requests
python -m web_server.app
```

## Notes
- SQLite DB and storage live under `web_server/`
- Runtime and large files are ignored by Git via `.gitignore`

## License
TBD

