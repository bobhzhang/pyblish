"""
Pyblish Web Integration Server

A simple Flask web application for managing and viewing Pyblish pipeline assets.
This serves as the integration endpoint for the production pipeline.
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import json
import datetime
from pathlib import Path

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'assets'
METADATA_FOLDER = 'metadata'
THUMBNAILS_FOLDER = 'thumbnails'

# Ensure directories exist
for folder in [UPLOAD_FOLDER, METADATA_FOLDER, THUMBNAILS_FOLDER]:
    os.makedirs(folder, exist_ok=True)

class AssetDatabase:
    """Simple file-based asset database."""
    
    def __init__(self):
        self.db_file = os.path.join(METADATA_FOLDER, 'assets.json')
        self.load_database()
    
    def load_database(self):
        """Load asset database from file."""
        if os.path.exists(self.db_file):
            with open(self.db_file, 'r') as f:
                self.assets = json.load(f)
        else:
            self.assets = {}
    
    def save_database(self):
        """Save asset database to file."""
        with open(self.db_file, 'w') as f:
            json.dump(self.assets, f, indent=2)
    
    def add_asset(self, asset_data):
        """Add or update an asset in the database."""
        asset_id = asset_data.get('asset_id')
        if not asset_id:
            asset_id = f"{asset_data.get('family', 'unknown')}_{asset_data.get('asset', 'unnamed')}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            asset_data['asset_id'] = asset_id
        
        asset_data['timestamp'] = datetime.datetime.now().isoformat()
        self.assets[asset_id] = asset_data
        self.save_database()
        return asset_id
    
    def get_asset(self, asset_id):
        """Get asset by ID."""
        return self.assets.get(asset_id)
    
    def get_all_assets(self):
        """Get all assets."""
        return self.assets
    
    def get_assets_by_family(self, family):
        """Get assets by family type."""
        return {k: v for k, v in self.assets.items() if v.get('family', '').lower() == family.lower()}

# Initialize database
db = AssetDatabase()

@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('index.html', assets=db.get_all_assets())

@app.route('/api/assets', methods=['GET'])
def get_assets():
    """API endpoint to get all assets."""
    family = request.args.get('family')
    if family:
        assets = db.get_assets_by_family(family)
    else:
        assets = db.get_all_assets()
    return jsonify(assets)

@app.route('/api/assets', methods=['POST'])
def create_asset():
    """API endpoint to create/update an asset."""
    try:
        asset_data = request.json
        asset_id = db.add_asset(asset_data)
        return jsonify({'success': True, 'asset_id': asset_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/assets/<asset_id>', methods=['GET'])
def get_asset(asset_id):
    """API endpoint to get a specific asset."""
    asset = db.get_asset(asset_id)
    if asset:
        return jsonify(asset)
    else:
        return jsonify({'error': 'Asset not found'}), 404

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """API endpoint to upload asset files."""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Get metadata
        asset_id = request.form.get('asset_id')
        family = request.form.get('family', 'unknown')
        
        # Create family folder
        family_folder = os.path.join(UPLOAD_FOLDER, family)
        os.makedirs(family_folder, exist_ok=True)
        
        # Save file
        filename = file.filename
        file_path = os.path.join(family_folder, filename)
        file.save(file_path)
        
        # Update asset metadata
        if asset_id:
            asset = db.get_asset(asset_id)
            if asset:
                if 'files' not in asset:
                    asset['files'] = []
                asset['files'].append({
                    'filename': filename,
                    'path': file_path,
                    'size': os.path.getsize(file_path),
                    'upload_time': datetime.datetime.now().isoformat()
                })
                db.add_asset(asset)
        
        return jsonify({
            'success': True, 
            'filename': filename,
            'path': file_path,
            'asset_id': asset_id
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/assets/<family>/<filename>')
def download_file(family, filename):
    """Download asset files."""
    return send_from_directory(os.path.join(UPLOAD_FOLDER, family), filename)

@app.route('/dashboard')
def dashboard():
    """Asset management dashboard."""
    return render_template('dashboard.html', assets=db.get_all_assets())

@app.route('/api/stats')
def get_stats():
    """Get pipeline statistics."""
    assets = db.get_all_assets()
    
    stats = {
        'total_assets': len(assets),
        'by_family': {},
        'recent_uploads': []
    }
    
    # Count by family
    for asset in assets.values():
        family = asset.get('family', 'Unknown')
        stats['by_family'][family] = stats['by_family'].get(family, 0) + 1
    
    # Get recent uploads (last 10)
    sorted_assets = sorted(assets.values(), key=lambda x: x.get('timestamp', ''), reverse=True)
    stats['recent_uploads'] = sorted_assets[:10]
    
    return jsonify(stats)

if __name__ == '__main__':
    print("="*60)
    print("PYBLISH WEB INTEGRATION SERVER")
    print("="*60)
    print("Starting Flask server...")
    print("Dashboard: http://localhost:5000")
    print("API Docs: http://localhost:5000/api/assets")
    print("="*60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
