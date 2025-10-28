"""
Extract Models Plugin

This plugin extracts 3D model assets from Maya and prepares them for integration.
It exports models in multiple formats (FBX, OBJ, Alembic) based on requirements.
"""

import pyblish.api
import sys
import os
import shutil
from pathlib import Path

# Add utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from config.settings import DEFAULT_PLUGIN_ORDERS


class ExtractModels(pyblish.api.InstancePlugin):
    """Extract 3D model assets for integration."""
    
    label = "Extract Models"
    order = DEFAULT_PLUGIN_ORDERS.get("extract_models", 210)
    hosts = ["maya"]
    families = ["model"]
    
    # Export settings
    EXPORT_FORMATS = ["fbx", "obj", "ma"]
    EXPORT_DIR = "exports/models"
    
    def process(self, instance):
        """Main processing function."""
        print("\n" + "="*50)
        print(f"[Extract Models] Processing {instance.name}...")
        print("="*50)

        # Respect manual selection
        if not bool(instance.data.get("publish", True)):
            print("[Extract Models] Skipped (publish=False)")
            return

        # Create export directory
        export_dir = self.create_export_directory(instance)
        print(f"[Extract Models] Export directory: {export_dir}")
        
        # Get meshes to export
        meshes = instance.data.get("meshes", [])
        if not meshes:
            print("[Extract Models] No meshes found in instance")
            return
        
        print(f"[Extract Models] Found {len(meshes)} meshes to export")
        
        # Export in different formats
        exported_files = []
        
        for format_type in self.EXPORT_FORMATS:
            try:
                export_file = self.export_format(instance, meshes, export_dir, format_type)
                if export_file:
                    exported_files.append(export_file)
                    print(f"[Extract Models] OK Exported {format_type.upper()}: {os.path.basename(export_file)}")
            except Exception as e:
                print(f"[Extract Models] ERROR Failed to export {format_type.upper()}: {e}")
        
        # Store export information in instance
        instance.data["exported_files"] = exported_files
        instance.data["export_directory"] = str(export_dir)
        
        # Create metadata file
        metadata_file = self.create_metadata_file(instance, export_dir)
        if metadata_file:
            exported_files.append(metadata_file)
            print(f"[Extract Models] OK Created metadata: {os.path.basename(metadata_file)}")
        
        print(f"[Extract Models] Extraction completed - {len(exported_files)} files created")
        print("="*50 + "\n")
    
    def create_export_directory(self, instance):
        """Create export directory for the instance.
        Always resolve to an absolute path under the repository root to avoid Maya cwd issues.
        """
        repo_root = Path(__file__).resolve().parents[2]
        export_path = (repo_root / self.EXPORT_DIR / instance.name).resolve()
        export_path.mkdir(parents=True, exist_ok=True)
        return export_path
    
    def export_format(self, instance, meshes, export_dir, format_type):
        """Export meshes in specified format."""
        try:
            import maya.cmds as cmds
            
            # Select meshes for export
            cmds.select(meshes, replace=True)
            
            # Generate filename
            filename = f"{instance.name}.{format_type}"
            export_file = export_dir / filename
            
            # Export based on format
            if format_type == "fbx":
                return self.export_fbx(export_file, meshes)
            elif format_type == "obj":
                return self.export_obj(export_file, meshes)
            elif format_type == "ma":
                return self.export_maya_ascii(export_file, meshes)
            else:
                print(f"[Extract Models] Unsupported format: {format_type}")
                return None
                
        except ImportError:
            print("[Extract Models] Maya not available")
            return None
    
    def export_fbx(self, export_file, meshes):
        """Export as FBX format with plugin load and diagnostics."""
        try:
            import maya.cmds as cmds
            # Ensure FBX plugin is loaded
            try:
                if not cmds.pluginInfo('fbxmaya', query=True, loaded=True):
                    cmds.loadPlugin('fbxmaya', quiet=True)
            except Exception as pe:
                print(f"[Extract Models] ERROR loading fbxmaya plugin: {pe}")
                import traceback; traceback.print_exc()
                return None

            # Select meshes
            cmds.select(meshes, replace=True)

            # FBX export settings
            cmds.FBXResetExport()
            cmds.FBXExportSmoothingGroups(v=True)
            cmds.FBXExportHardEdges(v=False)
            cmds.FBXExportTangents(v=False)
            cmds.FBXExportSmoothMesh(v=True)
            cmds.FBXExportInstances(v=False)
            cmds.FBXExportReferencedAssetsContent(v=False)
            cmds.FBXExportAnimations(v=False)
            cmds.FBXExportCameras(v=False)
            cmds.FBXExportLights(v=False)
            cmds.FBXExportEmbeddedTextures(v=False)

            # Export selected
            cmds.FBXExport(f=str(export_file), s=True)

            # Verify file exists
            if not os.path.exists(str(export_file)):
                print(f"[Extract Models] FBX file missing after export: {export_file}")
                return None
            return str(export_file)

        except Exception as e:
            print(f"[Extract Models] FBX export failed: {e}")
            try:
                drive = os.path.splitdrive(str(export_file))[0] or str(Path(export_file).anchor)
                usage = shutil.disk_usage(drive or os.getcwd())
                print(f"[Extract Models] Diagnostics - path={export_file}, parent_exists={os.path.exists(os.path.dirname(str(export_file)))}, free_MB={usage.free//(1024*1024)}")
            except Exception:
                pass
            import traceback; traceback.print_exc()
            return None
    
    def export_obj(self, export_file, meshes):
        """Export as OBJ format (absolute path, diagnostics)."""
        try:
            import maya.cmds as cmds
            # Select meshes
            cmds.select(meshes, replace=True)
            # OBJ export options
            options = ["groups=1", "ptgroups=1", "materials=0", "smoothing=1", "normals=1"]
            cmds.file(str(export_file), type="OBJexport", exportSelected=True, options=";".join(options), force=True)
            if not os.path.exists(str(export_file)):
                print(f"[Extract Models] OBJ file missing after export: {export_file}")
                return None
            return str(export_file)
        except Exception as e:
            print(f"[Extract Models] OBJ export failed: {e}")
            import traceback; traceback.print_exc()
            return None
    
    def export_maya_ascii(self, export_file, meshes):
        """Export as Maya ASCII format (absolute path, diagnostics)."""
        try:
            import maya.cmds as cmds
            # Select meshes
            cmds.select(meshes, replace=True)
            cmds.file(str(export_file), type="mayaAscii", exportSelected=True, force=True)
            if not os.path.exists(str(export_file)):
                print(f"[Extract Models] MA file missing after export: {export_file}")
                return None
            return str(export_file)
        except Exception as e:
            print(f"[Extract Models] Maya ASCII export failed: {e}")
            import traceback; traceback.print_exc()
            return None
    
    def create_metadata_file(self, instance, export_dir):
        """Create metadata file with model information."""
        try:
            import json
            
            # Collect metadata
            metadata = {
                "asset_name": instance.name,
                "family": instance.data.get("family"),
                "families": instance.data.get("families", []),
                "scene": instance.data.get("scene"),
                "plugin": instance.data.get("plugin"),
                "export_timestamp": self.get_timestamp(),
                "model_data": {
                    "mesh_count": instance.data.get("mesh_count", 0),
                    "total_vertices": instance.data.get("total_vertices", 0),
                    "total_faces": instance.data.get("total_faces", 0),
                    "meshes": instance.data.get("meshes", [])
                },
                "export_settings": {
                    "formats": self.EXPORT_FORMATS,
                    "export_directory": str(export_dir)
                },
                "maya_objects": [str(obj) for obj in instance]
            }
            
            # Write metadata file
            metadata_file = export_dir / f"{instance.name}_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return str(metadata_file)
            
        except Exception as e:
            print(f"[Extract Models] Metadata creation failed: {e}")
            return None
    
    def get_timestamp(self):
        """Get current timestamp string."""
        import datetime
        return datetime.datetime.now().isoformat()
