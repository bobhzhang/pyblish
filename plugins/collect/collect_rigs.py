"""
Collect Rigs Plugin

This plugin collects character and object rigs from the Maya scene.
It identifies rig hierarchies, control systems, and joint chains for validation.
"""

import pyblish.api
import sys
import os

# Add utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.maya_utils import get_objects_by_type, get_scene_name
from config.settings import DEFAULT_PLUGIN_ORDERS


class CollectRigs(pyblish.api.ContextPlugin):
    """Collect rig assets from the scene."""
    
    label = "Collect Rigs"
    order = DEFAULT_PLUGIN_ORDERS.get("collect_rigs", 30)
    hosts = ["maya"]
    
    def process(self, context):
        """Main processing function."""
        print("\n" + "="*50)
        print("[Collect Rigs] Starting rig collection...")
        print("="*50)
        
        # Get scene information
        scene_name = get_scene_name()
        print(f"[Collect Rigs] Scene: {scene_name}")
        
        # Get rig components
        joints = self.get_joints()
        controls = self.get_rig_controls()
        constraints = self.get_constraints()
        
        print(f"[Collect Rigs] Found {len(joints)} joints")
        print(f"[Collect Rigs] Found {len(controls)} rig controls")
        print(f"[Collect Rigs] Found {len(constraints)} constraints")
        
        if not joints and not controls:
            print("[Collect Rigs] No rig components found in scene")
            return
        
        # Group rig components into logical rig units
        rig_groups = self.group_rig_components(joints, controls, constraints)
        
        # Create instances for each rig group
        for group_name, components in rig_groups.items():
            instance = context.create_instance(group_name)
            
            # Get rig statistics
            rig_stats = self.get_rig_statistics(components)
            
            instance.data.update({
                "family": "Rig",  # Display name in Pyblish UI
                "families": ["rig", "skeleton", "controls"],  # Tags for validation
                "asset": group_name,
                "joints": components.get("joints", []),
                "controls": components.get("controls", []),
                "constraints": components.get("constraints", []),
                "joint_count": len(components.get("joints", [])),
                "control_count": len(components.get("controls", [])),
                "constraint_count": len(components.get("constraints", [])),
                "root_joint": rig_stats.get("root_joint"),
                "joint_hierarchy_depth": rig_stats.get("hierarchy_depth", 0),
                "scene": scene_name,
                "plugin": self.__class__.__name__,
                "icon": "user",
                "description": f"Rig with {len(components.get('joints', []))} joints and {len(components.get('controls', []))} controls",
                "publish": True
            })
            
            # Add rig components to instance
            for joint in components.get("joints", []):
                instance.append(joint)
            for control in components.get("controls", []):
                instance.append(control)
            
            print(f"[Collect Rigs] Created instance: {group_name}")
            print(f"  - Joints: {len(components.get('joints', []))}")
            print(f"  - Controls: {len(components.get('controls', []))}")
            print(f"  - Constraints: {len(components.get('constraints', []))}")
            print(f"  - Root Joint: {rig_stats.get('root_joint', 'None')}")
            print(f"  - Families: {instance.data['families']}")
        
        print(f"[Collect Rigs] Collection completed - {len(rig_groups)} rig groups")
        print("="*50 + "\n")
    
    def get_joints(self):
        """Get all joint objects in the scene."""
        try:
            import maya.cmds as cmds
            joints = cmds.ls(type='joint', long=True) or []
            return joints
        except ImportError:
            print("[Collect Rigs] Maya not available")
            return []
    
    def get_rig_controls(self):
        """Get rig control objects (typically NURBS curves or custom shapes)."""
        try:
            import maya.cmds as cmds
            controls = []
            
            # Look for NURBS curves (common for rig controls)
            nurbs_curves = cmds.ls(type='nurbsCurve', long=True) or []
            for curve in nurbs_curves:
                # Get transform parent
                transforms = cmds.listRelatives(curve, parent=True, type='transform', fullPath=True) or []
                for transform in transforms:
                    if self.is_rig_control(transform):
                        controls.append(transform)
            
            # Look for objects with specific naming patterns
            all_transforms = cmds.ls(type='transform', long=True) or []
            for transform in all_transforms:
                short_name = transform.split('|')[-1]
                if any(keyword in short_name.lower() for keyword in ['ctrl', 'control', 'ctl']):
                    if transform not in controls:
                        controls.append(transform)
            
            return list(set(controls))  # Remove duplicates
            
        except ImportError:
            print("[Collect Rigs] Maya not available")
            return []
    
    def get_constraints(self):
        """Get constraint objects in the scene."""
        try:
            import maya.cmds as cmds
            constraint_types = [
                'parentConstraint', 'pointConstraint', 'orientConstraint',
                'scaleConstraint', 'aimConstraint', 'poleVectorConstraint',
                'geometryConstraint', 'normalConstraint', 'tangentConstraint'
            ]
            
            constraints = []
            for constraint_type in constraint_types:
                found_constraints = cmds.ls(type=constraint_type, long=True) or []
                constraints.extend(found_constraints)
            
            return constraints
            
        except ImportError:
            print("[Collect Rigs] Maya not available")
            return []
    
    def is_rig_control(self, transform):
        """Check if a transform is likely a rig control."""
        try:
            import maya.cmds as cmds
            
            short_name = transform.split('|')[-1]
            
            # Check naming patterns
            if any(keyword in short_name.lower() for keyword in ['ctrl', 'control', 'ctl']):
                return True
            
            # Check for custom attributes (common on rig controls)
            user_attrs = cmds.listAttr(transform, userDefined=True) or []
            if user_attrs:
                return True
            
            # Check if it has NURBS curve shapes
            shapes = cmds.listRelatives(transform, shapes=True, type='nurbsCurve') or []
            if shapes:
                return True
            
            return False
            
        except ImportError:
            return False
    
    def group_rig_components(self, joints, controls, constraints):
        """Group rig components into logical rig units."""
        groups = {}
        
        # Group by root joints
        root_joints = self.find_root_joints(joints)
        
        for root_joint in root_joints:
            group_name = self.determine_rig_group_name(root_joint)
            
            # Get all joints in this hierarchy
            hierarchy_joints = self.get_joint_hierarchy(root_joint, joints)
            
            # Find related controls
            related_controls = self.find_related_controls(hierarchy_joints, controls)
            
            # Find related constraints
            related_constraints = self.find_related_constraints(hierarchy_joints + related_controls, constraints)
            
            groups[group_name] = {
                "joints": hierarchy_joints,
                "controls": related_controls,
                "constraints": related_constraints,
                "root_joint": root_joint
            }
        
        # Handle orphaned controls (controls not associated with any joint hierarchy)
        orphaned_controls = [ctrl for ctrl in controls if not any(ctrl in group["controls"] for group in groups.values())]
        if orphaned_controls:
            groups["OrphanedControls"] = {
                "joints": [],
                "controls": orphaned_controls,
                "constraints": [],
                "root_joint": None
            }
        
        return groups
    
    def find_root_joints(self, joints):
        """Find root joints (joints with no joint parents)."""
        try:
            import maya.cmds as cmds
            root_joints = []
            
            for joint in joints:
                parent = cmds.listRelatives(joint, parent=True, type='joint')
                if not parent:
                    root_joints.append(joint)
            
            return root_joints
            
        except ImportError:
            return []
    
    def get_joint_hierarchy(self, root_joint, all_joints):
        """Get all joints in a hierarchy starting from root joint."""
        try:
            import maya.cmds as cmds
            hierarchy = [root_joint]
            
            # Get all descendants that are joints
            descendants = cmds.listRelatives(root_joint, allDescendents=True, type='joint', fullPath=True) or []
            hierarchy.extend(descendants)
            
            return hierarchy
            
        except ImportError:
            return [root_joint]
    
    def find_related_controls(self, joints, all_controls):
        """Find controls related to a joint hierarchy."""
        try:
            import maya.cmds as cmds
            related_controls = []
            
            for control in all_controls:
                # Check if control is connected to any joint in the hierarchy
                for joint in joints:
                    connections = cmds.listConnections(control, destination=True) or []
                    if joint in connections:
                        related_controls.append(control)
                        break
                    
                    # Also check by naming convention
                    control_name = control.split('|')[-1]
                    joint_name = joint.split('|')[-1]
                    if any(part in control_name.lower() for part in joint_name.lower().split('_')):
                        if control not in related_controls:
                            related_controls.append(control)
            
            return related_controls
            
        except ImportError:
            return []
    
    def find_related_constraints(self, objects, all_constraints):
        """Find constraints related to a list of objects."""
        try:
            import maya.cmds as cmds
            related_constraints = []
            
            for constraint in all_constraints:
                # Check if constraint is connected to any object
                connections = cmds.listConnections(constraint) or []
                if any(obj in connections for obj in objects):
                    related_constraints.append(constraint)
            
            return related_constraints
            
        except ImportError:
            return []
    
    def determine_rig_group_name(self, root_joint):
        """Determine rig group name based on root joint name."""
        joint_name = root_joint.split('|')[-1]
        
        # Common rig naming patterns
        if any(keyword in joint_name.lower() for keyword in ['character', 'char', 'hero']):
            return 'CharacterRig'
        elif any(keyword in joint_name.lower() for keyword in ['face', 'facial']):
            return 'FacialRig'
        elif any(keyword in joint_name.lower() for keyword in ['hand', 'finger']):
            return 'HandRig'
        elif any(keyword in joint_name.lower() for keyword in ['spine', 'back']):
            return 'SpineRig'
        elif any(keyword in joint_name.lower() for keyword in ['leg', 'foot']):
            return 'LegRig'
        elif any(keyword in joint_name.lower() for keyword in ['arm', 'shoulder']):
            return 'ArmRig'
        else:
            # Extract name from joint (remove common suffixes)
            clean_name = joint_name.replace('_jnt', '').replace('_joint', '').replace('Joint', '')
            if '_' in clean_name:
                clean_name = clean_name.split('_')[0]
            return f"{clean_name.capitalize()}Rig"
    
    def get_rig_statistics(self, components):
        """Get statistics about the rig."""
        try:
            import maya.cmds as cmds
            
            joints = components.get("joints", [])
            root_joint = components.get("root_joint")
            
            # Calculate hierarchy depth
            max_depth = 0
            if root_joint and joints:
                for joint in joints:
                    depth = len(joint.split('|')) - len(root_joint.split('|'))
                    max_depth = max(max_depth, depth)
            
            return {
                "root_joint": root_joint.split('|')[-1] if root_joint else None,
                "hierarchy_depth": max_depth
            }
            
        except ImportError:
            return {
                "root_joint": None,
                "hierarchy_depth": 0
            }
