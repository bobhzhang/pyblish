"""
Validate Scene Settings Plugin

This plugin validates Maya scene settings for consistency and standards.
It checks units, frame rates, render settings, and other scene properties.
"""

import pyblish.api
import sys
import os

# Add utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.maya_utils import get_scene_units, get_fps, get_frame_range
from config.settings import DEFAULT_PLUGIN_ORDERS


class ValidateSceneSettings(pyblish.api.ContextPlugin):
    """Validate Maya scene settings for consistency."""
    
    label = "Validate Scene Settings"
    order = DEFAULT_PLUGIN_ORDERS.get("validate_scene_settings", 140)
    hosts = ["maya"]
    
    # Expected scene settings
    EXPECTED_SETTINGS = {
        'linear_unit': 'cm',
        'angular_unit': 'deg',
        'time_unit': 'film',  # 24 fps
        'fps': 24,
        'min_frame_range': 10  # Minimum frame range length
    }
    
    def process(self, context):
        """Main processing function."""
        print("\n" + "="*50)
        print("[Validate Scene Settings] Validating scene settings...")
        print("="*50)
        
        # Validate units
        self.validate_units()
        
        # Validate frame rate and time settings
        self.validate_time_settings()
        
        # Validate frame range
        self.validate_frame_range()
        
        # Validate render settings
        self.validate_render_settings()
        
        # Validate scene scale
        self.validate_scene_scale()
        
        print("[Validate Scene Settings] PASSED: Scene settings validation completed")
        print("="*50 + "\n")
    
    def validate_units(self):
        """Validate scene units."""
        print("[Validate Scene Settings] Checking scene units...")
        
        units = get_scene_units()
        linear_unit = units['linear']
        angular_unit = units['angular']
        
        print(f"  - Linear unit: {linear_unit}")
        print(f"  - Angular unit: {angular_unit}")
        
        issues = []
        
        # Check linear unit
        expected_linear = self.EXPECTED_SETTINGS['linear_unit']
        if linear_unit != expected_linear:
            issues.append(f"Linear unit is '{linear_unit}', expected '{expected_linear}'")
        
        # Check angular unit
        expected_angular = self.EXPECTED_SETTINGS['angular_unit']
        if angular_unit != expected_angular:
            issues.append(f"Angular unit is '{angular_unit}', expected '{expected_angular}'")
        
        if issues:
            error_msg = "Scene unit issues found:\n" + "\n".join(f"  - {issue}" for issue in issues)
            print(f"[Validate Scene Settings] FAILED: {error_msg}")
            raise ValueError(error_msg)
        
        print("[Validate Scene Settings] Units validation passed")
    
    def validate_time_settings(self):
        """Validate time and frame rate settings."""
        print("[Validate Scene Settings] Checking time settings...")
        
        units = get_scene_units()
        time_unit = units['time']
        fps = get_fps()
        
        print(f"  - Time unit: {time_unit}")
        print(f"  - FPS: {fps}")
        
        issues = []
        
        # Check time unit
        expected_time_unit = self.EXPECTED_SETTINGS['time_unit']
        if time_unit != expected_time_unit:
            issues.append(f"Time unit is '{time_unit}', expected '{expected_time_unit}'")
        
        # Check FPS
        expected_fps = self.EXPECTED_SETTINGS['fps']
        if fps != expected_fps:
            issues.append(f"FPS is {fps}, expected {expected_fps}")
        
        if issues:
            warning_msg = "Time setting issues found:\n" + "\n".join(f"  - {issue}" for issue in issues)
            print(f"[Validate Scene Settings] WARNING: {warning_msg}")
            # Don't fail for time settings, just warn
        else:
            print("[Validate Scene Settings] Time settings validation passed")
    
    def validate_frame_range(self):
        """Validate frame range settings."""
        print("[Validate Scene Settings] Checking frame range...")
        
        start_frame, end_frame = get_frame_range()
        frame_count = end_frame - start_frame + 1
        
        print(f"  - Start frame: {start_frame}")
        print(f"  - End frame: {end_frame}")
        print(f"  - Frame count: {frame_count}")
        
        min_range = self.EXPECTED_SETTINGS['min_frame_range']
        
        if frame_count < min_range:
            warning_msg = (
                f"Frame range is very short: {frame_count} frames\n"
                f"Consider using at least {min_range} frames for proper animation"
            )
            print(f"[Validate Scene Settings] WARNING: {warning_msg}")
        else:
            print("[Validate Scene Settings] Frame range validation passed")
    
    def validate_render_settings(self):
        """Validate render settings."""
        print("[Validate Scene Settings] Checking render settings...")
        
        try:
            import maya.cmds as cmds
            
            # Get current renderer
            current_renderer = cmds.getAttr("defaultRenderGlobals.currentRenderer")
            print(f"  - Current renderer: {current_renderer}")
            
            # Check image format
            image_format = cmds.getAttr("defaultRenderGlobals.imageFormat")
            print(f"  - Image format: {image_format}")
            
            # Check resolution
            width = cmds.getAttr("defaultResolution.width")
            height = cmds.getAttr("defaultResolution.height")
            print(f"  - Resolution: {width}x{height}")
            
            # Validate common issues
            issues = []
            
            # Check for reasonable resolution
            if width < 640 or height < 480:
                issues.append(f"Resolution is very low: {width}x{height}")
            
            # Check for common problematic settings
            if current_renderer == "mayaSoftware":
                issues.append("Using legacy Maya Software renderer - consider using Arnold or other modern renderer")
            
            if issues:
                warning_msg = "Render setting issues found:\n" + "\n".join(f"  - {issue}" for issue in issues)
                print(f"[Validate Scene Settings] WARNING: {warning_msg}")
            else:
                print("[Validate Scene Settings] Render settings validation passed")
                
        except ImportError:
            print("Maya not available - skipping render settings validation")
        except Exception as e:
            print(f"[Validate Scene Settings] Could not validate render settings: {e}")
    
    def validate_scene_scale(self):
        """Validate scene scale and object sizes."""
        print("[Validate Scene Settings] Checking scene scale...")
        
        try:
            import maya.cmds as cmds
            from utils.maya_utils import get_meshes
            
            meshes = get_meshes()
            if not meshes:
                print("  - No meshes found to validate scale")
                return
            
            # Check bounding box sizes
            very_large_objects = []
            very_small_objects = []
            
            for mesh in meshes[:10]:  # Check first 10 meshes
                try:
                    bbox = cmds.exactWorldBoundingBox(mesh)
                    if bbox:
                        width = bbox[3] - bbox[0]
                        height = bbox[4] - bbox[1]
                        depth = bbox[5] - bbox[2]
                        
                        max_dimension = max(width, height, depth)
                        
                        # Check for very large objects (> 1000 units)
                        if max_dimension > 1000:
                            very_large_objects.append({
                                'mesh': mesh.split('|')[-1],
                                'size': max_dimension
                            })
                        
                        # Check for very small objects (< 0.01 units)
                        elif max_dimension < 0.01:
                            very_small_objects.append({
                                'mesh': mesh.split('|')[-1],
                                'size': max_dimension
                            })
                except:
                    continue
            
            # Report scale issues as warnings
            warnings = []
            
            if very_large_objects:
                warning = "Very large objects detected (>1000 units):\n"
                for obj in very_large_objects:
                    warning += f"  - {obj['mesh']}: {obj['size']:.2f} units\n"
                warnings.append(warning)
            
            if very_small_objects:
                warning = "Very small objects detected (<0.01 units):\n"
                for obj in very_small_objects:
                    warning += f"  - {obj['mesh']}: {obj['size']:.4f} units\n"
                warnings.append(warning)
            
            if warnings:
                warning_msg = "\n".join(warnings)
                print(f"[Validate Scene Settings] WARNING: {warning_msg}")
            else:
                print("[Validate Scene Settings] Scene scale validation passed")
                
        except ImportError:
            print("Maya not available - skipping scene scale validation")
        except Exception as e:
            print(f"[Validate Scene Settings] Could not validate scene scale: {e}")
