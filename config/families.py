"""
Pyblish Asset Families Configuration

This module defines asset families and their properties for the production pipeline.
"""

from collections import namedtuple

# Family definition structure
FamilyDefinition = namedtuple('FamilyDefinition', [
    'name',           # Family name
    'label',          # Display label
    'description',    # Description
    'icon',           # FontAwesome icon name
    'extensions',     # Supported file extensions
    'requirements',   # Required attributes/components
    'optional',       # Optional attributes/components
])

# Asset Family Definitions
FAMILIES = {
    "model": FamilyDefinition(
        name="model",
        label="3D Model",
        description="3D geometry models including characters, props, and environments",
        icon="cube",
        extensions=[".ma", ".mb", ".fbx", ".obj", ".abc"],
        requirements=[
            "geometry",
            "uv_coordinates",
            "proper_naming",
        ],
        optional=[
            "materials",
            "textures",
            "blend_shapes",
        ]
    ),
    
    "rig": FamilyDefinition(
        name="rig",
        label="Character Rig",
        description="Character and object rigging setups with controls and constraints",
        icon="user",
        extensions=[".ma", ".mb"],
        requirements=[
            "skeleton",
            "controls",
            "skin_weights",
            "proper_naming",
        ],
        optional=[
            "facial_rig",
            "custom_attributes",
            "space_switching",
        ]
    ),
    
    "animation": FamilyDefinition(
        name="animation",
        label="Animation",
        description="Animation data including keyframes and motion capture",
        icon="play",
        extensions=[".ma", ".mb", ".abc", ".fbx"],
        requirements=[
            "keyframes",
            "time_range",
            "frame_rate",
        ],
        optional=[
            "motion_blur",
            "animation_layers",
            "constraints",
        ]
    ),
    
    "material": FamilyDefinition(
        name="material",
        label="Material",
        description="Shading materials and surface properties",
        icon="paint-brush",
        extensions=[".ma", ".mb"],
        requirements=[
            "shader_network",
            "material_assignment",
        ],
        optional=[
            "displacement",
            "subsurface_scattering",
            "emission",
        ]
    ),
    
    "texture": FamilyDefinition(
        name="texture",
        label="Texture",
        description="Texture maps and image files for materials",
        icon="image",
        extensions=[".jpg", ".png", ".tga", ".exr", ".hdr", ".tiff"],
        requirements=[
            "resolution",
            "color_space",
            "file_format",
        ],
        optional=[
            "mip_maps",
            "compression",
            "metadata",
        ]
    ),
    
    "scene": FamilyDefinition(
        name="scene",
        label="Scene Setup",
        description="Scene configurations including render settings and environment",
        icon="globe",
        extensions=[".ma", ".mb"],
        requirements=[
            "render_settings",
            "scene_scale",
            "units",
        ],
        optional=[
            "environment_lighting",
            "post_effects",
            "render_layers",
        ]
    ),
    
    "camera": FamilyDefinition(
        name="camera",
        label="Camera",
        description="Camera setups and animation for shots",
        icon="camera",
        extensions=[".ma", ".mb", ".abc"],
        requirements=[
            "camera_transform",
            "focal_length",
            "film_gate",
        ],
        optional=[
            "depth_of_field",
            "motion_blur",
            "camera_shake",
        ]
    ),
    
    "lighting": FamilyDefinition(
        name="lighting",
        label="Lighting Setup",
        description="Lighting rigs and illumination setups",
        icon="lightbulb-o",
        extensions=[".ma", ".mb"],
        requirements=[
            "light_sources",
            "shadows",
            "exposure",
        ],
        optional=[
            "global_illumination",
            "caustics",
            "volumetrics",
        ]
    ),
}

# Family Groups for UI organization
FAMILY_GROUPS = {
    "Modeling": ["model", "material", "texture"],
    "Rigging": ["rig"],
    "Animation": ["animation", "camera"],
    "Lighting": ["lighting", "scene"],
}

# Family Dependencies
FAMILY_DEPENDENCIES = {
    "rig": ["model"],
    "animation": ["rig"],
    "material": ["texture"],
    "lighting": ["model", "material"],
}

# Family Validation Rules
FAMILY_VALIDATION_RULES = {
    "model": [
        "validate_naming",
        "validate_polycount",
        "validate_uv_coordinates",
        "validate_geometry_cleanup",
    ],
    "rig": [
        "validate_naming",
        "validate_skeleton_hierarchy",
        "validate_skin_weights",
        "validate_controls",
    ],
    "animation": [
        "validate_naming",
        "validate_time_range",
        "validate_keyframes",
        "validate_frame_rate",
    ],
    "material": [
        "validate_naming",
        "validate_shader_network",
        "validate_texture_paths",
        "validate_material_assignment",
    ],
    "texture": [
        "validate_naming",
        "validate_resolution",
        "validate_color_space",
        "validate_file_format",
    ],
    "scene": [
        "validate_naming",
        "validate_render_settings",
        "validate_scene_scale",
        "validate_units",
    ],
    "camera": [
        "validate_naming",
        "validate_camera_settings",
        "validate_animation",
    ],
    "lighting": [
        "validate_naming",
        "validate_light_setup",
        "validate_shadows",
        "validate_exposure",
    ],
}

# Family Export Formats
FAMILY_EXPORT_FORMATS = {
    "model": ["fbx", "obj", "alembic"],
    "rig": ["maya_binary", "maya_ascii"],
    "animation": ["fbx", "alembic", "maya_binary"],
    "material": ["maya_binary", "maya_ascii"],
    "texture": ["original_format"],
    "scene": ["maya_binary", "maya_ascii"],
    "camera": ["alembic", "maya_binary"],
    "lighting": ["maya_binary", "maya_ascii"],
}


def get_family(name):
    """Get family definition by name."""
    return FAMILIES.get(name)


def get_family_names():
    """Get list of all family names."""
    return list(FAMILIES.keys())


def get_family_by_extension(extension):
    """Get families that support the given file extension."""
    matching_families = []
    for family_name, family_def in FAMILIES.items():
        if extension.lower() in [ext.lower() for ext in family_def.extensions]:
            matching_families.append(family_name)
    return matching_families


def get_validation_rules(family_name):
    """Get validation rules for a specific family."""
    return FAMILY_VALIDATION_RULES.get(family_name, [])


def get_export_formats(family_name):
    """Get export formats for a specific family."""
    return FAMILY_EXPORT_FORMATS.get(family_name, [])


def get_family_dependencies(family_name):
    """Get dependencies for a specific family."""
    return FAMILY_DEPENDENCIES.get(family_name, [])
