"""
Integrate Asset Database Plugin

This plugin integrates exported assets into an asset database or management system.
It creates metadata records and manages asset information.
"""

import pyblish.api
import os
import json
import sys
from datetime import datetime

# Add utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.file_utils import ensure_directory, save_json
from config.settings import DEFAULT_PLUGIN_ORDERS, INTEGRATION


class IntegrateAssetDatabase(pyblish.api.InstancePlugin):
    """Integrate assets into asset database system."""
    
    label = "Integrate Asset Database"
    order = DEFAULT_PLUGIN_ORDERS.get("integrate_asset_database", 320)
    hosts = ["maya"]
    families = ["model", "rig", "animation", "material"]
    
    def process(self, instance):
        """Main processing function."""
        print("\n" + "="*50)
        print(f"[Integrate Asset Database] Processing: {instance.name}")
        print("="*50)

        # Respect manual selection
        if not bool(instance.data.get("publish", True)):
            print("[Integrate Asset Database] Skipped (publish=False)")
            return

        # Check if asset database integration is enabled
        if not INTEGRATION.get("asset_database", {}).get("enabled", True):
            print("[Integrate Asset Database] Asset database integration is disabled - skipping")
            return
        
        family = instance.data.get("family")
        asset_name = instance.data.get("asset", instance.name)
        
        print(f"[Integrate Asset Database] Family: {family}")
        print(f"[Integrate Asset Database] Asset: {asset_name}")
        
        # Create asset metadata
        asset_metadata = self.create_asset_metadata(instance)
        
        # Get database directory
        database_dir = self.get_database_directory(instance)
        ensure_directory(database_dir)
        
        # Save asset record
        success = self.save_asset_record(asset_metadata, database_dir, asset_name, family)
        
        if success:
            print("[Integrate Asset Database] SUCCESS: Asset record created")
            instance.data["database_integrated"] = True
            instance.data["database_record_path"] = os.path.join(database_dir, f"{asset_name}_{family}.json")
            
            # Create thumbnails if enabled
            if INTEGRATION.get("asset_database", {}).get("create_thumbnails", True):
                self.create_asset_thumbnail(instance, database_dir, asset_name, family)
        else:
            print("[Integrate Asset Database] WARNING: Failed to create asset record")
        
        print("="*50 + "\n")
    
    def create_asset_metadata(self, instance):
        """Create comprehensive metadata for the asset."""
        family = instance.data.get("family")
        asset_name = instance.data.get("asset", instance.name)
        
        # Base metadata
        metadata = {
            "asset_name": asset_name,
            "family": family,
            "creation_date": datetime.now().isoformat(),
            "plugin": self.__class__.__name__,
            "scene": instance.data.get("scene", ""),
            "version": self.extract_version_from_instance(instance),
            "status": "published"
        }
        
        # Add family-specific metadata
        if family == "model":
            metadata.update(self.get_model_metadata(instance))
        elif family == "rig":
            metadata.update(self.get_rig_metadata(instance))
        elif family == "animation":
            metadata.update(self.get_animation_metadata(instance))
        elif family == "material":
            metadata.update(self.get_material_metadata(instance))
        
        # Add export information
        metadata["exports"] = self.get_export_metadata(instance)
        
        # Add validation results
        metadata["validation"] = self.get_validation_metadata(instance)
        
        # Add file information
        metadata["files"] = self.get_file_metadata(instance)
        
        return metadata
    
    def get_model_metadata(self, instance):
        """Get metadata specific to model assets."""
        metadata = {}
        
        # Mesh information
        meshes = instance.data.get("meshes", [])
        metadata["mesh_count"] = len(meshes)
        metadata["meshes"] = [mesh.split('|')[-1] for mesh in meshes]
        
        # Polycount information
        polycount = instance.data.get("polycount", {})
        metadata["polycount"] = polycount
        
        # Warnings
        warnings = instance.data.get("warnings", [])
        metadata["warnings"] = warnings
        
        return metadata
    
    def get_rig_metadata(self, instance):
        """Get metadata specific to rig assets."""
        metadata = {}
        
        # Rig components
        joints = instance.data.get("joints", [])
        controls = instance.data.get("controls", [])
        skin_clusters = instance.data.get("skin_clusters", [])
        
        metadata["joint_count"] = len(joints)
        metadata["control_count"] = len(controls)
        metadata["skin_cluster_count"] = len(skin_clusters)
        
        metadata["joints"] = [joint.split('|')[-1] for joint in joints]
        metadata["controls"] = [ctrl.split('|')[-1] for ctrl in controls]
        
        return metadata
    
    def get_animation_metadata(self, instance):
        """Get metadata specific to animation assets."""
        metadata = {}
        
        # Animation information
        animated_objects = instance.data.get("animated_objects", [])
        metadata["animated_object_count"] = len(animated_objects)
        
        # Frame range
        metadata["start_frame"] = instance.data.get("start_frame", 1)
        metadata["end_frame"] = instance.data.get("end_frame", 100)
        metadata["frame_count"] = instance.data.get("frame_count", 100)
        metadata["fps"] = instance.data.get("fps", 24)
        
        # Animated objects summary
        metadata["animated_objects"] = []
        for obj_data in animated_objects:
            metadata["animated_objects"].append({
                "object": obj_data['object'].split('|')[-1],
                "keyframe_count": obj_data.get('keyframe_count', 0)
            })
        
        return metadata
    
    def get_material_metadata(self, instance):
        """Get metadata specific to material assets."""
        metadata = {}
        
        # Material information
        materials = instance.data.get("materials", [])
        textures = instance.data.get("textures", [])
        missing_textures = instance.data.get("missing_textures", [])
        
        metadata["material_count"] = len(materials)
        metadata["texture_count"] = len(textures)
        metadata["missing_texture_count"] = len(missing_textures)
        
        metadata["materials"] = materials
        
        # Texture information
        metadata["texture_files"] = []
        for texture in textures:
            metadata["texture_files"].append({
                "node": texture.get("node", ""),
                "path": texture.get("path", ""),
                "exists": texture.get("exists", False)
            })
        
        return metadata
    
    def get_export_metadata(self, instance):
        """Get metadata about exported files."""
        exports = {}
        
        # Check for various export types
        export_mappings = {
            "fbx": "fbx_export_path",
            "obj": "obj_export_path",
            "mtl": "mtl_export_path",
            "alembic": "alembic_export_path",
            "textures": "texture_export_dir"
        }
        
        for export_type, data_key in export_mappings.items():
            if data_key in instance.data:
                path = instance.data[data_key]
                if path and os.path.exists(path):
                    exports[export_type] = {
                        "path": path,
                        "size_mb": self.get_path_size_mb(path),
                        "exists": True
                    }
        
        return exports
    
    def get_validation_metadata(self, instance):
        """Get metadata about validation results."""
        validation = {
            "passed": True,
            "warnings": instance.data.get("warnings", []),
            "errors": []
        }
        
        # Check if there were any validation failures
        # (This would be set by validation plugins if they failed)
        if instance.data.get("validation_failed", False):
            validation["passed"] = False
            validation["errors"] = instance.data.get("validation_errors", [])
        
        return validation
    
    def get_file_metadata(self, instance):
        """Get metadata about associated files."""
        files = []
        
        # Get all exported files
        exported_files = []
        
        # Add export paths
        for key in ["fbx_export_path", "obj_export_path", "mtl_export_path", "alembic_export_path"]:
            if key in instance.data:
                path = instance.data[key]
                if path and os.path.exists(path):
                    exported_files.append(path)
        
        # Add extracted textures
        extracted_textures = instance.data.get("extracted_textures", [])
        for texture in extracted_textures:
            if "extracted_path" in texture:
                exported_files.append(texture["extracted_path"])
        
        # Create file metadata
        for file_path in exported_files:
            if os.path.exists(file_path):
                files.append({
                    "path": file_path,
                    "filename": os.path.basename(file_path),
                    "size_mb": self.get_path_size_mb(file_path),
                    "format": os.path.splitext(file_path)[1].lower(),
                    "modified_date": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                })
        
        return files
    
    def get_database_directory(self, instance):
        """Get the asset database directory."""
        # Get scene directory or use default
        scene_path = instance.data.get("scene", "")
        if scene_path and os.path.dirname(scene_path):
            base_dir = os.path.dirname(scene_path)
        else:
            base_dir = os.getcwd()
        
        # Create database directory
        database_dir = os.path.join(base_dir, "asset_database")
        
        return database_dir
    
    def save_asset_record(self, metadata, database_dir, asset_name, family):
        """Save asset record to database."""
        try:
            # Create record filename
            record_filename = f"{asset_name}_{family}.json"
            record_path = os.path.join(database_dir, record_filename)
            
            # Save metadata as JSON
            save_json(metadata, record_path)
            
            print(f"[Integrate Asset Database] Saved record: {record_path}")
            
            # Update database index
            self.update_database_index(database_dir, asset_name, family, record_filename)
            
            return True
            
        except Exception as e:
            print(f"[Integrate Asset Database] Failed to save asset record: {e}")
            return False
    
    def update_database_index(self, database_dir, asset_name, family, record_filename):
        """Update the database index file."""
        index_path = os.path.join(database_dir, "asset_index.json")
        
        try:
            # Load existing index
            if os.path.exists(index_path):
                with open(index_path, 'r') as f:
                    index = json.load(f)
            else:
                index = {"assets": [], "last_updated": ""}
            
            # Update index entry
            asset_entry = {
                "asset_name": asset_name,
                "family": family,
                "record_file": record_filename,
                "last_updated": datetime.now().isoformat()
            }
            
            # Remove existing entry if it exists
            index["assets"] = [a for a in index["assets"] 
                             if not (a["asset_name"] == asset_name and a["family"] == family)]
            
            # Add new entry
            index["assets"].append(asset_entry)
            index["last_updated"] = datetime.now().isoformat()
            
            # Save updated index
            save_json(index, index_path)
            
            print(f"[Integrate Asset Database] Updated index: {index_path}")
            
        except Exception as e:
            print(f"[Integrate Asset Database] Failed to update index: {e}")
    
    def create_asset_thumbnail(self, instance, database_dir, asset_name, family):
        """Create thumbnail for the asset."""
        try:
            import maya.cmds as cmds
            
            # Create thumbnails directory
            thumbnails_dir = os.path.join(database_dir, "thumbnails")
            ensure_directory(thumbnails_dir)
            
            # Generate thumbnail filename
            thumbnail_filename = f"{asset_name}_{family}_thumbnail.jpg"
            thumbnail_path = os.path.join(thumbnails_dir, thumbnail_filename)
            
            # Take viewport screenshot
            cmds.playblast(
                frame=1,
                format='image',
                compression='jpg',
                quality=70,
                widthHeight=[256, 256],
                viewer=False,
                showOrnaments=False,
                filename=thumbnail_path.replace('.jpg', ''),
                completeFilename=thumbnail_path
            )
            
            if os.path.exists(thumbnail_path):
                print(f"[Integrate Asset Database] Created thumbnail: {thumbnail_path}")
                instance.data["thumbnail_path"] = thumbnail_path
            
        except ImportError:
            print("Maya not available - skipping thumbnail creation")
        except Exception as e:
            print(f"[Integrate Asset Database] Failed to create thumbnail: {e}")
    
    def extract_version_from_instance(self, instance):
        """Extract version number from instance data."""
        # Check export paths for version numbers
        for key in ["fbx_export_path", "obj_export_path", "alembic_export_path"]:
            if key in instance.data:
                path = instance.data[key]
                if path and "_v" in path:
                    import re
                    match = re.search(r'_v(\d+)', path)
                    if match:
                        return int(match.group(1))
        
        return 1  # Default version
    
    def get_path_size_mb(self, path):
        """Get size of path in megabytes."""
        if os.path.isfile(path):
            return os.path.getsize(path) / (1024 * 1024)
        elif os.path.isdir(path):
            total_size = 0
            for root, dirs, files in os.walk(path):
                for file in files:
                    file_path = os.path.join(root, file)
                    total_size += os.path.getsize(file_path)
            return total_size / (1024 * 1024)
        return 0
