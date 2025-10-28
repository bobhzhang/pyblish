"""
Collect Scene Plugin

This plugin collects scene configuration and settings from the Maya scene.
It identifies render settings, scene properties, and global configurations.
"""

import pyblish.api
import sys
import os

# Add utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.maya_utils import get_scene_name, get_frame_range, get_fps
from config.settings import DEFAULT_PLUGIN_ORDERS


class CollectScene(pyblish.api.ContextPlugin):
    """Collect scene configuration and settings."""
    
    label = "Collect Scene"
    order = DEFAULT_PLUGIN_ORDERS.get("collect_scene", 10)
    hosts = ["maya"]
    
    def process(self, context):
        """Main processing function."""
        print("\n" + "="*50)
        print("[Collect Scene] Starting scene collection...")
        print("="*50)
        
        # Get scene information
        scene_name = get_scene_name()
        scene_path = self.get_scene_path()
        
        print(f"[Collect Scene] Scene: {scene_name}")
        print(f"[Collect Scene] Path: {scene_path}")
        
        # Get scene settings
        scene_settings = self.get_scene_settings()
        render_settings = self.get_render_settings()
        units_settings = self.get_units_settings()
        
        # Create scene instance
        instance = context.create_instance("SceneSettings")
        
        instance.data.update({
            "family": "Scene",  # Display name in Pyblish UI
            "families": ["scene", "settings", "configuration"],  # Tags for validation
            "asset": "SceneSettings",
            "scene_name": scene_name,
            "scene_path": scene_path,
            "scene_settings": scene_settings,
            "render_settings": render_settings,
            "units_settings": units_settings,
            "frame_range": scene_settings.get("frame_range"),
            "fps": scene_settings.get("fps"),
            "current_renderer": render_settings.get("current_renderer"),
            "render_resolution": render_settings.get("resolution"),
            "linear_units": units_settings.get("linear"),
            "angular_units": units_settings.get("angular"),
            "time_units": units_settings.get("time"),
            "plugin": self.__class__.__name__,
            "icon": "cog",
            "description": f"Scene settings and configuration for {scene_name}"
        })
        
        print(f"[Collect Scene] Created instance: SceneSettings")
        print(f"  - Frame Range: {scene_settings.get('frame_range')}")
        print(f"  - FPS: {scene_settings.get('fps')}")
        print(f"  - Renderer: {render_settings.get('current_renderer')}")
        print(f"  - Resolution: {render_settings.get('resolution')}")
        print(f"  - Linear Units: {units_settings.get('linear')}")
        print(f"  - Families: {instance.data['families']}")
        
        print("[Collect Scene] Collection completed")
        print("="*50 + "\n")
    
    def get_scene_path(self):
        """Get the current Maya scene path."""
        try:
            import maya.cmds as cmds
            return cmds.file(query=True, sceneName=True) or ""
        except ImportError:
            return ""
    
    def get_scene_settings(self):
        """Get general scene settings."""
        try:
            import maya.cmds as cmds
            
            start_frame, end_frame = get_frame_range()
            fps = get_fps()
            
            # Get current time
            current_time = cmds.currentTime(query=True)
            
            # Get scene units
            linear_unit = cmds.currentUnit(query=True, linear=True)
            angular_unit = cmds.currentUnit(query=True, angle=True)
            time_unit = cmds.currentUnit(query=True, time=True)
            
            # Get playback settings
            playback_speed = cmds.playbackOptions(query=True, playbackSpeed=True)
            loop_mode = cmds.playbackOptions(query=True, loop=True)
            
            return {
                "frame_range": (start_frame, end_frame),
                "fps": fps,
                "current_time": current_time,
                "linear_unit": linear_unit,
                "angular_unit": angular_unit,
                "time_unit": time_unit,
                "playback_speed": playback_speed,
                "loop_mode": loop_mode
            }
            
        except ImportError:
            return {}
    
    def get_render_settings(self):
        """Get render settings."""
        try:
            import maya.cmds as cmds
            
            # Get current renderer
            current_renderer = cmds.getAttr("defaultRenderGlobals.currentRenderer")
            
            # Get render resolution
            width = cmds.getAttr("defaultResolution.width")
            height = cmds.getAttr("defaultResolution.height")
            device_aspect_ratio = cmds.getAttr("defaultResolution.deviceAspectRatio")
            
            # Get render quality settings
            render_quality = cmds.getAttr("defaultRenderQuality.edgeAntiAliasing")
            
            # Get output settings
            image_format = cmds.getAttr("defaultRenderGlobals.imageFormat")
            animation = cmds.getAttr("defaultRenderGlobals.animation")
            start_frame = cmds.getAttr("defaultRenderGlobals.startFrame")
            end_frame = cmds.getAttr("defaultRenderGlobals.endFrame")
            by_frame = cmds.getAttr("defaultRenderGlobals.byFrameStep")
            
            return {
                "current_renderer": current_renderer,
                "resolution": (width, height),
                "device_aspect_ratio": device_aspect_ratio,
                "render_quality": render_quality,
                "image_format": image_format,
                "animation": animation,
                "render_start_frame": start_frame,
                "render_end_frame": end_frame,
                "by_frame": by_frame
            }
            
        except ImportError:
            return {}
        except Exception as e:
            print(f"[Collect Scene] Warning: Could not get render settings: {e}")
            return {}
    
    def get_units_settings(self):
        """Get units settings."""
        try:
            import maya.cmds as cmds
            
            linear = cmds.currentUnit(query=True, linear=True)
            angular = cmds.currentUnit(query=True, angle=True)
            time = cmds.currentUnit(query=True, time=True)
            
            return {
                "linear": linear,
                "angular": angular,
                "time": time
            }
            
        except ImportError:
            return {
                "linear": "cm",
                "angular": "deg", 
                "time": "film"
            }
