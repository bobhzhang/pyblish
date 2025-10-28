"""
File Utility Functions

This module contains utility functions for file operations in the Pyblish pipeline.
"""

import os
import re
import shutil
import json
from datetime import datetime


def ensure_directory(directory_path):
    """Ensure a directory exists, create if it doesn't."""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
        print(f"Created directory: {directory_path}")
    return directory_path


def get_next_version(file_path):
    """Get the next version number for a file."""
    directory = os.path.dirname(file_path)
    filename = os.path.basename(file_path)
    name, ext = os.path.splitext(filename)
    
    # Extract version pattern (e.g., _v001)
    version_pattern = r'_v(\d{3})$'
    match = re.search(version_pattern, name)
    
    if match:
        current_version = int(match.group(1))
        base_name = name[:match.start()]
    else:
        current_version = 0
        base_name = name
    
    # Find existing versions
    existing_versions = []
    if os.path.exists(directory):
        for existing_file in os.listdir(directory):
            existing_name, existing_ext = os.path.splitext(existing_file)
            if existing_ext == ext and existing_name.startswith(base_name):
                version_match = re.search(version_pattern, existing_name)
                if version_match:
                    existing_versions.append(int(version_match.group(1)))
    
    # Get next version
    if existing_versions:
        next_version = max(existing_versions) + 1
    else:
        next_version = current_version + 1
    
    # Construct new filename
    new_name = f"{base_name}_v{next_version:03d}{ext}"
    return os.path.join(directory, new_name)


def backup_file(file_path, backup_dir=None):
    """Create a backup of a file."""
    if not os.path.exists(file_path):
        return None
    
    if backup_dir is None:
        backup_dir = os.path.join(os.path.dirname(file_path), "backup")
    
    ensure_directory(backup_dir)
    
    filename = os.path.basename(file_path)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name, ext = os.path.splitext(filename)
    backup_filename = f"{name}_{timestamp}{ext}"
    backup_path = os.path.join(backup_dir, backup_filename)
    
    shutil.copy2(file_path, backup_path)
    print(f"Backed up file: {backup_path}")
    return backup_path


def clean_filename(filename):
    """Clean a filename to remove invalid characters."""
    # Remove invalid characters
    invalid_chars = r'[<>:"/\\|?*]'
    clean_name = re.sub(invalid_chars, '_', filename)
    
    # Remove multiple underscores
    clean_name = re.sub(r'_+', '_', clean_name)
    
    # Remove leading/trailing underscores and dots
    clean_name = clean_name.strip('_.')
    
    return clean_name


def get_file_size(file_path):
    """Get file size in bytes."""
    if os.path.exists(file_path):
        return os.path.getsize(file_path)
    return 0


def get_file_size_mb(file_path):
    """Get file size in megabytes."""
    size_bytes = get_file_size(file_path)
    return size_bytes / (1024 * 1024)


def copy_with_metadata(source, destination):
    """Copy file with metadata preservation."""
    ensure_directory(os.path.dirname(destination))
    shutil.copy2(source, destination)
    print(f"Copied: {source} -> {destination}")
    return destination


def move_with_backup(source, destination):
    """Move file with backup of destination if it exists."""
    if os.path.exists(destination):
        backup_file(destination)
    
    ensure_directory(os.path.dirname(destination))
    shutil.move(source, destination)
    print(f"Moved: {source} -> {destination}")
    return destination


def find_files_by_pattern(directory, pattern):
    """Find files matching a pattern in a directory."""
    matching_files = []
    if os.path.exists(directory):
        for root, dirs, files in os.walk(directory):
            for file in files:
                if re.match(pattern, file):
                    matching_files.append(os.path.join(root, file))
    return matching_files


def find_files_by_extension(directory, extensions):
    """Find files with specific extensions in a directory."""
    if isinstance(extensions, str):
        extensions = [extensions]
    
    matching_files = []
    if os.path.exists(directory):
        for root, dirs, files in os.walk(directory):
            for file in files:
                _, ext = os.path.splitext(file)
                if ext.lower() in [e.lower() for e in extensions]:
                    matching_files.append(os.path.join(root, file))
    return matching_files


def get_relative_path(file_path, base_path):
    """Get relative path from base path."""
    try:
        return os.path.relpath(file_path, base_path)
    except ValueError:
        return file_path


def normalize_path(path):
    """Normalize path separators for cross-platform compatibility."""
    return os.path.normpath(path).replace('\\', '/')


def create_directory_structure(base_path, structure):
    """Create directory structure from a dictionary."""
    for name, subdirs in structure.items():
        dir_path = os.path.join(base_path, name)
        ensure_directory(dir_path)
        
        if isinstance(subdirs, dict):
            create_directory_structure(dir_path, subdirs)
        elif isinstance(subdirs, list):
            for subdir in subdirs:
                ensure_directory(os.path.join(dir_path, subdir))


def save_json(data, file_path):
    """Save data to JSON file."""
    ensure_directory(os.path.dirname(file_path))
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)
    print(f"Saved JSON: {file_path}")


def load_json(file_path):
    """Load data from JSON file."""
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    return None


def get_disk_usage(path):
    """Get disk usage statistics for a path."""
    if os.path.exists(path):
        total, used, free = shutil.disk_usage(path)
        return {
            'total': total,
            'used': used,
            'free': free,
            'total_gb': total / (1024**3),
            'used_gb': used / (1024**3),
            'free_gb': free / (1024**3),
        }
    return None


def validate_file_path(file_path):
    """Validate if a file path is valid and accessible."""
    try:
        # Check if path is valid
        os.path.normpath(file_path)
        
        # Check if directory exists or can be created
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            try:
                os.makedirs(directory)
            except OSError:
                return False, "Cannot create directory"
        
        # Check if file can be written (if it doesn't exist)
        if not os.path.exists(file_path):
            try:
                with open(file_path, 'w') as f:
                    pass
                os.remove(file_path)
            except OSError:
                return False, "Cannot write to location"
        
        return True, "Valid path"
        
    except Exception as e:
        return False, str(e)
