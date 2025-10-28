"""
Integrate Version Control Plugin

This plugin integrates exported assets into version control systems.
It handles Git operations and maintains version history.
"""

import pyblish.api
import os
import subprocess
import sys
from datetime import datetime

# Add utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.file_utils import ensure_directory
from config.settings import DEFAULT_PLUGIN_ORDERS, VERSION_CONTROL


class IntegrateVersionControl(pyblish.api.InstancePlugin):
    """Integrate assets into version control system."""
    
    label = "Integrate Version Control"
    order = DEFAULT_PLUGIN_ORDERS.get("integrate_version_control", 310)
    hosts = ["maya"]
    families = ["model", "rig", "animation", "material"]
    
    def process(self, instance):
        """Main processing function."""
        print("\n" + "="*50)
        print(f"[Integrate Version Control] Processing: {instance.name}")
        print("="*50)
        
        # Check if version control is enabled
        if not VERSION_CONTROL.get("enabled", True):
            print("[Integrate Version Control] Version control is disabled - skipping")
            return
        
        family = instance.data.get("family")
        asset_name = instance.data.get("asset", instance.name)
        
        print(f"[Integrate Version Control] Family: {family}")
        print(f"[Integrate Version Control] Asset: {asset_name}")
        
        # Get exported files from instance
        exported_files = self.get_exported_files(instance)
        
        if not exported_files:
            print("[Integrate Version Control] No exported files found to version")
            return
        
        print(f"[Integrate Version Control] Files to version: {len(exported_files)}")
        for file_path in exported_files:
            print(f"  - {file_path}")
        
        # Initialize or check Git repository
        repo_path = self.get_repository_path(exported_files[0])
        if not self.ensure_git_repository(repo_path):
            print("[Integrate Version Control] Failed to initialize Git repository")
            return
        
        # Add files to version control
        success = self.add_files_to_version_control(exported_files, repo_path, instance)
        
        if success:
            print("[Integrate Version Control] SUCCESS: Files added to version control")
            instance.data["version_controlled"] = True
            instance.data["repository_path"] = repo_path
        else:
            print("[Integrate Version Control] WARNING: Some files may not have been versioned properly")
        
        print("="*50 + "\n")
    
    def get_exported_files(self, instance):
        """Get list of exported files from instance data."""
        exported_files = []
        
        # Check for various export paths
        export_keys = [
            "fbx_export_path",
            "obj_export_path", 
            "mtl_export_path",
            "alembic_export_path",
            "texture_export_dir"
        ]
        
        for key in export_keys:
            if key in instance.data:
                path = instance.data[key]
                if path and os.path.exists(path):
                    if os.path.isfile(path):
                        exported_files.append(path)
                    elif os.path.isdir(path):
                        # Add all files in directory
                        for root, dirs, files in os.walk(path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                exported_files.append(file_path)
        
        # Check for extracted textures
        extracted_textures = instance.data.get("extracted_textures", [])
        for texture in extracted_textures:
            if "extracted_path" in texture:
                path = texture["extracted_path"]
                if os.path.exists(path):
                    exported_files.append(path)
        
        return list(set(exported_files))  # Remove duplicates
    
    def get_repository_path(self, file_path):
        """Determine the repository root path."""
        # Start from the file's directory and work up
        current_path = os.path.dirname(file_path)
        
        while current_path and current_path != os.path.dirname(current_path):
            # Check if this directory is already a Git repository
            git_dir = os.path.join(current_path, '.git')
            if os.path.exists(git_dir):
                return current_path
            
            # Move up one level
            current_path = os.path.dirname(current_path)
        
        # If no Git repository found, use the export directory
        return os.path.dirname(file_path)
    
    def ensure_git_repository(self, repo_path):
        """Ensure Git repository exists at the given path."""
        try:
            # Check if already a Git repository
            git_dir = os.path.join(repo_path, '.git')
            if os.path.exists(git_dir):
                print(f"[Integrate Version Control] Git repository found: {repo_path}")
                return True
            
            # Initialize new Git repository
            print(f"[Integrate Version Control] Initializing Git repository: {repo_path}")
            
            result = subprocess.run(
                ['git', 'init'],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("[Integrate Version Control] Git repository initialized successfully")
                
                # Create initial .gitignore if it doesn't exist
                self.create_gitignore(repo_path)
                
                return True
            else:
                print(f"[Integrate Version Control] Failed to initialize Git repository: {result.stderr}")
                return False
                
        except FileNotFoundError:
            print("[Integrate Version Control] Git not found - please install Git")
            return False
        except Exception as e:
            print(f"[Integrate Version Control] Error initializing Git repository: {e}")
            return False
    
    def create_gitignore(self, repo_path):
        """Create a basic .gitignore file for the repository."""
        gitignore_path = os.path.join(repo_path, '.gitignore')
        
        if os.path.exists(gitignore_path):
            return
        
        gitignore_content = """# Maya files
*.ma.swatches
*.mb.swatches
incrementalSave/
*.tmp

# OS files
.DS_Store
Thumbs.db

# Temporary files
*.log
*.bak
*~

# Large binary files (consider using Git LFS)
*.psd
*.ai
*.tiff
*.tga
*.exr
*.hdr
"""
        
        try:
            with open(gitignore_path, 'w') as f:
                f.write(gitignore_content)
            print(f"[Integrate Version Control] Created .gitignore: {gitignore_path}")
        except Exception as e:
            print(f"[Integrate Version Control] Failed to create .gitignore: {e}")
    
    def add_files_to_version_control(self, files, repo_path, instance):
        """Add files to Git version control."""
        try:
            # Add files to Git
            for file_path in files:
                # Get relative path from repository root
                rel_path = os.path.relpath(file_path, repo_path)
                
                print(f"[Integrate Version Control] Adding file: {rel_path}")
                
                result = subprocess.run(
                    ['git', 'add', rel_path],
                    cwd=repo_path,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    print(f"[Integrate Version Control] Warning: Failed to add {rel_path}: {result.stderr}")
            
            # Check if there are changes to commit
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            
            if not result.stdout.strip():
                print("[Integrate Version Control] No changes to commit")
                return True
            
            # Commit changes if auto-commit is enabled
            if VERSION_CONTROL.get("auto_commit", False):
                return self.commit_changes(repo_path, instance)
            else:
                print("[Integrate Version Control] Files staged for commit (auto-commit disabled)")
                return True
                
        except Exception as e:
            print(f"[Integrate Version Control] Error adding files to Git: {e}")
            return False
    
    def commit_changes(self, repo_path, instance):
        """Commit staged changes to Git."""
        try:
            # Generate commit message
            commit_message = self.generate_commit_message(instance)
            
            print(f"[Integrate Version Control] Committing changes: {commit_message}")
            
            result = subprocess.run(
                ['git', 'commit', '-m', commit_message],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("[Integrate Version Control] Changes committed successfully")
                
                # Get commit hash
                result = subprocess.run(
                    ['git', 'rev-parse', 'HEAD'],
                    cwd=repo_path,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    commit_hash = result.stdout.strip()
                    instance.data["commit_hash"] = commit_hash
                    print(f"[Integrate Version Control] Commit hash: {commit_hash}")
                
                return True
            else:
                print(f"[Integrate Version Control] Failed to commit changes: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"[Integrate Version Control] Error committing changes: {e}")
            return False
    
    def generate_commit_message(self, instance):
        """Generate commit message based on instance data."""
        template = VERSION_CONTROL.get("commit_message_template", "{asset_type}: {asset_name}")
        
        family = instance.data.get("family", "asset")
        asset_name = instance.data.get("asset", instance.name)
        
        # Get version if available
        version = "latest"
        for key in ["fbx_export_path", "obj_export_path", "alembic_export_path"]:
            if key in instance.data:
                path = instance.data[key]
                if path and "_v" in path:
                    # Extract version from filename
                    import re
                    match = re.search(r'_v(\d+)', path)
                    if match:
                        version = match.group(1)
                        break
        
        # Format commit message
        commit_message = template.format(
            asset_type=family,
            asset_name=asset_name,
            version=version
        )
        
        # Add timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_message += f" - {timestamp}"
        
        return commit_message
