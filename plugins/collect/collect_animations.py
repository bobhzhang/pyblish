"""
Collect Animations Plugin

This plugin collects animation data from the Maya scene.
It identifies animated objects and keyframe data for animation assets.
"""

import pyblish.api
import sys
import os

# Add utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.maya_utils import get_frame_range, get_fps, get_scene_name
from config.settings import DEFAULT_PLUGIN_ORDERS


class CollectAnimations(pyblish.api.ContextPlugin):
    """Collect animation assets from the scene."""
    
    label = "Collect Animations"
    order = DEFAULT_PLUGIN_ORDERS.get("collect_animations", 40)
    hosts = ["maya"]
    
    def process(self, context):
        """Main processing function."""
        print("\n" + "="*50)
        print("[Collect Animations] Starting animation collection...")
        print("="*50)
        
        # Get scene information
        scene_name = get_scene_name()
        start_frame, end_frame = get_frame_range()
        fps = get_fps()
        
        print(f"[Collect Animations] Scene: {scene_name}")
        print(f"[Collect Animations] Frame Range: {start_frame} - {end_frame}")
        print(f"[Collect Animations] FPS: {fps}")
        
        # Get animated objects
        animated_objects = self.get_animated_objects()
        print(f"[Collect Animations] Found {len(animated_objects)} animated objects")
        
        if not animated_objects:
            print("[Collect Animations] No animated objects found in scene")
            return
        
        # Group animated objects
        animation_groups = self.group_animated_objects(animated_objects)
        
        # Create instances for each animation group
        for group_name, objects in animation_groups.items():
            instance = context.create_instance(group_name)
            instance.data.update({
                "family": "Animation",  # Display name in Pyblish UI
                "families": ["animation", "keyframes", "motion"],  # Tags for validation
                "asset": group_name,
                "animated_objects": objects,
                "start_frame": start_frame,
                "end_frame": end_frame,
                "fps": fps,
                "frame_count": end_frame - start_frame + 1,
                "total_keyframes": sum(obj['keyframe_count'] for obj in objects),
                "scene": scene_name,
                "plugin": self.__class__.__name__,
                "icon": "play",
                "description": f"Animation with {len(objects)} animated objects and {sum(obj['keyframe_count'] for obj in objects)} keyframes",
                "publish": True
            })
            
            # Add animated objects to instance
            for obj in objects:
                instance.append(obj['object'])
            
            print(f"[Collect Animations] Created instance: {group_name}")
            print(f"  - Animated Objects: {len(objects)}")
            print(f"  - Frame Range: {start_frame}-{end_frame}")
            
            # Print details of animated objects
            for obj in objects[:5]:  # Show first 5 objects
                print(f"    - {obj['object']}: {len(obj['keyframes'])} keyframes")
            if len(objects) > 5:
                print(f"    ... and {len(objects) - 5} more objects")
        
        print(f"[Collect Animations] Collection completed - {len(animation_groups)} animation groups")
        print("="*50 + "\n")
    
    def get_animated_objects(self):
        """Get all objects with animation keyframes."""
        try:
            import maya.cmds as cmds
            animated_objects = []
            
            # Get all keyframe nodes
            anim_curves = cmds.ls(type='animCurve') or []
            
            if not anim_curves:
                return animated_objects
            
            # Group by connected object
            object_keyframes = {}
            
            for curve in anim_curves:
                # Get connected objects
                connections = cmds.listConnections(curve, destination=True) or []
                
                for connection in connections:
                    if connection not in object_keyframes:
                        object_keyframes[connection] = []
                    
                    # Get keyframe information
                    keyframes = cmds.keyframe(curve, query=True, timeChange=True) or []
                    values = cmds.keyframe(curve, query=True, valueChange=True) or []
                    
                    object_keyframes[connection].extend(list(zip(keyframes, values)))
            
            # Convert to list format
            for obj, keyframes in object_keyframes.items():
                if keyframes:  # Only include objects with actual keyframes
                    animated_objects.append({
                        'object': obj,
                        'keyframes': keyframes,
                        'keyframe_count': len(keyframes)
                    })
            
            return animated_objects
            
        except ImportError:
            print("Maya not available")
            return []
    
    def group_animated_objects(self, animated_objects):
        """Group animated objects into logical animation units."""
        groups = {}
        
        for obj_data in animated_objects:
            obj = obj_data['object']
            
            # Get short name
            short_name = obj.split('|')[-1] if '|' in obj else obj
            
            # Determine group name based on naming convention
            group_name = self.determine_animation_group(short_name)
            
            if group_name not in groups:
                groups[group_name] = []
            groups[group_name].append(obj_data)
        
        # If no groups found, create a default group
        if not groups and animated_objects:
            groups['DefaultAnimation'] = animated_objects
        
        return groups
    
    def determine_animation_group(self, object_name):
        """Determine animation group based on object name."""
        # Common animation group patterns
        if any(keyword in object_name.lower() for keyword in ['character', 'char', 'hero']):
            return 'CharacterAnimation'
        elif any(keyword in object_name.lower() for keyword in ['camera', 'cam']):
            return 'CameraAnimation'
        elif any(keyword in object_name.lower() for keyword in ['prop', 'object', 'obj']):
            return 'PropAnimation'
        elif any(keyword in object_name.lower() for keyword in ['light', 'lamp']):
            return 'LightingAnimation'
        elif any(keyword in object_name.lower() for keyword in ['ctrl', 'control', 'rig']):
            # Extract character/rig name from control
            parts = object_name.split('_')
            if len(parts) > 1:
                return f"{parts[0]}Animation"
            return 'RigAnimation'
        else:
            # Default grouping by first part of name
            parts = object_name.split('_')
            if len(parts) > 1:
                return f"{parts[0]}Animation"
            return 'DefaultAnimation'
