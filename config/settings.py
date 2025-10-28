"""
Pyblish Production Pipeline Settings

This module contains configuration settings for the Pyblish production pipeline.
"""

# Pipeline Settings
PIPELINE_NAME = "Production Pipeline"
PIPELINE_VERSION = "1.0.0"

# Asset Families
ASSET_FAMILIES = [
    "model",      # 3D models
    "rig",        # Character/object rigs
    "animation",  # Animation data
    "material",   # Materials and shaders
    "texture",    # Texture files
    "scene",      # Scene settings and configurations
    "camera",     # Camera setups
    "lighting",   # Lighting setups
]

# File Extensions
SUPPORTED_EXTENSIONS = {
    "model": [".ma", ".mb", ".fbx", ".obj", ".abc"],
    "rig": [".ma", ".mb"],
    "animation": [".ma", ".mb", ".abc", ".fbx"],
    "material": [".ma", ".mb"],
    "texture": [".jpg", ".png", ".tga", ".exr", ".hdr", ".tiff"],
    "scene": [".ma", ".mb"],
    "camera": [".ma", ".mb", ".abc"],
    "lighting": [".ma", ".mb"],
}

# Naming Conventions
NAMING_PATTERNS = {
    "model": r"^[A-Z][a-zA-Z0-9_]*_model_v\d{3}$",
    "rig": r"^[A-Z][a-zA-Z0-9_]*_rig_v\d{3}$",
    "animation": r"^[A-Z][a-zA-Z0-9_]*_anim_v\d{3}$",
    "material": r"^[A-Z][a-zA-Z0-9_]*_mat_v\d{3}$",
    "texture": r"^[A-Z][a-zA-Z0-9_]*_tex_v\d{3}$",
    "scene": r"^[A-Z][a-zA-Z0-9_]*_scene_v\d{3}$",
}

# Quality Standards
QUALITY_STANDARDS = {
    "max_polycount": {
        "character": 50000,
        "prop": 10000,
        "environment": 100000,
    },
    "texture_resolution": {
        "character": 2048,
        "prop": 1024,
        "environment": 4096,
    },
    "required_uv_sets": ["map1"],
    "max_texture_size_mb": 50,
}

# Export Settings
EXPORT_SETTINGS = {
    "fbx": {
        "version": "FBX201800",
        "ascii": False,
        "triangulate": True,
        "smoothing_groups": True,
        "tangents_and_binormals": True,
    },
    "obj": {
        "groups": True,
        "materials": True,
        "smoothing": True,
        "normals": True,
    },
    "alembic": {
        "uv_write": True,
        "write_visibility": True,
        "write_face_sets": True,
        "data_format": "ogawa",
    },
}

# Directory Structure
DIRECTORY_STRUCTURE = {
    "assets": "assets",
    "shots": "shots",
    "publish": "publish",
    "work": "work",
    "cache": "cache",
    "textures": "textures",
    "references": "references",
}

# Version Control Settings
VERSION_CONTROL = {
    "enabled": True,
    "auto_commit": False,
    "commit_message_template": "{asset_type}: {asset_name} v{version}",
    "branch_naming": "feature/{asset_name}",
}

# Integration Settings
INTEGRATION = {
    "asset_database": {
        "enabled": True,
        "update_metadata": True,
        "create_thumbnails": True,
    },
    "notification": {
        "enabled": True,
        "email_on_success": False,
        "email_on_failure": True,
    },
}

# Plugin Order Ranges
PLUGIN_ORDER_RANGES = {
    "collect": (0, 99),
    "validate": (100, 199),
    "extract": (200, 299),
    "integrate": (300, 399),
}

# Default Plugin Orders
DEFAULT_PLUGIN_ORDERS = {
    # Collection
    "collect_scene": 10,
    "collect_models": 20,
    "collect_materials": 25,
    "collect_rigs": 30,
    "collect_cameras": 35,
    "collect_animations": 40,
    
    # Validation
    "validate_naming": 110,
    "validate_polycount": 120,
    "validate_materials": 130,
    "validate_scene_settings": 140,
    
    # Extraction
    "extract_models": 210,
    "extract_fbx": 215,
    "extract_obj": 220,
    "extract_alembic": 230,
    "extract_textures": 240,

    # Integration
    "integrate_version_control": 310,
    "integrate_web_pipeline": 320,
    "integrate_asset_database": 325,
    "integrate_pipeline": 330,
}

# Logging Configuration
LOGGING = {
    "level": "INFO",
    "format": "[%(levelname)s] %(name)s: %(message)s",
    "file_logging": True,
    "log_directory": "logs",
}
