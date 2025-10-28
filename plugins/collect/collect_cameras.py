"""
Collect Cameras Plugin

This plugin collects camera assets from the Maya scene.
It identifies cameras, their settings, and animation data.
"""

import pyblish.api
import sys
import os

# Add utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.maya_utils import get_scene_name, get_frame_range
from config.settings import DEFAULT_PLUGIN_ORDERS


class CollectCameras(pyblish.api.ContextPlugin):
    """Collect camera assets from the scene."""
    
    label = "Collect Cameras"
    order = DEFAULT_PLUGIN_ORDERS.get("collect_cameras", 35)
    hosts = ["maya"]
    
    def process(self, context):
        """Main processing function."""
        print("\n" + "="*50)
        print("[Collect Cameras] Starting camera collection...")
        print("="*50)
        
        # Get scene information
        scene_name = get_scene_name()
        print(f"[Collect Cameras] Scene: {scene_name}")
        
        # Get cameras
        cameras = self.get_cameras()
        print(f"[Collect Cameras] Found {len(cameras)} cameras")
        
        if not cameras:
            print("[Collect Cameras] No cameras found in scene")
            return
        
        # Create instances for each camera
        for camera_data in cameras:
            camera_name = camera_data["name"]
            instance = context.create_instance(camera_name)
            
            # Get camera animation data
            animation_data = self.get_camera_animation(camera_data["transform"])
            
            instance.data.update({
                "family": "Camera",  # Display name in Pyblish UI
                "families": ["camera", "shot", "cinematography"],  # Tags for validation
                "asset": camera_name,
                "camera_transform": camera_data["transform"],
                "camera_shape": camera_data["shape"],
                "camera_settings": camera_data["settings"],
                "is_animated": animation_data["is_animated"],
                "keyframe_count": animation_data["keyframe_count"],
                "animation_range": animation_data["animation_range"],
                "focal_length": camera_data["settings"].get("focal_length"),
                "film_back": camera_data["settings"].get("film_back"),
                "near_clip": camera_data["settings"].get("near_clip"),
                "far_clip": camera_data["settings"].get("far_clip"),
                "scene": scene_name,
                "plugin": self.__class__.__name__,
                "icon": "video-camera",
                "description": f"Camera with focal length {camera_data['settings'].get('focal_length', 'unknown')}mm",
                "publish": True
            })
            
            # Add camera objects to instance
            instance.append(camera_data["transform"])
            instance.append(camera_data["shape"])
            
            print(f"[Collect Cameras] Created instance: {camera_name}")
            print(f"  - Focal Length: {camera_data['settings'].get('focal_length')}mm")
            print(f"  - Film Back: {camera_data['settings'].get('film_back')}")
            print(f"  - Animated: {animation_data['is_animated']}")
            if animation_data["is_animated"]:
                print(f"  - Keyframes: {animation_data['keyframe_count']}")
            print(f"  - Families: {instance.data['families']}")
        
        print(f"[Collect Cameras] Collection completed - {len(cameras)} cameras")
        print("="*50 + "\n")
    
    def get_cameras(self):
        """Get all camera objects in the scene."""
        try:
            import maya.cmds as cmds
            
            # Get all camera shapes
            camera_shapes = cmds.ls(type='camera', long=True) or []
            cameras = []
            
            for shape in camera_shapes:
                # Get camera transform
                transforms = cmds.listRelatives(shape, parent=True, type='transform', fullPath=True) or []
                if not transforms:
                    continue
                
                transform = transforms[0]
                camera_name = transform.split('|')[-1]
                
                # Skip default cameras unless they're modified
                if camera_name in ['persp', 'top', 'front', 'side']:
                    if not self.is_camera_modified(transform, shape):
                        continue
                
                # Get camera settings
                settings = self.get_camera_settings(shape)
                
                cameras.append({
                    "name": camera_name,
                    "transform": transform,
                    "shape": shape,
                    "settings": settings
                })
            
            return cameras
            
        except ImportError:
            print("[Collect Cameras] Maya not available")
            return []
    
    def get_camera_settings(self, camera_shape):
        """Get camera settings and properties."""
        try:
            import maya.cmds as cmds
            
            # Get basic camera attributes
            focal_length = cmds.getAttr(f"{camera_shape}.focalLength")
            horizontal_film_aperture = cmds.getAttr(f"{camera_shape}.horizontalFilmAperture")
            vertical_film_aperture = cmds.getAttr(f"{camera_shape}.verticalFilmAperture")
            near_clip = cmds.getAttr(f"{camera_shape}.nearClipPlane")
            far_clip = cmds.getAttr(f"{camera_shape}.farClipPlane")
            
            # Get film back size
            film_back = (horizontal_film_aperture, vertical_film_aperture)
            
            # Get additional settings
            orthographic = cmds.getAttr(f"{camera_shape}.orthographic")
            orthographic_width = cmds.getAttr(f"{camera_shape}.orthographicWidth") if orthographic else None
            
            # Get depth of field settings
            depth_of_field = cmds.getAttr(f"{camera_shape}.depthOfField")
            f_stop = cmds.getAttr(f"{camera_shape}.fStop") if depth_of_field else None
            focus_distance = cmds.getAttr(f"{camera_shape}.focusDistance") if depth_of_field else None
            
            return {
                "focal_length": focal_length,
                "film_back": film_back,
                "horizontal_film_aperture": horizontal_film_aperture,
                "vertical_film_aperture": vertical_film_aperture,
                "near_clip": near_clip,
                "far_clip": far_clip,
                "orthographic": orthographic,
                "orthographic_width": orthographic_width,
                "depth_of_field": depth_of_field,
                "f_stop": f_stop,
                "focus_distance": focus_distance
            }
            
        except ImportError:
            return {}
        except Exception as e:
            print(f"[Collect Cameras] Warning: Could not get camera settings: {e}")
            return {}
    
    def is_camera_modified(self, transform, shape):
        """Check if a default camera has been modified."""
        try:
            import maya.cmds as cmds
            
            # Check if transform has keyframes
            if cmds.keyframe(transform, query=True):
                return True
            
            # Check if camera settings have been modified from defaults
            focal_length = cmds.getAttr(f"{shape}.focalLength")
            if abs(focal_length - 35.0) > 0.001:  # Default focal length is 35mm
                return True
            
            # Check if camera has custom attributes
            user_attrs = cmds.listAttr(transform, userDefined=True) or []
            if user_attrs:
                return True
            
            user_attrs_shape = cmds.listAttr(shape, userDefined=True) or []
            if user_attrs_shape:
                return True
            
            return False
            
        except ImportError:
            return False
    
    def get_camera_animation(self, camera_transform):
        """Get camera animation data."""
        try:
            import maya.cmds as cmds
            
            # Check for keyframes on transform
            keyframes = cmds.keyframe(camera_transform, query=True, timeChange=True) or []
            
            # Also check camera shape for animated attributes
            camera_shapes = cmds.listRelatives(camera_transform, shapes=True, type='camera') or []
            for shape in camera_shapes:
                shape_keyframes = cmds.keyframe(shape, query=True, timeChange=True) or []
                keyframes.extend(shape_keyframes)
            
            is_animated = len(keyframes) > 0
            keyframe_count = len(keyframes)
            
            # Get animation range
            animation_range = None
            if keyframes:
                animation_range = (min(keyframes), max(keyframes))
            
            return {
                "is_animated": is_animated,
                "keyframe_count": keyframe_count,
                "animation_range": animation_range,
                "keyframes": keyframes
            }
            
        except ImportError:
            return {
                "is_animated": False,
                "keyframe_count": 0,
                "animation_range": None,
                "keyframes": []
            }
