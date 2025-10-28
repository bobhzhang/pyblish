"""
Maya Utility Functions

This module contains utility functions for working with Maya in the Pyblish pipeline.
"""

import os
import re


def get_maya_selection():
    """Get currently selected objects in Maya."""
    try:
        import maya.cmds as cmds
        return cmds.ls(selection=True, long=True) or []
    except ImportError:
        print("Maya not available")
        return []


def get_scene_name():
    """Get the current Maya scene name."""
    try:
        import maya.cmds as cmds
        scene_path = cmds.file(query=True, sceneName=True)
        if scene_path:
            return os.path.basename(scene_path)
        return "untitled"
    except ImportError:
        print("Maya not available")
        return "untitled"


def get_scene_path():
    """Get the current Maya scene path."""
    try:
        import maya.cmds as cmds
        return cmds.file(query=True, sceneName=True) or ""
    except ImportError:
        print("Maya not available")
        return ""


def get_frame_range():
    """Get the current frame range from Maya."""
    try:
        import maya.cmds as cmds
        start_frame = cmds.playbackOptions(query=True, minTime=True)
        end_frame = cmds.playbackOptions(query=True, maxTime=True)
        return int(start_frame), int(end_frame)
    except ImportError:
        print("Maya not available")
        return 1, 100


def get_current_frame():
    """Get the current frame in Maya."""
    try:
        import maya.cmds as cmds
        return int(cmds.currentTime(query=True))
    except ImportError:
        print("Maya not available")
        return 1


def get_fps():
    """Get the current frames per second setting."""
    try:
        import maya.cmds as cmds
        time_unit = cmds.currentUnit(query=True, time=True)
        fps_mapping = {
            'game': 15,
            'film': 24,
            'pal': 25,
            'ntsc': 30,
            'show': 48,
            'palf': 50,
            'ntscf': 60
        }
        return fps_mapping.get(time_unit, 24)
    except ImportError:
        print("Maya not available")
        return 24


def get_scene_units():
    """Get the current scene units."""
    try:
        import maya.cmds as cmds
        linear_unit = cmds.currentUnit(query=True, linear=True)
        angular_unit = cmds.currentUnit(query=True, angle=True)
        time_unit = cmds.currentUnit(query=True, time=True)
        return {
            'linear': linear_unit,
            'angular': angular_unit,
            'time': time_unit
        }
    except ImportError:
        print("Maya not available")
        return {'linear': 'cm', 'angular': 'deg', 'time': 'film'}


def get_objects_by_type(object_type):
    """Get all objects of a specific type in the scene."""
    try:
        import maya.cmds as cmds
        return cmds.ls(type=object_type, long=True) or []
    except ImportError:
        print("Maya not available")
        return []


def get_meshes():
    """Get all mesh objects in the scene."""
    return get_objects_by_type('mesh')


def get_cameras():
    """Get all camera objects in the scene."""
    return get_objects_by_type('camera')


def get_lights():
    """Get all light objects in the scene."""
    light_types = ['directionalLight', 'pointLight', 'spotLight', 'areaLight']
    lights = []
    for light_type in light_types:
        lights.extend(get_objects_by_type(light_type))
    return lights


def get_materials():
    """Get all material nodes in the scene."""
    try:
        import maya.cmds as cmds
        materials = []
        shader_types = ['lambert', 'blinn', 'phong', 'surfaceShader', 'standardSurface']
        for shader_type in shader_types:
            materials.extend(cmds.ls(type=shader_type) or [])
        return materials
    except ImportError:
        print("Maya not available")
        return []


def get_polycount(mesh_list=None):
    """Get polygon count for specified meshes or all meshes."""
    try:
        import maya.cmds as cmds
        if mesh_list is None:
            mesh_list = get_meshes()
        
        total_faces = 0
        total_vertices = 0
        
        for mesh in mesh_list:
            try:
                face_count = cmds.polyEvaluate(mesh, face=True) or 0
                vertex_count = cmds.polyEvaluate(mesh, vertex=True) or 0
                total_faces += face_count
                total_vertices += vertex_count
            except:
                continue
                
        return {'faces': total_faces, 'vertices': total_vertices}
    except ImportError:
        print("Maya not available")
        return {'faces': 0, 'vertices': 0}


def validate_naming_convention(name, pattern):
    """Validate if a name follows the specified naming convention."""
    return bool(re.match(pattern, name))


def get_uv_sets(mesh):
    """Get UV sets for a mesh."""
    try:
        import maya.cmds as cmds
        return cmds.polyUVSet(mesh, query=True, allUVSets=True) or []
    except ImportError:
        print("Maya not available")
        return []


def has_uv_coordinates(mesh):
    """Check if a mesh has UV coordinates."""
    uv_sets = get_uv_sets(mesh)
    return len(uv_sets) > 0


def get_texture_files():
    """Get all texture file nodes in the scene."""
    try:
        import maya.cmds as cmds
        file_nodes = cmds.ls(type='file') or []
        texture_files = []
        
        for node in file_nodes:
            file_path = cmds.getAttr(f"{node}.fileTextureName")
            if file_path:
                texture_files.append({
                    'node': node,
                    'path': file_path,
                    'exists': os.path.exists(file_path)
                })
        
        return texture_files
    except ImportError:
        print("Maya not available")
        return []


def get_missing_textures():
    """Get list of missing texture files."""
    texture_files = get_texture_files()
    return [tex for tex in texture_files if not tex['exists']]


def create_workspace_mel():
    """Create a workspace.mel file for the current project."""
    try:
        import maya.cmds as cmds
        workspace_path = cmds.workspace(query=True, rootDirectory=True)
        mel_content = '''//Maya 2023 Project Definition

workspace -fr "fluidCache" "cache/nCache/fluid";
workspace -fr "images" "images";
workspace -fr "offlineEdit" "scenes/edits";
workspace -fr "STEP_DC" "data";
workspace -fr "CATIAV5_DC" "data";
workspace -fr "sound" "sound";
workspace -fr "furFiles" "renderData/fur/furFiles";
workspace -fr "depth" "renderData/depth";
workspace -fr "CATIAV4_DC" "data";
workspace -fr "autoSave" "autosave";
workspace -fr "diskCache" "data";
workspace -fr "fileCache" "cache/nCache";
workspace -fr "STEP_DC" "data";
workspace -fr "3dPaintTextures" "sourceimages/3dPaintTextures";
workspace -fr "mel" "scripts";
workspace -fr "particles" "cache/particles";
workspace -fr "scene" "scenes";
workspace -fr "mayaAscii" "scenes";
workspace -fr "mayaBinary" "scenes";
workspace -fr "move" "data";
workspace -fr "sourceImages" "sourceimages";
workspace -fr "clips" "clips";
workspace -fr "templates" "assets";
workspace -fr "OBJexport" "data";
workspace -fr "furEqualMap" "renderData/fur/furEqualMap";
'''
        
        mel_file_path = os.path.join(workspace_path, "workspace.mel")
        with open(mel_file_path, 'w') as f:
            f.write(mel_content)
        
        return mel_file_path
    except ImportError:
        print("Maya not available")
        return None
