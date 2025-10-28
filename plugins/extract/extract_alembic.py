"""
Extract Alembic Plugin

This plugin exports animation and geometry cache to Alembic format.
It handles export settings and file naming conventions for ABC files.
"""

import pyblish.api
import os
import sys
from pathlib import Path

# Add utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.file_utils import ensure_directory, get_next_version
from config.settings import DEFAULT_PLUGIN_ORDERS, EXPORT_SETTINGS


class ExtractAlembic(pyblish.api.InstancePlugin):
    """Export assets to Alembic format."""
    
    label = "Extract Alembic"
    order = DEFAULT_PLUGIN_ORDERS.get("extract_alembic", 230)
    hosts = ["maya"]
    families = ["model", "animation"]
    
    def process(self, instance):
        """Main processing function."""
        print("\n" + "="*50)
        print(f"[Extract Alembic] Exporting: {instance.name}")
        print("="*50)

        family = instance.data.get("family")
        asset_name = instance.data.get("asset", instance.name)

        print(f"[Extract Alembic] Family: {family}")
        print(f"[Extract Alembic] Asset: {asset_name}")

        # Respect manual selection
        if not bool(instance.data.get("publish", True)):
            print("[Extract Alembic] Skipped (publish=False)")
            return

        # Determine export path
        export_path = self.get_export_path(instance, asset_name, family)
        print(f"[Extract Alembic] Export path: {export_path}")
        
        # Ensure export directory exists
        ensure_directory(os.path.dirname(export_path))
        
        # Prepare objects for export
        export_objects = self.get_export_objects(instance, family)
        print(f"[Extract Alembic] Objects to export: {len(export_objects)}")
        
        if not export_objects:
            print("[Extract Alembic] No objects to export")
            return
        
        # Perform Alembic export
        success = self.export_alembic(export_objects, export_path, family, instance)
        
        if success:
            # Store export information in instance
            instance.data["alembic_export_path"] = export_path
            instance.data["exported_objects"] = export_objects
            
            print(f"[Extract Alembic] SUCCESS: Exported to {export_path}")
            print(f"[Extract Alembic] File size: {self.get_file_size_mb(export_path):.2f} MB")
        else:
            error_msg = f"Failed to export Alembic to {export_path}"
            print(f"[Extract Alembic] FAILED: {error_msg}")
            raise RuntimeError(error_msg)
        
        print("="*50 + "\n")
    
    def get_export_path(self, instance, asset_name, family):
        """Generate export file path under repo root to avoid Program Files cwd."""
        repo_root = Path(__file__).resolve().parents[2]
        fam = (family or "").lower()
        base_folder = "exports/models" if fam == "model" else "exports/animation"
        export_dir = (repo_root / base_folder / asset_name).resolve()
        os.makedirs(str(export_dir), exist_ok=True)
        filename = f"{asset_name}.abc" if fam == "model" else f"{asset_name}_anim.abc"
        export_path = str(export_dir / filename)
        if os.path.exists(export_path):
            export_path = get_next_version(export_path)
        return export_path
    
    def get_export_objects(self, instance, family):
        """Get objects to export based on family."""
        export_objects = []
        
        if family == "model":
            # Export meshes
            meshes = instance.data.get("meshes", [])
            export_objects.extend(meshes)
            
        elif family == "animation":
            # Export animated objects
            animated_objects = instance.data.get("animated_objects", [])
            for obj_data in animated_objects:
                export_objects.append(obj_data['object'])
        
        # Add any additional objects from instance
        for obj in instance:
            if isinstance(obj, str) and obj not in export_objects:
                export_objects.append(obj)
        
        return export_objects
    
    def export_alembic(self, objects, export_path, family, instance):
        """Perform the actual Alembic export."""
        try:
            import maya.cmds as cmds
            
            # Check if AbcExport command is available
            if not cmds.pluginInfo('AbcExport', query=True, loaded=True):
                try:
                    cmds.loadPlugin('AbcExport', quiet=True)
                    print("[Extract Alembic] Loaded AbcExport plugin")
                except Exception as pe:
                    print(f"[Extract Alembic] Failed to load AbcExport plugin: {pe}")
                    return False
            
            # Build Alembic export command
            abc_command = self.build_alembic_command(objects, export_path, family, instance)
            
            print(f"[Extract Alembic] Exporting {len(objects)} objects...")
            print(f"[Extract Alembic] Command: {abc_command}")
            
            # Execute Alembic export
            cmds.AbcExport(j=abc_command)
            
            # Verify export
            if os.path.exists(export_path):
                print(f"[Extract Alembic] Export successful")
                return True
            else:
                print(f"[Extract Alembic] Export failed - file not created")
                return False
                
        except ImportError:
            print("Maya not available - cannot export Alembic")
            return False
        except Exception as e:
            print(f"[Extract Alembic] Export failed: {e}")
            return False
    
    def build_alembic_command(self, objects, export_path, family, instance):
        """Build Alembic export command string."""
        command_parts = []
        
        # Get Alembic settings
        abc_settings = EXPORT_SETTINGS.get("alembic", {})
        
        # Frame range
        if family == "animation":
            start_frame = instance.data.get("start_frame", 1)
            end_frame = instance.data.get("end_frame", 100)
            command_parts.append(f"-frameRange {start_frame} {end_frame}")
        else:
            # For models, export single frame
            command_parts.append("-frameRange 1 1")
        
        # Data format
        data_format = abc_settings.get("data_format", "ogawa")
        command_parts.append(f"-dataFormat {data_format}")
        
        # UV write
        if abc_settings.get("uv_write", True):
            command_parts.append("-uvWrite")
        
        # Write visibility
        if abc_settings.get("write_visibility", True):
            command_parts.append("-writeVisibility")
        
        # Write face sets
        if abc_settings.get("write_face_sets", True):
            command_parts.append("-writeFaceSets")
        
        # World space
        command_parts.append("-worldSpace")
        
        # Write UV sets
        command_parts.append("-writeUVSets")
        
        # Strip namespaces
        command_parts.append("-stripNamespaces")
        
        # Root objects
        for obj in objects:
            # Get transform node if shape is provided
            transform = self.get_transform_node(obj)
            if transform:
                command_parts.append(f"-root {transform}")
        
        # Output file
        command_parts.append(f"-file {export_path}")
        
        return " ".join(command_parts)
    
    def get_transform_node(self, node):
        """Get transform node from shape or return node if already transform."""
        try:
            import maya.cmds as cmds
            
            # Check if node exists
            if not cmds.objExists(node):
                return None
            
            # Get node type
            node_type = cmds.nodeType(node)
            
            # If it's a shape node, get its transform
            if node_type in ['mesh', 'nurbsCurve', 'nurbsSurface']:
                transforms = cmds.listRelatives(node, parent=True, type='transform')
                if transforms:
                    return transforms[0]
            
            # If it's already a transform, return it
            elif node_type == 'transform':
                return node
            
            # For other node types, try to find associated transform
            else:
                transforms = cmds.listRelatives(node, parent=True, type='transform')
                if transforms:
                    return transforms[0]
                else:
                    return node
                    
        except Exception as e:
            print(f"[Extract Alembic] Warning: Could not get transform for {node}: {e}")
            return node
    
    def get_file_size_mb(self, file_path):
        """Get file size in megabytes."""
        if os.path.exists(file_path):
            size_bytes = os.path.getsize(file_path)
            return size_bytes / (1024 * 1024)
        return 0
