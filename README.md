# Pyblish Web Assets (v2.0.0)

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


## 使用指南 (End-to-End Guide)

### 1) 前期准备
- 仓库路径建议保持为 `D:\pyblish`（`userSetup.py` 默认从此路径注册 `plugins/`）
- Python 环境参考下文 Development，小型依赖仅需 `flask`、`requests`
- 若 Maya 端未安装 Pyblish，请将其安装到 `mayapy`（按你本机路径替换示例中的 Maya 版本）：

```bat
"C:\Program Files\Autodesk\Maya2022\bin\mayapy.exe" -m pip install -U pip
"C:\Program Files\Autodesk\Maya2022\bin\mayapy.exe" -m pip install pyblish-base pyblish-lite
```

- 将仓库根目录的 `userSetup.py` 复制到你的 Maya 脚本目录，例如：
  - `C:\Users\<User>\Documents\maya\2022\scripts\userSetup.py`

### 2) 启动 Web 服务
- 在仓库根目录运行（默认服务地址 `http://127.0.0.1:5000`）：

```bat
.\.venv\Scripts\python.exe -c "from web_server.app import app; app.run(host='127.0.0.1', port=5000, debug=False)"
```

- 浏览器打开 UI：`http://127.0.0.1:5000/ui`
  - 页面不会持久保存 Key；每次进入请输入 `bob_key`，点击 Apply 即时校验（✓/✗）

### 3) 启动 Maya（.bat 注入变量；不做全局持久化）
- 建议使用下面的 `.bat` 启动脚本，仅在本次会话注入变量：

```bat
@echo off
set WEB_SERVER_URL=http://127.0.0.1:5000
set WEB_API_KEY=bob_key
start "" "C:\Program Files\Autodesk\Maya2022\bin\maya.exe"
```

说明：
- `WEB_SERVER_URL` 指定 Web 服务地址
- `WEB_API_KEY` 为管理员 Key（上传/删除），仅对本次启动会话生效，符合“不持久化”的要求

### 4) 在 Maya 内发布（Pyblish）
- 启动后菜单栏出现 `Pyblish` 菜单 → 选择 `Show Pyblish Lite`
- 在侧边的 `Instance Selector` 面板勾选/取消要发布的实例
- 在 Pyblish Lite 中点击 `Run` 开始发布
  - 集成插件会读取环境变量中的 `WEB_SERVER_URL` 与 `WEB_API_KEY`，以稳定 `asset_id` 和自增 `version` 上传

### 5) Web 端查看与下载
- 打开 `http://127.0.0.1:5000/ui`，输入 `bob_key` 并点击 Apply（看到 ✓ Key OK）
- 在列表/详情页面可：
  - 下载打包 ZIP：`download zip`
  - 下载单文件（如 `.fbx/.obj/.ma`）
  - 删除资产/删除版本（仅 admin，且为硬删除）
- 也可绕开 UI 直接拼接公开下载链接（无需 Key）：
  - 打包 ZIP：`/api/assets/<asset_id>/package?version=N`
  - 单文件：`/api/assets/<asset_id>/download?version=N&format=fbx`

### 6) 流程图（简图）
```mermaid
flowchart TD
  A[准备: 代码 + venv + userSetup.py] --> B[启动 Web 服务 127.0.0.1:5000]
  B --> C[启动 Maya (.bat 注入 WEB_API_KEY/WEB_SERVER_URL)]
  C --> D[Pyblish Lite 选择实例 → Run]
  D --> E[服务器保存资产/版本]
  E --> F[浏览器 /ui 输入 bob_key 点击 Apply]
  F --> G[下载包/单文件 或 管理(删除)]
```

### 7) 故障排查（速记）
- UI 显示 Key 无效：确认输入 `bob_key` 并点击 Apply；服务是否运行在 `5000` 端口
- 看不到 `Pyblish` 菜单：检查 `userSetup.py` 是否在 Maya 脚本目录、`mayapy` 是否已安装 `pyblish-*`
- 上传 401/403：确认启动 Maya 的方式已注入 `WEB_API_KEY`
- 下载 404：版本/格式不存在或 `asset_id` 拼写不对
- 服务端报错：查看启动 Web 服务的终端输出，或访问 `/api/stats` 自检

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
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
python.exe -m pip install flask requests

.\.venv\Scripts\python.exe -c "from web_server.app import app; app.run(host='127.0.0.1', port=5000, debug=False)"

## Notes
- SQLite DB and storage live under `web_server/`
- Runtime and large files are ignored by Git via `.gitignore`

## License
TBD

