"""
Extract FBX Plugin

This plugin exports model and animation assets to FBX format.
It handles export settings and file naming conventions.
"""

import pyblish.api
import os
import sys
from pathlib import Path

# Add utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.file_utils import ensure_directory, get_next_version
from config.settings import DEFAULT_PLUGIN_ORDERS, EXPORT_SETTINGS


class ExtractFBX(pyblish.api.InstancePlugin):
    """Export assets to FBX format."""
    
    label = "Extract FBX"
    order = DEFAULT_PLUGIN_ORDERS.get("extract_fbx", 210)
    hosts = ["maya"]
    families = ["model", "animation"]
    
    def process(self, instance):
        """Main processing function."""
        print("\n" + "="*50)
        print(f"[Extract FBX] Exporting: {instance.name}")
        print("="*50)

        family = instance.data.get("family")
        asset_name = instance.data.get("asset", instance.name)

        print(f"[Extract FBX] Family: {family}")
        print(f"[Extract FBX] Asset: {asset_name}")

        # Respect manual selection
        if not bool(instance.data.get("publish", True)):
            print("[Extract FBX] Skipped (publish=False)")
            return

        # Determine export path
        export_path = self.get_export_path(instance, asset_name, family)
        print(f"[Extract FBX] Export path: {export_path}")
        
        # Ensure export directory exists
        ensure_directory(os.path.dirname(export_path))
        
        # Prepare objects for export
        export_objects = self.get_export_objects(instance, family)
        print(f"[Extract FBX] Objects to export: {len(export_objects)}")
        
        if not export_objects:
            print("[Extract FBX] No objects to export")
            return
        
        # Perform FBX export
        success = self.export_fbx(export_objects, export_path, family, instance)
        
        if success:
            # Store export information in instance
            instance.data["fbx_export_path"] = export_path
            instance.data["exported_objects"] = export_objects
            
            print(f"[Extract FBX] SUCCESS: Exported to {export_path}")
            print(f"[Extract FBX] File size: {self.get_file_size_mb(export_path):.2f} MB")
        else:
            error_msg = f"Failed to export FBX to {export_path}"
            print(f"[Extract FBX] FAILED: {error_msg}")
            raise RuntimeError(error_msg)
        
        print("="*50 + "\n")
    
    def get_export_path(self, instance, asset_name, family):
        """Generate export file path under repo root to avoid Program Files cwd."""
        repo_root = Path(__file__).resolve().parents[2]
        fam = (family or "").lower()
        base_folder = "exports/models" if fam == "model" else f"exports/{fam or 'misc'}"
        export_dir = (repo_root / base_folder / asset_name).resolve()
        os.makedirs(str(export_dir), exist_ok=True)
        filename = f"{asset_name}.fbx"
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
    
    def export_fbx(self, objects, export_path, family, instance):
        """Perform the actual FBX export."""
        try:
            import maya.cmds as cmds
            import maya.mel as mel
            
            # Ensure fbx plugin
            try:
                if not cmds.pluginInfo('fbxmaya', q=True, loaded=True):
                    cmds.loadPlugin('fbxmaya', quiet=True)
            except Exception as pe:
                print(f"[Extract FBX] ERROR loading fbxmaya: {pe}")
                return False

            # Select objects for export
            if objects:
                cmds.select(objects, replace=True)
            else:
                cmds.select(all=True)

            # Get FBX export settings
            fbx_settings = EXPORT_SETTINGS.get("fbx", {})

            # Configure FBX export settings
            self.configure_fbx_settings(fbx_settings, family, instance)

            # Perform export
            print(f"[Extract FBX] Exporting {len(objects)} objects...")

            # Use FBX export command (cmds wrapper is more stable)
            export_path_norm = export_path.replace('\\', '/')
            try:
                cmds.FBXExport(f=export_path_norm, s=True)
            except Exception as ce:
                print(f"[Extract FBX] cmds.FBXExport failed: {ce}")
                # Fallback to cmds.file exporter
                try:
                    cmds.file(export_path_norm, force=True, options="v=0;", type="FBX export", exportSelected=True)
                except Exception as ce2:
                    print(f"[Extract FBX] cmds.file FBX export fallback failed: {ce2}")
                    raise

            # Verify export
            if os.path.exists(export_path):
                print(f"[Extract FBX] Export successful")
                return True
            else:
                print(f"[Extract FBX] Export failed - file not created")
                return False
                
        except ImportError:
            print("Maya not available - cannot export FBX")
            return False
        except Exception as e:
            print(f"[Extract FBX] Export failed: {e}")
            return False
    
    def configure_fbx_settings(self, fbx_settings, family, instance):
        """Configure FBX export settings."""
        try:
            import maya.mel as mel
            
            print("[Extract FBX] Configuring FBX settings...")
            
            # Reset to default settings
            mel.eval("FBXResetExport")
            
            # Set version
            version = fbx_settings.get("version", "FBX201800")
            mel.eval(f"FBXExportFileVersion {version}")
            
            # Set ASCII/Binary
            ascii_format = fbx_settings.get("ascii", False)
            mel.eval(f"FBXExportInAscii -v {str(ascii_format).lower()}")
            
            # Configure based on family
            if family == "model":
                self.configure_model_fbx_settings(fbx_settings)
            elif family == "animation":
                self.configure_animation_fbx_settings(fbx_settings, instance)
            
            print("[Extract FBX] FBX settings configured")
            
        except Exception as e:
            print(f"[Extract FBX] Warning: Could not configure FBX settings: {e}")
    
    def configure_model_fbx_settings(self, fbx_settings):
        """Configure FBX settings for model export."""
        try:
            import maya.mel as mel
            
            # Geometry settings
            mel.eval("FBXExportSmoothingGroups -v true")
            mel.eval("FBXExportHardEdges -v false")
            mel.eval("FBXExportTangents -v false")
            
            # Triangulate if specified
            triangulate = fbx_settings.get("triangulate", True)
            mel.eval(f"FBXExportTriangulate -v {str(triangulate).lower()}")
            
            # Materials and textures
            mel.eval("FBXExportEmbeddedTextures -v false")
            mel.eval("FBXExportSkins -v true")
            
            # Animation (disable for models)
            mel.eval("FBXExportAnimationOnly -v false")
            mel.eval("FBXExportBakeComplexAnimation -v false")
            
            print("[Extract FBX] Model FBX settings configured")
            
        except Exception as e:
            print(f"[Extract FBX] Warning: Could not configure model FBX settings: {e}")
    
    def configure_animation_fbx_settings(self, fbx_settings, instance):
        """Configure FBX settings for animation export."""
        try:
            import maya.mel as mel
            
            # Animation settings
            mel.eval("FBXExportAnimationOnly -v false")  # Export geometry + animation
            mel.eval("FBXExportBakeComplexAnimation -v true")
            mel.eval("FBXExportBakeComplexStep -v 1")
            
            # Set frame range
            start_frame = instance.data.get("start_frame", 1)
            end_frame = instance.data.get("end_frame", 100)
            
            mel.eval(f"FBXExportBakeComplexStart -v {start_frame}")
            mel.eval(f"FBXExportBakeComplexEnd -v {end_frame}")
            
            # Constraints and connections
            mel.eval("FBXExportConstraints -v false")
            mel.eval("FBXExportSkeletonDefinitions -v true")
            
            # Deformers
            mel.eval("FBXExportSkins -v true")
            mel.eval("FBXExportShapes -v true")
            
            print(f"[Extract FBX] Animation FBX settings configured (frames {start_frame}-{end_frame})")
            
        except Exception as e:
            print(f"[Extract FBX] Warning: Could not configure animation FBX settings: {e}")
    
    def get_file_size_mb(self, file_path):
        """Get file size in megabytes."""
        if os.path.exists(file_path):
            size_bytes = os.path.getsize(file_path)
            return size_bytes / (1024 * 1024)
        return 0
