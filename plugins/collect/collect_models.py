"""
Collect Models Plugin

This plugin collects 3D model assets from the Maya scene.
It identifies mesh objects and creates instances for validation and export.
"""

import pyblish.api
import sys
import os

# Add utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.maya_utils import get_meshes, get_scene_name
from config.settings import DEFAULT_PLUGIN_ORDERS


class CollectModels(pyblish.api.ContextPlugin):
    """Collect 3D model assets from the scene."""
    
    label = "Collect Models"
    order = DEFAULT_PLUGIN_ORDERS.get("collect_models", 20)
    hosts = ["maya"]
    
    def process(self, context):
        """Main processing function."""
        print("\n" + "="*50)
        print("[Collect Models] Starting model collection...")
        print("="*50)
        
        # Get scene information
        scene_name = get_scene_name()
        print(f"[Collect Models] Scene: {scene_name}")
        
        # Get all mesh objects in the scene
        meshes = get_meshes()
        print(f"[Collect Models] Found {len(meshes)} mesh objects")
        
        if not meshes:
            print("[Collect Models] No mesh objects found in scene")
            return
        
        # Group meshes by naming convention or selection
        model_groups = self.group_meshes(meshes)
        
        # Create instances for each model group
        for group_name, mesh_list in model_groups.items():
            instance = context.create_instance(group_name)
            
            # Get detailed mesh information
            mesh_info = self.get_mesh_details(mesh_list)
            
            instance.data.update({
                "family": "Model",  # Display name in Pyblish UI
                "families": ["model", "geometry", "mesh"],  # Tags for validation
                "asset": group_name,
                "meshes": mesh_list,
                "mesh_count": len(mesh_list),
                "total_vertices": mesh_info["total_vertices"],
                "total_faces": mesh_info["total_faces"],
                "scene": scene_name,
                "plugin": self.__class__.__name__,
                "icon": "cube",
                "description": f"Model group with {len(mesh_list)} meshes",
                "publish": True
            })
            
            # Add mesh objects to instance
            for mesh in mesh_list:
                instance.append(mesh)
            
            print(f"[Collect Models] Created instance: {group_name}")
            print(f"  - Meshes: {len(mesh_list)}")
            print(f"  - Total Vertices: {mesh_info['total_vertices']}")
            print(f"  - Total Faces: {mesh_info['total_faces']}")
            print(f"  - Families: {instance.data['families']}")
        
        print(f"[Collect Models] Collection completed - {len(model_groups)} model groups")
        print("="*50 + "\n")
    
    def group_meshes(self, meshes):
        """Group meshes into logical model units."""
        groups = {}
        
        for mesh in meshes:
            # Get short name (without path)
            short_name = mesh.split('|')[-1]
            
            # Extract group name based on naming convention
            group_name = self.determine_model_group(short_name)
            
            if group_name not in groups:
                groups[group_name] = []
            groups[group_name].append(mesh)
        
        # If no groups found, create a default group
        if not groups and meshes:
            groups['DefaultModel'] = meshes
        
        return groups
    
    def determine_model_group(self, mesh_name):
        """Determine model group based on mesh name."""
        # Skip default Maya objects
        if mesh_name.lower() in ['persp', 'top', 'front', 'side']:
            return None
        
        # Common model group patterns
        if any(keyword in mesh_name.lower() for keyword in ['character', 'char', 'hero']):
            return 'Character'
        elif any(keyword in mesh_name.lower() for keyword in ['prop', 'object', 'obj']):
            return 'Prop'
        elif any(keyword in mesh_name.lower() for keyword in ['environment', 'env', 'set']):
            return 'Environment'
        elif any(keyword in mesh_name.lower() for keyword in ['vehicle', 'car', 'truck']):
            return 'Vehicle'
        elif any(keyword in mesh_name.lower() for keyword in ['building', 'house', 'structure']):
            return 'Architecture'
        else:
            # Extract group name from naming convention (prefix before underscore)
            if '_' in mesh_name:
                prefix = mesh_name.split('_')[0]
                return prefix.capitalize()
            else:
                return 'DefaultModel'
    
    def get_mesh_details(self, mesh_list):
        """Get detailed information about meshes."""
        try:
            import maya.cmds as cmds
            
            total_vertices = 0
            total_faces = 0
            
            for mesh in mesh_list:
                try:
                    # Get vertex count
                    vertices = cmds.polyEvaluate(mesh, vertex=True) or 0
                    # Get face count
                    faces = cmds.polyEvaluate(mesh, face=True) or 0
                    
                    total_vertices += vertices
                    total_faces += faces
                    
                except Exception as e:
                    print(f"[Collect Models] Warning: Could not evaluate {mesh}: {e}")
            
            return {
                "total_vertices": total_vertices,
                "total_faces": total_faces
            }
            
        except ImportError:
            print("[Collect Models] Maya not available")
            return {
                "total_vertices": 0,
                "total_faces": 0
            }
