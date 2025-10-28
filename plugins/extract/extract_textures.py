"""
Extract Textures Plugin

This plugin copies and organizes texture files for material assets.
It handles texture file management and creates organized texture libraries.
"""

import pyblish.api
import os
import shutil
import sys

# Add utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.file_utils import ensure_directory, copy_with_metadata, get_next_version
from config.settings import DEFAULT_PLUGIN_ORDERS


class ExtractTextures(pyblish.api.InstancePlugin):
    """Extract and organize texture files for material assets."""
    
    label = "Extract Textures"
    order = DEFAULT_PLUGIN_ORDERS.get("extract_textures", 240)
    hosts = ["maya"]
    families = ["material"]
    
    def process(self, instance):
        """Main processing function."""
        print("\n" + "="*50)
        print(f"[Extract Textures] Extracting: {instance.name}")
        print("="*50)
        
        family = instance.data.get("family")
        asset_name = instance.data.get("asset", instance.name)
        
        print(f"[Extract Textures] Family: {family}")
        print(f"[Extract Textures] Asset: {asset_name}")
        
        # Get textures from instance
        textures = instance.data.get("textures", [])
        if not textures:
            print("[Extract Textures] No textures found to extract")
            return
        
        print(f"[Extract Textures] Textures to extract: {len(textures)}")
        
        # Determine export directory
        export_dir = self.get_export_directory(instance, asset_name)
        print(f"[Extract Textures] Export directory: {export_dir}")
        
        # Ensure export directory exists
        ensure_directory(export_dir)
        
        # Extract textures
        extracted_textures = self.extract_texture_files(textures, export_dir, instance)
        
        if extracted_textures:
            # Store extraction information in instance
            instance.data["texture_export_dir"] = export_dir
            instance.data["extracted_textures"] = extracted_textures
            
            print(f"[Extract Textures] SUCCESS: Extracted {len(extracted_textures)} textures")
            
            # Calculate total size
            total_size_mb = sum(tex['size_mb'] for tex in extracted_textures)
            print(f"[Extract Textures] Total size: {total_size_mb:.2f} MB")
            
            # Create texture manifest
            self.create_texture_manifest(extracted_textures, export_dir, asset_name)
        else:
            print("[Extract Textures] No textures were extracted")
        
        print("="*50 + "\n")
    
    def get_export_directory(self, instance, asset_name):
        """Generate export directory path."""
        # Get scene directory or use default
        scene_path = instance.data.get("scene", "")
        if scene_path and os.path.dirname(scene_path):
            base_dir = os.path.dirname(scene_path)
        else:
            base_dir = os.getcwd()
        
        # Create export directory structure
        export_dir = os.path.join(base_dir, "export", "textures", asset_name)
        
        return export_dir
    
    def extract_texture_files(self, textures, export_dir, instance):
        """Extract texture files to export directory."""
        extracted_textures = []
        
        for texture_info in textures:
            texture_path = texture_info['path']
            texture_node = texture_info['node']
            
            if not os.path.exists(texture_path):
                print(f"[Extract Textures] Warning: Texture file not found: {texture_path}")
                continue
            
            try:
                # Determine destination filename
                dest_filename = self.get_destination_filename(texture_path, texture_node)
                dest_path = os.path.join(export_dir, dest_filename)
                
                # Handle file conflicts
                if os.path.exists(dest_path):
                    if self.files_are_identical(texture_path, dest_path):
                        print(f"[Extract Textures] Skipping identical file: {dest_filename}")
                        continue
                    else:
                        dest_path = get_next_version(dest_path)
                        dest_filename = os.path.basename(dest_path)
                
                # Copy texture file
                copy_with_metadata(texture_path, dest_path)
                
                # Get file information
                file_size_mb = os.path.getsize(dest_path) / (1024 * 1024)
                
                extracted_info = {
                    'original_path': texture_path,
                    'extracted_path': dest_path,
                    'filename': dest_filename,
                    'node': texture_node,
                    'size_mb': file_size_mb,
                    'format': os.path.splitext(dest_filename)[1].lower()
                }
                
                extracted_textures.append(extracted_info)
                print(f"[Extract Textures] Extracted: {dest_filename} ({file_size_mb:.2f} MB)")
                
            except Exception as e:
                print(f"[Extract Textures] Failed to extract {texture_path}: {e}")
                continue
        
        return extracted_textures
    
    def get_destination_filename(self, texture_path, texture_node):
        """Generate destination filename for texture."""
        original_filename = os.path.basename(texture_path)
        name, ext = os.path.splitext(original_filename)
        
        # Clean filename
        clean_name = self.clean_texture_name(name)
        
        # Add node name if different from filename
        if texture_node and texture_node.lower() not in clean_name.lower():
            clean_name = f"{texture_node}_{clean_name}"
        
        return f"{clean_name}{ext}"
    
    def clean_texture_name(self, name):
        """Clean texture name for consistent naming."""
        import re
        
        # Remove invalid characters
        clean_name = re.sub(r'[<>:"/\\|?*]', '_', name)
        
        # Remove multiple underscores
        clean_name = re.sub(r'_+', '_', clean_name)
        
        # Remove leading/trailing underscores
        clean_name = clean_name.strip('_')
        
        return clean_name
    
    def files_are_identical(self, file1, file2):
        """Check if two files are identical."""
        try:
            # Compare file sizes first
            if os.path.getsize(file1) != os.path.getsize(file2):
                return False
            
            # Compare file contents
            with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
                chunk_size = 8192
                while True:
                    chunk1 = f1.read(chunk_size)
                    chunk2 = f2.read(chunk_size)
                    
                    if chunk1 != chunk2:
                        return False
                    
                    if not chunk1:  # End of file
                        break
            
            return True
            
        except Exception:
            return False
    
    def create_texture_manifest(self, extracted_textures, export_dir, asset_name):
        """Create a manifest file listing all extracted textures."""
        import json
        from datetime import datetime
        
        manifest_data = {
            'asset_name': asset_name,
            'extraction_date': datetime.now().isoformat(),
            'texture_count': len(extracted_textures),
            'total_size_mb': sum(tex['size_mb'] for tex in extracted_textures),
            'textures': []
        }
        
        for texture in extracted_textures:
            manifest_data['textures'].append({
                'filename': texture['filename'],
                'original_path': texture['original_path'],
                'node': texture['node'],
                'size_mb': round(texture['size_mb'], 2),
                'format': texture['format']
            })
        
        # Sort textures by filename
        manifest_data['textures'].sort(key=lambda x: x['filename'])
        
        # Write manifest file
        manifest_path = os.path.join(export_dir, f"{asset_name}_textures_manifest.json")
        
        try:
            with open(manifest_path, 'w') as f:
                json.dump(manifest_data, f, indent=4)
            
            print(f"[Extract Textures] Created manifest: {manifest_path}")
            
        except Exception as e:
            print(f"[Extract Textures] Failed to create manifest: {e}")
