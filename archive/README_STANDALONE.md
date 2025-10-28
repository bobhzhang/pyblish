# Pyblish Production Pipeline (Standalone Version)

## 🎯 Overview

This is a **standalone version** of the Pyblish production pipeline that **requires NO external dependencies** beyond Python standard library and Maya. No Flask, no pip installs, no virtual environments needed!

## ✨ Features

### 🔧 **Zero Dependencies**
- Uses only Python standard library
- No Flask, requests, or other external packages
- Works out-of-the-box with Maya

### 🌐 **Built-in Web Server**
- Standalone HTTP server using `http.server`
- Real-time asset dashboard
- RESTful API for integration
- Automatic browser opening

### 📦 **Complete Pipeline**
- **Collection**: Gather assets from Maya scene
- **Validation**: Check quality standards (extensible)
- **Extraction**: Export assets in multiple formats
- **Integration**: Upload to web pipeline

### 🎭 **Asset Types Supported**
- **Models**: 3D geometry with statistics
- **Rigs**: Joint hierarchies and controls
- **Materials**: Shaders and textures
- **Animations**: Keyframe data and motion
- **Cameras**: Shot cameras with settings
- **Scene**: Global scene configuration

## 🚀 Quick Start

### **Method 1: In Maya (Recommended)**

```python
# In Maya Script Editor
exec(open(r'D:\pyblish\start_standalone_pipeline.py').read())
main()
```

### **Method 2: Command Line**

```bash
cd D:\pyblish
python start_standalone_pipeline.py
```

### **Method 3: Web Server Only**

```bash
cd D:\pyblish\web_integration
python app_standalone.py
```

## 📋 Usage Steps

### 1. **Start the Pipeline**
Run the startup script in Maya - it will:
- ✅ Start standalone web server (port 5000)
- ✅ Register all Pyblish plugins
- ✅ Create production test scene
- ✅ Open web dashboard automatically

### 2. **Run Collection**
```python
# Collect all assets from scene
context, results = run_full_pipeline()
```

### 3. **View Results**
- **Web Dashboard**: http://localhost:5000
- **API Endpoint**: http://localhost:5000/api/assets
- **Maya Console**: Detailed plugin execution logs

## 🗂️ File Structure

```
D:\pyblish\
├── plugins/
│   ├── collect/                    # Asset collection plugins
│   │   ├── collect_models.py       # 3D model collection
│   │   ├── collect_rigs.py         # Rig and joint collection
│   │   ├── collect_materials.py    # Material and texture collection
│   │   ├── collect_animations.py   # Animation data collection
│   │   ├── collect_cameras.py      # Camera collection
│   │   └── collect_scene.py        # Scene settings collection
│   ├── extract/                    # Asset export plugins
│   │   └── extract_models.py       # Multi-format model export
│   └── integrate/                  # Pipeline integration plugins
│       └── integrate_web_pipeline.py # Web server integration
├── web_integration/
│   ├── app_standalone.py           # 🆕 Standalone web server
│   ├── app.py                      # Original Flask version
│   ├── assets/                     # Uploaded asset files
│   ├── metadata/                   # Asset database (JSON)
│   └── thumbnails/                 # Asset thumbnails
├── config/
│   └── settings.py                 # Pipeline configuration
├── utils/
│   └── maya_utils.py               # Maya utility functions
├── start_standalone_pipeline.py    # 🆕 Main startup script
├── start_pipeline.py               # Original Flask version
└── run_pipeline_demo.py            # Pipeline demonstration
```

## 🔧 Configuration

### **Web Server Settings**
Edit `web_integration/app_standalone.py`:
```python
PORT = 5000                    # Server port
UPLOAD_FOLDER = 'assets'       # Asset storage directory
METADATA_FOLDER = 'metadata'   # Database directory
```

### **Plugin Orders**
Edit `config/settings.py`:
```python
DEFAULT_PLUGIN_ORDERS = {
    # Collection (0-99)
    "collect_scene": 10,
    "collect_models": 20,
    "collect_materials": 25,
    "collect_rigs": 30,
    "collect_cameras": 35,
    "collect_animations": 40,
    
    # Extraction (200-299)
    "extract_models": 210,
    
    # Integration (300-399)
    "integrate_web_pipeline": 320,
}
```

## 📊 Web Dashboard Features

### **Main Dashboard** (http://localhost:5000)
- Pipeline flow visualization
- Asset statistics by type
- Recent assets overview
- Real-time updates

### **Detailed Dashboard** (http://localhost:5000/dashboard)
- Complete asset listing
- Export and integration status
- Asset metadata and details
- Family-based filtering

### **API Endpoints**
- `GET /api/assets` - List all assets
- `GET /api/assets/{id}` - Get specific asset
- `GET /api/stats` - Pipeline statistics
- `POST /api/assets` - Create new asset

## 🎭 Test Scene Assets

The automatic test scene includes:

### **Models**
- `Hero_MainCharacter_01` - Main character cube
- `Prop_MagicOrb_01` - Magical prop sphere
- `Env_Ground_01` - Environment ground plane
- `Vehicle_Spaceship_01` - Vehicle cylinder

### **Rigs**
- Character rig: `Character_Root_jnt` → `Character_Spine_jnt` → `Character_Head_jnt`
- Facial rig: `Facial_Root_jnt` → `Facial_Jaw_jnt`

### **Materials**
- `Hero_Skin_Material` - Character skin shader
- `Prop_Magic_Material` - Magical prop shader
- `Env_Ground_Material` - Environment shader

### **Cameras**
- `Shot_001_Camera` - Wide shot (50mm lens)
- `Shot_002_CloseUp_Camera` - Close-up shot (85mm lens)

### **Animation**
- Character bounce and rotation (24 frames)
- Prop scaling and spinning animation
- Camera movement and rotation

## 🔍 Troubleshooting

### **Web Server Won't Start**
```python
# Check if port is in use
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
result = sock.connect_ex(('localhost', 5000))
if result == 0:
    print("Port 5000 is in use")
```

### **Plugins Not Found**
```python
# Check plugin registration
import pyblish.api
plugins = pyblish.api.discover()
print(f"Found {len(plugins)} plugins")
for plugin in plugins:
    print(f"  - {plugin.__name__}")
```

### **Maya Import Errors**
```python
# Test Maya availability
try:
    import maya.cmds as cmds
    print("Maya available")
except ImportError:
    print("Maya not available - run inside Maya")
```

## 🆚 Standalone vs Flask Version

| Feature | Standalone | Flask |
|---------|------------|-------|
| Dependencies | ✅ None | ❌ Flask, requests |
| Setup | ✅ Instant | ❌ pip install |
| File Upload | ⚠️ Limited | ✅ Full support |
| Templates | ✅ Embedded | ✅ Separate files |
| Performance | ✅ Good | ✅ Better |
| Production Ready | ⚠️ Basic | ✅ Full |

## 🎯 Next Steps

1. **Extend Validation**: Add quality check plugins
2. **Add Export Formats**: Support more file types
3. **Database Integration**: Connect to production database
4. **User Authentication**: Add login system
5. **File Management**: Improve upload handling

## 📞 Support

This standalone version provides a complete, dependency-free Pyblish pipeline perfect for:
- ✅ Quick prototyping
- ✅ Educational purposes  
- ✅ Environments with restricted package installation
- ✅ Maya-only workflows

For production environments with full web features, consider the Flask version with proper database integration.
