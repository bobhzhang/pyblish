"""
Validate Naming Plugin

This plugin validates that assets follow proper naming conventions.
It checks object names, file names, and hierarchy naming standards.
"""

import pyblish.api
import re
import sys
import os

# Add utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.maya_utils import validate_naming_convention
from config.settings import DEFAULT_PLUGIN_ORDERS, NAMING_PATTERNS


class ValidateNaming(pyblish.api.InstancePlugin):
    """Validate naming conventions for assets."""
    
    label = "Validate Naming"
    order = DEFAULT_PLUGIN_ORDERS.get("validate_naming", 110)
    hosts = ["maya"]
    families = ["model", "rig", "animation", "material", "scene"]
    
    def process(self, instance):
        """Main processing function."""
        print("\n" + "="*50)
        print(f"[Validate Naming] Validating: {instance.name}")
        print("="*50)

        family = instance.data.get("family", "unknown")
        print(f"[Validate Naming] Asset family: {family}")

        # Respect manual selection
        if not bool(instance.data.get("publish", True)):
            print("[Validate Naming] Skipped (publish=False)")
            return

        # Validate instance name
        self.validate_instance_name(instance)
        
        # Validate object names based on family
        if family == "model":
            self.validate_model_naming(instance)
        elif family == "rig":
            self.validate_rig_naming(instance)
        elif family == "animation":
            self.validate_animation_naming(instance)
        elif family == "material":
            self.validate_material_naming(instance)
        
        # Validate general naming rules
        self.validate_general_naming_rules(instance)
        
        print(f"[Validate Naming] PASSED: Naming conventions validated")
        print("="*50 + "\n")
    
    def validate_instance_name(self, instance):
        """Validate the instance name follows conventions."""
        name = instance.name
        family = instance.data.get("family", "unknown")
        
        print(f"[Validate Naming] Checking instance name: {name}")
        
        # Check for valid characters (alphanumeric, underscore, no spaces)
        if not re.match(r'^[A-Za-z][A-Za-z0-9_]*$', name):
            error_msg = (
                f"Instance name '{name}' contains invalid characters.\n"
                f"Names should start with a letter and contain only letters, numbers, and underscores."
            )
            print(f"[Validate Naming] FAILED: {error_msg}")
            raise ValueError(error_msg)
        
        # Check naming pattern for family if defined
        if family in NAMING_PATTERNS:
            pattern = NAMING_PATTERNS[family]
            if not re.match(pattern, name):
                warning_msg = (
                    f"Instance name '{name}' doesn't follow recommended pattern for {family}.\n"
                    f"Recommended pattern: {pattern}"
                )
                print(f"[Validate Naming] WARNING: {warning_msg}")
                
                # Store warning in instance data
                if "warnings" not in instance.data:
                    instance.data["warnings"] = []
                instance.data["warnings"].append(warning_msg)
        
        print(f"[Validate Naming] Instance name validation passed")
    
    def validate_model_naming(self, instance):
        """Validate naming for model assets."""
        meshes = instance.data.get("meshes", [])
        print(f"[Validate Naming] Validating {len(meshes)} mesh names")
        
        invalid_names = []
        
        for mesh in meshes:
            mesh_name = mesh.split('|')[-1]  # Get short name
            
            # Check for valid mesh naming
            if not self.is_valid_object_name(mesh_name):
                invalid_names.append(mesh_name)
        
        if invalid_names:
            error_msg = (
                f"Invalid mesh names found:\n" +
                "\n".join(f"  - {name}" for name in invalid_names) +
                "\nMesh names should follow camelCase or snake_case conventions."
            )
            print(f"[Validate Naming] FAILED: {error_msg}")
            raise ValueError(error_msg)
        
        print(f"[Validate Naming] Model naming validation passed")
    
    def validate_rig_naming(self, instance):
        """Validate naming for rig assets."""
        joints = instance.data.get("joints", [])
        controls = instance.data.get("controls", [])
        
        print(f"[Validate Naming] Validating {len(joints)} joint names")
        print(f"[Validate Naming] Validating {len(controls)} control names")
        
        invalid_joints = []
        invalid_controls = []
        
        # Validate joint names
        for joint in joints:
            joint_name = joint.split('|')[-1]
            if not self.is_valid_joint_name(joint_name):
                invalid_joints.append(joint_name)
        
        # Validate control names
        for control in controls:
            control_name = control.split('|')[-1]
            if not self.is_valid_control_name(control_name):
                invalid_controls.append(control_name)
        
        errors = []
        if invalid_joints:
            errors.append(
                "Invalid joint names:\n" +
                "\n".join(f"  - {name}" for name in invalid_joints)
            )
        
        if invalid_controls:
            errors.append(
                "Invalid control names:\n" +
                "\n".join(f"  - {name}" for name in invalid_controls)
            )
        
        if errors:
            error_msg = "\n\n".join(errors)
            print(f"[Validate Naming] FAILED: {error_msg}")
            raise ValueError(error_msg)
        
        print(f"[Validate Naming] Rig naming validation passed")
    
    def validate_animation_naming(self, instance):
        """Validate naming for animation assets."""
        animated_objects = instance.data.get("animated_objects", [])
        print(f"[Validate Naming] Validating {len(animated_objects)} animated object names")
        
        invalid_names = []
        
        for obj_data in animated_objects:
            obj_name = obj_data['object'].split('|')[-1]
            if not self.is_valid_object_name(obj_name):
                invalid_names.append(obj_name)
        
        if invalid_names:
            error_msg = (
                f"Invalid animated object names:\n" +
                "\n".join(f"  - {name}" for name in invalid_names)
            )
            print(f"[Validate Naming] FAILED: {error_msg}")
            raise ValueError(error_msg)
        
        print(f"[Validate Naming] Animation naming validation passed")
    
    def validate_material_naming(self, instance):
        """Validate naming for material assets."""
        materials = instance.data.get("materials", [])
        print(f"[Validate Naming] Validating {len(materials)} material names")
        
        invalid_names = []
        
        for material in materials:
            if not self.is_valid_material_name(material):
                invalid_names.append(material)
        
        if invalid_names:
            error_msg = (
                f"Invalid material names:\n" +
                "\n".join(f"  - {name}" for name in invalid_names)
            )
            print(f"[Validate Naming] FAILED: {error_msg}")
            raise ValueError(error_msg)
        
        print(f"[Validate Naming] Material naming validation passed")
    
    def validate_general_naming_rules(self, instance):
        """Validate general naming rules."""
        print(f"[Validate Naming] Checking general naming rules")
        
        # Check for reserved words
        reserved_words = ['con', 'prn', 'aux', 'nul', 'com1', 'com2', 'lpt1', 'lpt2']
        
        # Get all object names from instance
        all_objects = []
        for obj in instance:
            if isinstance(obj, str):
                all_objects.append(obj.split('|')[-1])
        
        reserved_violations = []
        for obj_name in all_objects:
            if obj_name.lower() in reserved_words:
                reserved_violations.append(obj_name)
        
        if reserved_violations:
            warning_msg = (
                f"Objects using reserved words found:\n" +
                "\n".join(f"  - {name}" for name in reserved_violations)
            )
            print(f"[Validate Naming] WARNING: {warning_msg}")
            
            if "warnings" not in instance.data:
                instance.data["warnings"] = []
            instance.data["warnings"].append(warning_msg)
    
    def is_valid_object_name(self, name):
        """Check if object name is valid."""
        # Should start with letter, contain only alphanumeric and underscore
        return bool(re.match(r'^[A-Za-z][A-Za-z0-9_]*$', name))
    
    def is_valid_joint_name(self, name):
        """Check if joint name is valid."""
        # Joints often have specific suffixes
        valid_suffixes = ['_jnt', '_joint', '_bone', '_Joint', '_Jnt']
        
        if any(name.endswith(suffix) for suffix in valid_suffixes):
            return self.is_valid_object_name(name)
        
        # Allow joints without suffix if they follow general naming
        return self.is_valid_object_name(name)
    
    def is_valid_control_name(self, name):
        """Check if control name is valid."""
        # Controls often have specific suffixes
        valid_suffixes = ['_ctrl', '_control', '_ctl', '_Ctrl', '_Control']
        
        if any(name.endswith(suffix) for suffix in valid_suffixes):
            return self.is_valid_object_name(name)
        
        # Allow controls without suffix if they follow general naming
        return self.is_valid_object_name(name)
    
    def is_valid_material_name(self, name):
        """Check if material name is valid."""
        # Materials often have specific suffixes
        valid_suffixes = ['_mat', '_material', '_shader', '_Mat', '_Material']
        
        if any(name.endswith(suffix) for suffix in valid_suffixes):
            return self.is_valid_object_name(name)
        
        # Allow materials without suffix if they follow general naming
        return self.is_valid_object_name(name)
