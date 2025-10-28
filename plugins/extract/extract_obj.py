"""
Extract OBJ Plugin

This plugin exports model assets to OBJ format.
It handles export settings and file naming conventions for OBJ files.
"""

import pyblish.api
import os
import sys
from pathlib import Path

# Add utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.file_utils import ensure_directory, get_next_version
from config.settings import DEFAULT_PLUGIN_ORDERS, EXPORT_SETTINGS


class ExtractOBJ(pyblish.api.InstancePlugin):
    """Export model assets to OBJ format."""
    
    label = "Extract OBJ"
    order = DEFAULT_PLUGIN_ORDERS.get("extract_obj", 220)
    hosts = ["maya"]
    families = ["model"]
    
    def process(self, instance):
        """Main processing function."""
        print("\n" + "="*50)
        print(f"[Extract OBJ] Exporting: {instance.name}")
        print("="*50)

        family = instance.data.get("family")
        asset_name = instance.data.get("asset", instance.name)

        print(f"[Extract OBJ] Family: {family}")
        print(f"[Extract OBJ] Asset: {asset_name}")

        # Respect manual selection
        if not bool(instance.data.get("publish", True)):
            print("[Extract OBJ] Skipped (publish=False)")
            return

        # Only process model family
        if family != "model":
            print(f"[Extract OBJ] Skipping - family '{family}' not supported for OBJ export")
            return
        
        # Get meshes to export
        meshes = instance.data.get("meshes", [])
        if not meshes:
            print("[Extract OBJ] No meshes found to export")
            return
        
        print(f"[Extract OBJ] Meshes to export: {len(meshes)}")
        
        # Determine export path
        export_path = self.get_export_path(instance, asset_name)
        print(f"[Extract OBJ] Export path: {export_path}")
        
        # Ensure export directory exists
        ensure_directory(os.path.dirname(export_path))
        
        # Perform OBJ export
        success = self.export_obj(meshes, export_path, instance)
        
        if success:
            # Store export information in instance
            instance.data["obj_export_path"] = export_path
            instance.data["exported_meshes"] = meshes
            
            print(f"[Extract OBJ] SUCCESS: Exported to {export_path}")
            print(f"[Extract OBJ] File size: {self.get_file_size_mb(export_path):.2f} MB")
            
            # Check for MTL file
            mtl_path = export_path.replace('.obj', '.mtl')
            if os.path.exists(mtl_path):
                print(f"[Extract OBJ] MTL file created: {mtl_path}")
                instance.data["mtl_export_path"] = mtl_path
        else:
            error_msg = f"Failed to export OBJ to {export_path}"
            print(f"[Extract OBJ] FAILED: {error_msg}")
            raise RuntimeError(error_msg)
        
        print("="*50 + "\n")
    
    def get_export_path(self, instance, asset_name):
        """Generate export file path under repo root to avoid Program Files cwd."""
        repo_root = Path(__file__).resolve().parents[2]
        export_dir = (repo_root / "exports/models" / asset_name).resolve()
        os.makedirs(str(export_dir), exist_ok=True)
        filename = f"{asset_name}.obj"
        export_path = str(export_dir / filename)
        if os.path.exists(export_path):
            export_path = get_next_version(export_path)
        return export_path
    
    def export_obj(self, meshes, export_path, instance):
        """Perform the actual OBJ export."""
        try:
            import maya.cmds as cmds
            
            # Select meshes for export
            cmds.select(meshes, replace=True)
            
            # Get OBJ export settings
            obj_settings = EXPORT_SETTINGS.get("obj", {})
            
            # Configure export options
            options = self.build_export_options(obj_settings)
            
            print(f"[Extract OBJ] Exporting {len(meshes)} meshes...")
            print(f"[Extract OBJ] Export options: {options}")
            
            # Perform export using Maya's OBJ exporter
            cmds.file(
                export_path,
                force=True,
                options=options,
                type="OBJexport",
                exportSelected=True
            )
            
            # Verify export
            if os.path.exists(export_path):
                print(f"[Extract OBJ] Export successful")
                return True
            else:
                print(f"[Extract OBJ] Export failed - file not created")
                return False
                
        except ImportError:
            print("Maya not available - cannot export OBJ")
            return False
        except Exception as e:
            print(f"[Extract OBJ] Export failed: {e}")
            return False
    
    def build_export_options(self, obj_settings):
        """Build OBJ export options string."""
        options = []
        
        # Groups
        if obj_settings.get("groups", True):
            options.append("groups=1")
        else:
            options.append("groups=0")
        
        # Point groups
        options.append("ptgroups=1")
        
        # Materials
        if obj_settings.get("materials", True):
            options.append("materials=1")
        else:
            options.append("materials=0")
        
        # Smoothing
        if obj_settings.get("smoothing", True):
            options.append("smoothing=1")
        else:
            options.append("smoothing=0")
        
        # Normals
        if obj_settings.get("normals", True):
            options.append("normals=1")
        else:
            options.append("normals=0")
        
        # UV coordinates
        options.append("uvs=1")
        
        return ";".join(options)
    
    def get_file_size_mb(self, file_path):
        """Get file size in megabytes."""
        if os.path.exists(file_path):
            size_bytes = os.path.getsize(file_path)
            return size_bytes / (1024 * 1024)
        return 0
