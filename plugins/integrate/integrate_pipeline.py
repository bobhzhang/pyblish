"""
Integrate Pipeline Plugin

This plugin performs final pipeline integration tasks.
It handles notifications, cleanup, and pipeline-specific operations.
"""

import pyblish.api
import os
import sys
from datetime import datetime

# Add utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.file_utils import ensure_directory, save_json
from config.settings import DEFAULT_PLUGIN_ORDERS, INTEGRATION


class IntegratePipeline(pyblish.api.InstancePlugin):
    """Perform final pipeline integration tasks."""
    
    label = "Integrate Pipeline"
    order = DEFAULT_PLUGIN_ORDERS.get("integrate_pipeline", 330)
    hosts = ["maya"]
    families = ["model", "rig", "animation", "material"]
    
    def process(self, instance):
        """Main processing function."""
        print("\n" + "="*50)
        print(f"[Integrate Pipeline] Processing: {instance.name}")
        print("="*50)

        # Respect manual selection
        if not bool(instance.data.get("publish", True)):
            print("[Integrate Pipeline] Skipped (publish=False)")
            return

        family = instance.data.get("family")
        asset_name = instance.data.get("asset", instance.name)

        print(f"[Integrate Pipeline] Family: {family}")
        print(f"[Integrate Pipeline] Asset: {asset_name}")

        # Create pipeline summary
        pipeline_summary = self.create_pipeline_summary(instance)
        
        # Save pipeline report
        self.save_pipeline_report(instance, pipeline_summary)
        
        # Send notifications if enabled
        if INTEGRATION.get("notification", {}).get("enabled", True):
            self.send_notifications(instance, pipeline_summary)
        
        # Perform cleanup tasks
        self.perform_cleanup(instance)
        
        # Update pipeline statistics
        self.update_pipeline_statistics(instance, pipeline_summary)
        
        print("[Integrate Pipeline] SUCCESS: Pipeline integration completed")
        print("="*50 + "\n")
    
    def create_pipeline_summary(self, instance):
        """Create a comprehensive summary of the pipeline execution."""
        family = instance.data.get("family")
        asset_name = instance.data.get("asset", instance.name)
        
        summary = {
            "asset_name": asset_name,
            "family": family,
            "completion_date": datetime.now().isoformat(),
            "status": "success",
            "pipeline_version": "1.0.0",
            "execution_summary": {}
        }
        
        # Collect execution data
        summary["execution_summary"] = {
            "collection": self.get_collection_summary(instance),
            "validation": self.get_validation_summary(instance),
            "extraction": self.get_extraction_summary(instance),
            "integration": self.get_integration_summary(instance)
        }
        
        # Calculate overall statistics
        summary["statistics"] = self.calculate_statistics(instance)
        
        # Add warnings and errors
        summary["warnings"] = instance.data.get("warnings", [])
        summary["errors"] = instance.data.get("errors", [])
        
        return summary
    
    def get_collection_summary(self, instance):
        """Get summary of collection phase."""
        family = instance.data.get("family")
        
        collection_summary = {
            "phase": "collection",
            "status": "completed",
            "items_collected": 0
        }
        
        if family == "model":
            meshes = instance.data.get("meshes", [])
            collection_summary["items_collected"] = len(meshes)
            collection_summary["meshes"] = len(meshes)
            
        elif family == "rig":
            joints = instance.data.get("joints", [])
            controls = instance.data.get("controls", [])
            collection_summary["items_collected"] = len(joints) + len(controls)
            collection_summary["joints"] = len(joints)
            collection_summary["controls"] = len(controls)
            
        elif family == "animation":
            animated_objects = instance.data.get("animated_objects", [])
            collection_summary["items_collected"] = len(animated_objects)
            collection_summary["animated_objects"] = len(animated_objects)
            
        elif family == "material":
            materials = instance.data.get("materials", [])
            textures = instance.data.get("textures", [])
            collection_summary["items_collected"] = len(materials) + len(textures)
            collection_summary["materials"] = len(materials)
            collection_summary["textures"] = len(textures)
        
        return collection_summary
    
    def get_validation_summary(self, instance):
        """Get summary of validation phase."""
        warnings = instance.data.get("warnings", [])
        errors = instance.data.get("errors", [])
        validation_failed = instance.data.get("validation_failed", False)
        
        validation_summary = {
            "phase": "validation",
            "status": "failed" if validation_failed else "passed",
            "warning_count": len(warnings),
            "error_count": len(errors)
        }
        
        # Add specific validation results
        if instance.data.get("polycount"):
            validation_summary["polycount_check"] = "passed"
        
        return validation_summary
    
    def get_extraction_summary(self, instance):
        """Get summary of extraction phase."""
        extraction_summary = {
            "phase": "extraction",
            "status": "completed",
            "exports": {}
        }
        
        # Check for exported files
        export_keys = [
            ("fbx", "fbx_export_path"),
            ("obj", "obj_export_path"),
            ("alembic", "alembic_export_path"),
            ("textures", "texture_export_dir")
        ]
        
        total_size_mb = 0
        export_count = 0
        
        for export_type, data_key in export_keys:
            if data_key in instance.data:
                path = instance.data[data_key]
                if path and os.path.exists(path):
                    size_mb = self.get_path_size_mb(path)
                    extraction_summary["exports"][export_type] = {
                        "path": path,
                        "size_mb": round(size_mb, 2),
                        "status": "success"
                    }
                    total_size_mb += size_mb
                    export_count += 1
        
        extraction_summary["total_exports"] = export_count
        extraction_summary["total_size_mb"] = round(total_size_mb, 2)
        
        return extraction_summary
    
    def get_integration_summary(self, instance):
        """Get summary of integration phase."""
        integration_summary = {
            "phase": "integration",
            "status": "completed",
            "version_controlled": instance.data.get("version_controlled", False),
            "database_integrated": instance.data.get("database_integrated", False)
        }
        
        # Add commit information if available
        if instance.data.get("commit_hash"):
            integration_summary["commit_hash"] = instance.data["commit_hash"]
        
        # Add database record path if available
        if instance.data.get("database_record_path"):
            integration_summary["database_record"] = instance.data["database_record_path"]
        
        return integration_summary
    
    def calculate_statistics(self, instance):
        """Calculate overall pipeline statistics."""
        statistics = {
            "total_files_created": 0,
            "total_size_mb": 0,
            "processing_time": "unknown"
        }
        
        # Count created files
        file_keys = ["fbx_export_path", "obj_export_path", "alembic_export_path", "mtl_export_path"]
        for key in file_keys:
            if key in instance.data and instance.data[key]:
                if os.path.exists(instance.data[key]):
                    statistics["total_files_created"] += 1
                    statistics["total_size_mb"] += self.get_path_size_mb(instance.data[key])
        
        # Count extracted textures
        extracted_textures = instance.data.get("extracted_textures", [])
        statistics["total_files_created"] += len(extracted_textures)
        for texture in extracted_textures:
            statistics["total_size_mb"] += texture.get("size_mb", 0)
        
        statistics["total_size_mb"] = round(statistics["total_size_mb"], 2)
        
        return statistics
    
    def save_pipeline_report(self, instance, summary):
        """Save pipeline execution report."""
        try:
            # Get report directory
            scene_path = instance.data.get("scene", "")
            if scene_path and os.path.dirname(scene_path):
                base_dir = os.path.dirname(scene_path)
            else:
                base_dir = os.getcwd()
            
            reports_dir = os.path.join(base_dir, "pipeline_reports")
            ensure_directory(reports_dir)
            
            # Create report filename
            asset_name = instance.data.get("asset", instance.name)
            family = instance.data.get("family")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            report_filename = f"{asset_name}_{family}_pipeline_report_{timestamp}.json"
            report_path = os.path.join(reports_dir, report_filename)
            
            # Save report
            save_json(summary, report_path)
            
            print(f"[Integrate Pipeline] Saved pipeline report: {report_path}")
            instance.data["pipeline_report_path"] = report_path
            
        except Exception as e:
            print(f"[Integrate Pipeline] Failed to save pipeline report: {e}")
    
    def send_notifications(self, instance, summary):
        """Send notifications about pipeline completion."""
        try:
            asset_name = instance.data.get("asset", instance.name)
            family = instance.data.get("family")
            
            # Determine if this is a success or failure
            has_errors = len(summary.get("errors", [])) > 0
            validation_failed = summary["execution_summary"]["validation"]["status"] == "failed"
            
            is_success = not (has_errors or validation_failed)
            
            # Check notification settings
            notification_settings = INTEGRATION.get("notification", {})
            should_notify = False
            
            if is_success and notification_settings.get("email_on_success", False):
                should_notify = True
            elif not is_success and notification_settings.get("email_on_failure", True):
                should_notify = True
            
            if should_notify:
                self.create_notification_message(instance, summary, is_success)
            
        except Exception as e:
            print(f"[Integrate Pipeline] Failed to send notifications: {e}")
    
    def create_notification_message(self, instance, summary, is_success):
        """Create notification message."""
        asset_name = instance.data.get("asset", instance.name)
        family = instance.data.get("family")
        
        status = "SUCCESS" if is_success else "FAILED"
        
        message = f"""
Pipeline {status}: {asset_name} ({family})

Summary:
- Status: {status}
- Files Created: {summary['statistics']['total_files_created']}
- Total Size: {summary['statistics']['total_size_mb']} MB
- Warnings: {len(summary.get('warnings', []))}
- Errors: {len(summary.get('errors', []))}

Completion Time: {summary['completion_date']}
"""
        
        print(f"[Integrate Pipeline] Notification: {message}")
        
        # Here you could integrate with actual notification systems
        # like email, Slack, Discord, etc.
    
    def perform_cleanup(self, instance):
        """Perform cleanup tasks."""
        print("[Integrate Pipeline] Performing cleanup tasks...")
        
        # Clean up temporary files
        # (Add specific cleanup logic here)
        
        # Clear Maya selection
        try:
            import maya.cmds as cmds
            cmds.select(clear=True)
        except ImportError:
            pass
        
        print("[Integrate Pipeline] Cleanup completed")
    
    def update_pipeline_statistics(self, instance, summary):
        """Update global pipeline statistics."""
        try:
            # Get statistics directory
            scene_path = instance.data.get("scene", "")
            if scene_path and os.path.dirname(scene_path):
                base_dir = os.path.dirname(scene_path)
            else:
                base_dir = os.getcwd()
            
            stats_dir = os.path.join(base_dir, "pipeline_statistics")
            ensure_directory(stats_dir)
            
            stats_file = os.path.join(stats_dir, "pipeline_stats.json")
            
            # Load existing statistics
            if os.path.exists(stats_file):
                with open(stats_file, 'r') as f:
                    import json
                    stats = json.load(f)
            else:
                stats = {
                    "total_assets_processed": 0,
                    "assets_by_family": {},
                    "total_files_created": 0,
                    "total_size_mb": 0,
                    "last_updated": ""
                }
            
            # Update statistics
            family = instance.data.get("family")
            
            stats["total_assets_processed"] += 1
            stats["assets_by_family"][family] = stats["assets_by_family"].get(family, 0) + 1
            stats["total_files_created"] += summary["statistics"]["total_files_created"]
            stats["total_size_mb"] += summary["statistics"]["total_size_mb"]
            stats["last_updated"] = datetime.now().isoformat()
            
            # Save updated statistics
            save_json(stats, stats_file)
            
            print(f"[Integrate Pipeline] Updated pipeline statistics: {stats_file}")
            
        except Exception as e:
            print(f"[Integrate Pipeline] Failed to update statistics: {e}")
    
    def get_path_size_mb(self, path):
        """Get size of path in megabytes."""
        if os.path.isfile(path):
            return os.path.getsize(path) / (1024 * 1024)
        elif os.path.isdir(path):
            total_size = 0
            for root, dirs, files in os.walk(path):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        total_size += os.path.getsize(file_path)
                    except OSError:
                        continue
            return total_size / (1024 * 1024)
        return 0
