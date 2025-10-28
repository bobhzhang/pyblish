"""
Validate Polycount Plugin

This plugin validates that model assets meet polygon count requirements.
It checks face and vertex counts against defined quality standards.
"""

import pyblish.api
import sys
import os

# Add utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.maya_utils import get_polycount
from config.settings import DEFAULT_PLUGIN_ORDERS, QUALITY_STANDARDS


class ValidatePolycount(pyblish.api.InstancePlugin):
    """Validate polygon count for model assets."""
    
    label = "Validate Polycount"
    order = DEFAULT_PLUGIN_ORDERS.get("validate_polycount", 120)
    hosts = ["maya"]
    families = ["model"]
    
    def process(self, instance):
        """Main processing function."""
        print("\n" + "="*50)
        print(f"[Validate Polycount] Validating: {instance.name}")
        print("="*50)

        # Respect manual selection
        if not bool(instance.data.get("publish", True)):
            print("[Validate Polycount] Skipped (publish=False)")
            return

        # Get meshes from instance
        meshes = instance.data.get("meshes", [])
        if not meshes:
            print("[Validate Polycount] No meshes found in instance")
            return
        
        print(f"[Validate Polycount] Checking {len(meshes)} meshes")
        
        # Get polycount for all meshes
        polycount_info = get_polycount(meshes)
        total_faces = polycount_info['faces']
        total_vertices = polycount_info['vertices']
        
        print(f"[Validate Polycount] Total faces: {total_faces}")
        print(f"[Validate Polycount] Total vertices: {total_vertices}")
        
        # Store polycount info in instance data
        instance.data["polycount"] = polycount_info
        
        # Determine asset type for validation
        asset_type = self.determine_asset_type(instance)
        print(f"[Validate Polycount] Asset type: {asset_type}")
        
        # Get quality standards
        max_polycount = QUALITY_STANDARDS["max_polycount"].get(asset_type, 50000)
        print(f"[Validate Polycount] Maximum allowed faces: {max_polycount}")
        
        # Validate polycount
        if total_faces > max_polycount:
            error_msg = (
                f"Polycount exceeds limit for {asset_type}!\n"
                f"Current: {total_faces} faces\n"
                f"Maximum: {max_polycount} faces\n"
                f"Excess: {total_faces - max_polycount} faces"
            )
            print(f"[Validate Polycount] FAILED: {error_msg}")
            raise ValueError(error_msg)
        
        # Check individual mesh polycounts
        self.validate_individual_meshes(meshes, asset_type)
        
        print(f"[Validate Polycount] PASSED: Polycount within limits")
        print(f"[Validate Polycount] Used {total_faces}/{max_polycount} faces ({(total_faces/max_polycount)*100:.1f}%)")
        print("="*50 + "\n")
    
    def determine_asset_type(self, instance):
        """Determine asset type from instance data or name."""
        # Check if asset type is explicitly set
        asset_type = instance.data.get("asset_type")
        if asset_type:
            return asset_type
        
        # Determine from instance name
        name = instance.name.lower()
        
        if any(keyword in name for keyword in ['character', 'char', 'hero', 'person', 'human']):
            return 'character'
        elif any(keyword in name for keyword in ['environment', 'env', 'building', 'landscape', 'terrain']):
            return 'environment'
        else:
            return 'prop'  # Default to prop
    
    def validate_individual_meshes(self, meshes, asset_type):
        """Validate individual mesh polycounts."""
        print("[Validate Polycount] Checking individual meshes:")
        
        # Define per-mesh limits based on asset type
        per_mesh_limits = {
            'character': 10000,
            'prop': 5000,
            'environment': 20000
        }
        
        max_per_mesh = per_mesh_limits.get(asset_type, 5000)
        
        high_poly_meshes = []
        
        for mesh in meshes:
            mesh_polycount = get_polycount([mesh])
            mesh_faces = mesh_polycount['faces']
            
            mesh_name = mesh.split('|')[-1]  # Get short name
            print(f"  - {mesh_name}: {mesh_faces} faces")
            
            if mesh_faces > max_per_mesh:
                high_poly_meshes.append({
                    'mesh': mesh_name,
                    'faces': mesh_faces,
                    'limit': max_per_mesh
                })
        
        # Report high poly meshes as warnings
        if high_poly_meshes:
            warning_msg = "High polygon count meshes detected:\n"
            for mesh_info in high_poly_meshes:
                warning_msg += (
                    f"  - {mesh_info['mesh']}: {mesh_info['faces']} faces "
                    f"(limit: {mesh_info['limit']})\n"
                )
            print(f"[Validate Polycount] WARNING: {warning_msg}")
            
            # Store warning in instance data
            if "warnings" not in instance.data:
                instance.data["warnings"] = []
            instance.data["warnings"].append(warning_msg)
