"""
Collect Materials Plugin

This plugin collects material and shader assets from the Maya scene.
It identifies materials, textures, and shading networks for validation.
"""

import pyblish.api
import sys
import os

# Add utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.maya_utils import get_scene_name
from config.settings import DEFAULT_PLUGIN_ORDERS


class CollectMaterials(pyblish.api.ContextPlugin):
    """Collect material assets from the scene."""
    
    label = "Collect Materials"
    order = DEFAULT_PLUGIN_ORDERS.get("collect_materials", 25)
    hosts = ["maya"]
    
    def process(self, context):
        """Main processing function."""
        print("\n" + "="*50)
        print("[Collect Materials] Starting material collection...")
        print("="*50)
        
        # Get scene information
        scene_name = get_scene_name()
        print(f"[Collect Materials] Scene: {scene_name}")
        
        # Get material components
        materials = self.get_materials()
        textures = self.get_texture_files()
        shading_groups = self.get_shading_groups()
        
        print(f"[Collect Materials] Found {len(materials)} materials")
        print(f"[Collect Materials] Found {len(textures)} texture files")
        print(f"[Collect Materials] Found {len(shading_groups)} shading groups")
        
        if not materials and not shading_groups:
            print("[Collect Materials] No materials found in scene")
            return
        
        # Group materials into logical units
        material_groups = self.group_materials(materials, textures, shading_groups)
        
        # Create instances for each material group
        for group_name, components in material_groups.items():
            instance = context.create_instance(group_name)
            
            # Get material statistics
            material_stats = self.get_material_statistics(components)
            
            instance.data.update({
                "family": "Material",  # Display name in Pyblish UI
                "families": ["material", "shader", "texture"],  # Tags for validation
                "asset": group_name,
                "materials": components.get("materials", []),
                "textures": components.get("textures", []),
                "shading_groups": components.get("shading_groups", []),
                "material_count": len(components.get("materials", [])),
                "texture_count": len(components.get("textures", [])),
                "shading_group_count": len(components.get("shading_groups", [])),
                "texture_resolution": material_stats.get("max_texture_resolution"),
                "total_texture_size": material_stats.get("total_texture_size"),
                "missing_textures": material_stats.get("missing_textures", []),
                "scene": scene_name,
                "plugin": self.__class__.__name__,
                "icon": "paint-brush",
                "description": f"Material group with {len(components.get('materials', []))} materials and {len(components.get('textures', []))} textures",
                "publish": True
            })
            
            # Add material components to instance
            for material in components.get("materials", []):
                instance.append(material)
            for sg in components.get("shading_groups", []):
                instance.append(sg)
            
            print(f"[Collect Materials] Created instance: {group_name}")
            print(f"  - Materials: {len(components.get('materials', []))}")
            print(f"  - Textures: {len(components.get('textures', []))}")
            print(f"  - Shading Groups: {len(components.get('shading_groups', []))}")
            print(f"  - Missing Textures: {len(material_stats.get('missing_textures', []))}")
            print(f"  - Families: {instance.data['families']}")
        
        print(f"[Collect Materials] Collection completed - {len(material_groups)} material groups")
        print("="*50 + "\n")
    
    def get_materials(self):
        """Get all material nodes in the scene."""
        try:
            import maya.cmds as cmds
            
            # Common material types in Maya
            material_types = [
                'lambert', 'blinn', 'phong', 'phongE', 'anisotropic',
                'layeredShader', 'surfaceShader', 'useBackground',
                'aiStandardSurface', 'aiStandard',  # Arnold materials
                'RedshiftMaterial', 'RedshiftArchitectural',  # Redshift materials
                'VRayMtl', 'VRayBlendMtl',  # V-Ray materials
            ]
            
            materials = []
            for mat_type in material_types:
                found_materials = cmds.ls(type=mat_type, long=True) or []
                materials.extend(found_materials)
            
            # Filter out default materials
            default_materials = ['lambert1', 'particleCloud1', 'shaderGlow1']
            materials = [mat for mat in materials if mat.split('|')[-1] not in default_materials]
            
            return materials
            
        except ImportError:
            print("[Collect Materials] Maya not available")
            return []
    
    def get_texture_files(self):
        """Get all texture file nodes and their file paths."""
        try:
            import maya.cmds as cmds
            
            texture_nodes = cmds.ls(type='file', long=True) or []
            textures = []
            
            for node in texture_nodes:
                try:
                    file_path = cmds.getAttr(f"{node}.fileTextureName")
                    if file_path:
                        textures.append({
                            "node": node,
                            "file_path": file_path,
                            "exists": os.path.exists(file_path) if file_path else False
                        })
                except:
                    pass
            
            return textures
            
        except ImportError:
            print("[Collect Materials] Maya not available")
            return []
    
    def get_shading_groups(self):
        """Get all shading group nodes."""
        try:
            import maya.cmds as cmds
            
            shading_groups = cmds.ls(type='shadingEngine', long=True) or []
            
            # Filter out default shading groups
            default_sgs = ['initialShadingGroup', 'initialParticleSE']
            shading_groups = [sg for sg in shading_groups if sg.split('|')[-1] not in default_sgs]
            
            return shading_groups
            
        except ImportError:
            print("[Collect Materials] Maya not available")
            return []
    
    def group_materials(self, materials, textures, shading_groups):
        """Group materials into logical units."""
        groups = {}
        
        # Group by material naming convention
        for material in materials:
            material_name = material.split('|')[-1]
            group_name = self.determine_material_group(material_name)
            
            if group_name not in groups:
                groups[group_name] = {
                    "materials": [],
                    "textures": [],
                    "shading_groups": []
                }
            
            groups[group_name]["materials"].append(material)
            
            # Find related textures
            related_textures = self.find_related_textures(material, textures)
            groups[group_name]["textures"].extend(related_textures)
            
            # Find related shading groups
            related_sgs = self.find_related_shading_groups(material, shading_groups)
            groups[group_name]["shading_groups"].extend(related_sgs)
        
        # Handle orphaned shading groups
        orphaned_sgs = []
        for sg in shading_groups:
            if not any(sg in group["shading_groups"] for group in groups.values()):
                orphaned_sgs.append(sg)
        
        if orphaned_sgs:
            if "OrphanedMaterials" not in groups:
                groups["OrphanedMaterials"] = {
                    "materials": [],
                    "textures": [],
                    "shading_groups": []
                }
            groups["OrphanedMaterials"]["shading_groups"].extend(orphaned_sgs)
        
        # Remove duplicates
        for group in groups.values():
            group["textures"] = list(set([tex["node"] for tex in group["textures"]]))
            group["shading_groups"] = list(set(group["shading_groups"]))
        
        return groups
    
    def determine_material_group(self, material_name):
        """Determine material group based on material name."""
        # Common material group patterns
        if any(keyword in material_name.lower() for keyword in ['character', 'char', 'hero']):
            return 'CharacterMaterials'
        elif any(keyword in material_name.lower() for keyword in ['prop', 'object', 'obj']):
            return 'PropMaterials'
        elif any(keyword in material_name.lower() for keyword in ['environment', 'env', 'set']):
            return 'EnvironmentMaterials'
        elif any(keyword in material_name.lower() for keyword in ['vehicle', 'car', 'truck']):
            return 'VehicleMaterials'
        elif any(keyword in material_name.lower() for keyword in ['building', 'house', 'structure']):
            return 'ArchitectureMaterials'
        elif any(keyword in material_name.lower() for keyword in ['skin', 'flesh', 'body']):
            return 'SkinMaterials'
        elif any(keyword in material_name.lower() for keyword in ['hair', 'fur']):
            return 'HairMaterials'
        elif any(keyword in material_name.lower() for keyword in ['eye', 'eyes']):
            return 'EyeMaterials'
        elif any(keyword in material_name.lower() for keyword in ['cloth', 'fabric', 'clothing']):
            return 'ClothMaterials'
        else:
            # Extract group name from naming convention
            if '_' in material_name:
                prefix = material_name.split('_')[0]
                return f"{prefix.capitalize()}Materials"
            else:
                return 'DefaultMaterials'
    
    def find_related_textures(self, material, all_textures):
        """Find textures connected to a material."""
        try:
            import maya.cmds as cmds
            
            related_textures = []
            
            # Get all connections from the material
            connections = cmds.listConnections(material, source=True, destination=False) or []
            
            for texture_info in all_textures:
                texture_node = texture_info["node"]
                if texture_node in connections:
                    related_textures.append(texture_info)
                
                # Also check indirect connections
                texture_connections = cmds.listConnections(texture_node, source=False, destination=True) or []
                if any(conn in connections for conn in texture_connections):
                    if texture_info not in related_textures:
                        related_textures.append(texture_info)
            
            return related_textures
            
        except ImportError:
            return []
    
    def find_related_shading_groups(self, material, all_shading_groups):
        """Find shading groups connected to a material."""
        try:
            import maya.cmds as cmds
            
            related_sgs = []
            
            # Check direct connections
            connections = cmds.listConnections(material, source=False, destination=True, type='shadingEngine') or []
            
            for sg in all_shading_groups:
                if sg in connections:
                    related_sgs.append(sg)
            
            return related_sgs
            
        except ImportError:
            return []
    
    def get_material_statistics(self, components):
        """Get statistics about the material group."""
        try:
            import maya.cmds as cmds
            
            textures = components.get("textures", [])
            missing_textures = []
            total_size = 0
            max_resolution = 0
            
            # Analyze texture files
            for texture_node in textures:
                try:
                    file_path = cmds.getAttr(f"{texture_node}.fileTextureName")
                    if file_path:
                        if not os.path.exists(file_path):
                            missing_textures.append(file_path)
                        else:
                            # Get file size
                            try:
                                size = os.path.getsize(file_path)
                                total_size += size
                            except:
                                pass
                            
                            # Try to get resolution (basic check)
                            try:
                                from PIL import Image
                                with Image.open(file_path) as img:
                                    width, height = img.size
                                    resolution = max(width, height)
                                    max_resolution = max(max_resolution, resolution)
                            except:
                                pass
                except:
                    pass
            
            return {
                "missing_textures": missing_textures,
                "total_texture_size": total_size,
                "max_texture_resolution": max_resolution
            }
            
        except ImportError:
            return {
                "missing_textures": [],
                "total_texture_size": 0,
                "max_texture_resolution": 0
            }
