"""
Validate Materials Plugin

This plugin validates material assets for completeness and quality.
It checks shader networks, texture assignments, and material properties.
"""

import pyblish.api
import sys
import os

# Add utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.maya_utils import get_missing_textures
from config.settings import DEFAULT_PLUGIN_ORDERS, QUALITY_STANDARDS


class ValidateMaterials(pyblish.api.InstancePlugin):
    """Validate material assets for quality and completeness."""
    
    label = "Validate Materials"
    order = DEFAULT_PLUGIN_ORDERS.get("validate_materials", 130)
    hosts = ["maya"]
    families = ["material"]
    
    def process(self, instance):
        """Main processing function."""
        print("\n" + "="*50)
        print(f"[Validate Materials] Validating: {instance.name}")
        print("="*50)
        
        # Get materials and textures from instance
        materials = instance.data.get("materials", [])
        textures = instance.data.get("textures", [])
        missing_textures = instance.data.get("missing_textures", [])
        
        print(f"[Validate Materials] Materials: {len(materials)}")
        print(f"[Validate Materials] Textures: {len(textures)}")
        print(f"[Validate Materials] Missing textures: {len(missing_textures)}")
        
        # Validate materials exist
        if not materials:
            error_msg = "No materials found in material instance"
            print(f"[Validate Materials] FAILED: {error_msg}")
            raise ValueError(error_msg)
        
        # Validate missing textures
        self.validate_missing_textures(instance, missing_textures)
        
        # Validate material assignments
        self.validate_material_assignments(instance, materials)
        
        # Validate texture properties
        self.validate_texture_properties(instance, textures)
        
        # Validate shader networks
        self.validate_shader_networks(instance, materials)
        
        print(f"[Validate Materials] PASSED: Material validation completed")
        print("="*50 + "\n")
    
    def validate_missing_textures(self, instance, missing_textures):
        """Validate that no textures are missing."""
        if missing_textures:
            error_msg = (
                f"Missing texture files detected:\n" +
                "\n".join(f"  - {tex['node']}: {tex['path']}" for tex in missing_textures)
            )
            print(f"[Validate Materials] FAILED: {error_msg}")
            raise ValueError(error_msg)
        
        print("[Validate Materials] No missing textures found")
    
    def validate_material_assignments(self, instance, materials):
        """Validate that materials are properly assigned."""
        try:
            import maya.cmds as cmds
            
            unassigned_materials = []
            
            for material in materials:
                # Get shading groups connected to material
                shading_groups = cmds.listConnections(material, type='shadingEngine') or []
                
                if not shading_groups:
                    unassigned_materials.append(material)
                    continue
                
                # Check if shading group has assigned objects
                has_assignments = False
                for sg in shading_groups:
                    members = cmds.sets(sg, query=True) or []
                    if members:
                        has_assignments = True
                        break
                
                if not has_assignments:
                    unassigned_materials.append(material)
            
            if unassigned_materials:
                warning_msg = (
                    f"Materials with no assignments found:\n" +
                    "\n".join(f"  - {mat}" for mat in unassigned_materials)
                )
                print(f"[Validate Materials] WARNING: {warning_msg}")
                
                # Store warning in instance data
                if "warnings" not in instance.data:
                    instance.data["warnings"] = []
                instance.data["warnings"].append(warning_msg)
            else:
                print("[Validate Materials] All materials have assignments")
                
        except ImportError:
            print("Maya not available - skipping assignment validation")
    
    def validate_texture_properties(self, instance, textures):
        """Validate texture file properties."""
        max_texture_size_mb = QUALITY_STANDARDS.get("max_texture_size_mb", 50)
        
        oversized_textures = []
        invalid_formats = []
        valid_formats = ['.jpg', '.jpeg', '.png', '.tga', '.exr', '.hdr', '.tiff', '.tif']
        
        for texture_info in textures:
            texture_path = texture_info['path']
            
            if not texture_path or not os.path.exists(texture_path):
                continue
            
            # Check file size
            file_size_mb = os.path.getsize(texture_path) / (1024 * 1024)
            if file_size_mb > max_texture_size_mb:
                oversized_textures.append({
                    'path': texture_path,
                    'size_mb': file_size_mb,
                    'limit_mb': max_texture_size_mb
                })
            
            # Check file format
            _, ext = os.path.splitext(texture_path)
            if ext.lower() not in valid_formats:
                invalid_formats.append({
                    'path': texture_path,
                    'format': ext
                })
        
        # Report oversized textures as warnings
        if oversized_textures:
            warning_msg = "Oversized texture files detected:\n"
            for tex in oversized_textures:
                warning_msg += (
                    f"  - {os.path.basename(tex['path'])}: {tex['size_mb']:.1f}MB "
                    f"(limit: {tex['limit_mb']}MB)\n"
                )
            print(f"[Validate Materials] WARNING: {warning_msg}")
            
            if "warnings" not in instance.data:
                instance.data["warnings"] = []
            instance.data["warnings"].append(warning_msg)
        
        # Report invalid formats as errors
        if invalid_formats:
            error_msg = (
                f"Invalid texture formats detected:\n" +
                "\n".join(f"  - {os.path.basename(tex['path'])}: {tex['format']}" 
                         for tex in invalid_formats) +
                f"\nValid formats: {', '.join(valid_formats)}"
            )
            print(f"[Validate Materials] FAILED: {error_msg}")
            raise ValueError(error_msg)
        
        print(f"[Validate Materials] Texture properties validation passed")
    
    def validate_shader_networks(self, instance, materials):
        """Validate shader network completeness."""
        try:
            import maya.cmds as cmds
            
            incomplete_materials = []
            
            for material in materials:
                # Get material type
                material_type = cmds.nodeType(material)
                
                # Check required connections based on material type
                required_attrs = self.get_required_attributes(material_type)
                missing_connections = []
                
                for attr in required_attrs:
                    full_attr = f"{material}.{attr}"
                    if cmds.attributeQuery(attr, node=material, exists=True):
                        connections = cmds.listConnections(full_attr, source=True) or []
                        if not connections:
                            # Check if attribute has a non-default value
                            try:
                                value = cmds.getAttr(full_attr)
                                if self.is_default_value(attr, value):
                                    missing_connections.append(attr)
                            except:
                                missing_connections.append(attr)
                
                if missing_connections:
                    incomplete_materials.append({
                        'material': material,
                        'missing': missing_connections
                    })
            
            if incomplete_materials:
                warning_msg = "Materials with incomplete shader networks:\n"
                for mat_info in incomplete_materials:
                    warning_msg += f"  - {mat_info['material']}:\n"
                    for attr in mat_info['missing']:
                        warning_msg += f"    * {attr}\n"
                
                print(f"[Validate Materials] WARNING: {warning_msg}")
                
                if "warnings" not in instance.data:
                    instance.data["warnings"] = []
                instance.data["warnings"].append(warning_msg)
            else:
                print("[Validate Materials] Shader networks validation passed")
                
        except ImportError:
            print("Maya not available - skipping shader network validation")
    
    def get_required_attributes(self, material_type):
        """Get required attributes for material type."""
        attribute_map = {
            'lambert': ['color'],
            'blinn': ['color', 'specularColor'],
            'phong': ['color', 'specularColor'],
            'standardSurface': ['baseColor'],
            'surfaceShader': ['outColor']
        }
        
        return attribute_map.get(material_type, ['color'])
    
    def is_default_value(self, attribute, value):
        """Check if attribute has default value."""
        default_values = {
            'color': [0.5, 0.5, 0.5],
            'baseColor': [0.18, 0.18, 0.18],
            'specularColor': [0.0, 0.0, 0.0],
            'outColor': [0.0, 0.0, 0.0]
        }
        
        default = default_values.get(attribute, [0.0, 0.0, 0.0])
        
        # Handle both single values and RGB tuples
        if isinstance(value, (list, tuple)):
            return list(value) == default
        else:
            return value == default[0]
