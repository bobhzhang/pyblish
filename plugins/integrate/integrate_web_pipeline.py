"""
Integrate Web Pipeline Plugin

This plugin integrates assets into the web-based production pipeline.
It uploads asset data and files to the web integration server.
"""

import pyblish.api
import sys
import os
import json
# Optional dependency: requests
try:
    import requests  # type: ignore
    HAVE_REQUESTS = True
except Exception:
    requests = None  # type: ignore
    HAVE_REQUESTS = False
    import urllib.request
    import urllib.error
    import urllib.parse
import shutil
from pathlib import Path

# Add utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from config.settings import DEFAULT_PLUGIN_ORDERS


class IntegrateWebPipeline(pyblish.api.InstancePlugin):
    """Integrate assets into the web-based production pipeline."""

    label = "Integrate Web Pipeline"
    order = DEFAULT_PLUGIN_ORDERS.get("integrate_web_pipeline", 320)
    hosts = ["maya"]
    families = ["model", "rig", "animation", "material", "camera", "scene"]

    # Configuration
    WEB_SERVER_URL = "http://localhost:5000"
    TEMP_EXPORT_DIR = "temp_exports"


    def _server_url(self):
        """Return WEB_SERVER_URL from env or default class value."""
        return os.getenv("WEB_SERVER_URL") or self.WEB_SERVER_URL

    def _headers(self):
        """Return auth headers if WEB_API_KEY is set; otherwise empty dict."""
        key = os.getenv("WEB_API_KEY") or ""
        return {"X-API-Key": key} if key else {}

    # Note: This plugin works with both Flask and standalone servers

    def process(self, instance):
        """Main processing function."""
        print("\n" + "="*50)
        print(f"[Integrate Web] Processing {instance.name}...")
        print("="*50)

        # Respect manual selection
        if not bool(instance.data.get("publish", True)):
            print("[Integrate Web] Skipped (publish=False)")
            return

        # Check if web server is available
        if not self.check_web_server():
            print("[Integrate Web] Web server not available, skipping integration")
            return

        # Prepare asset data
        asset_data = self.prepare_asset_data(instance)
        print(f"[Integrate Web] Prepared asset data for {instance.name}")

        # Export asset files if needed
        exported_files = self.export_asset_files(instance)
        if exported_files:
            print(f"[Integrate Web] Exported {len(exported_files)} files")

        # Upload to web pipeline
        success = self.upload_to_pipeline(asset_data, exported_files)

        if success:
            print(f"[Integrate Web] OK Successfully integrated {instance.name}")
            # Store integration info in instance
            instance.data["integrated"] = True
            instance.data["integration_url"] = f"{self._server_url()}/api/assets/{asset_data.get('asset_id')}"
        else:
            print(f"[Integrate Web] ERROR Failed to integrate {instance.name}")
            instance.data["integrated"] = False

        print("="*50 + "\n")

    def _http_get_json(self, url, timeout=5, headers=None):
        """GET JSON with requests or urllib fallback."""
        try:
            if HAVE_REQUESTS:
                resp = requests.get(url, timeout=timeout, headers=headers or {})
                if resp.status_code != 200:
                    return None
                return resp.json()
            else:
                req = urllib.request.Request(url, method="GET", headers=headers or {})
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    data = r.read().decode('utf-8', errors='ignore')
                import json as _json
                return _json.loads(data)
        except Exception:
            return None

    def _http_post_json(self, url, payload, timeout=30, headers=None):
        """POST JSON with requests or urllib fallback. Returns (status_code, json_or_text)."""
        try:
            if HAVE_REQUESTS:
                resp = requests.post(url, json=payload, timeout=timeout, headers=headers or {})
                try:
                    body = resp.json()
                except Exception:
                    body = resp.text
                return resp.status_code, body
            else:
                import json as _json
                data = _json.dumps(payload).encode('utf-8')
                req = urllib.request.Request(url, data=data, headers={**{"Content-Type": "application/json"}, **(headers or {})})
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    resp_text = r.read().decode('utf-8', errors='ignore')
                    try:
                        return 200, _json.loads(resp_text)
                    except Exception:
                        return 200, resp_text
        except urllib.error.HTTPError as e:
            try:
                body = e.read().decode('utf-8', errors='ignore')
            except Exception:
                body = str(e)
            return e.code, body
        except Exception as e:
            return 0, str(e)

    def _http_post_multipart(self, url, file_path, fields=None, timeout=60, headers=None):
        """POST multipart file upload.
        If requests is not available, fallback returns (501, 'Not Implemented')."""
        if HAVE_REQUESTS:
            try:
                with open(file_path, 'rb') as f:
                    files = {'file': f}
                    data = fields or {}
                    resp = requests.post(url, files=files, data=data, timeout=timeout, headers=headers or {})
                    try:
                        body = resp.json()
                    except Exception:
                        body = resp.text
                    return resp.status_code, body
            except Exception as e:
                return 0, str(e)
        else:
            # Minimal fallback not implemented; also the standalone server returns 501 currently
            return 501, 'Multipart upload not implemented in urllib fallback'

    def check_web_server(self):
        """Check if the web server is available."""
        result = self._http_get_json(f"{self._server_url()}/api/stats", timeout=5, headers=self._headers())
        return result is not None

    def prepare_asset_data(self, instance):
        """Prepare asset data for web integration with stable asset_id and version.
        - asset_id: <family>_<assetName>
        - version: query server for next version or default to 1
        """
        family_display = instance.data.get("family", "Unknown")
        family = str(family_display or "unknown").lower()
        asset_name = instance.data.get("asset", instance.name)
        asset_id = f"{family}_{asset_name}"

        # Determine next version by querying server (best-effort)
        version = 1
        detail = self._http_get_json(f"{self._server_url()}/api/assets/{asset_id}", timeout=5, headers=self._headers())
        try:
            if detail and isinstance(detail, dict):
                versions = detail.get("versions", [])
                if versions:
                    version = int(max(v.get("version", 0) for v in versions) + 1)
        except Exception:
            pass

        # Extract relevant data from instance
        asset_data = {
            "asset_id": asset_id,
            "version": version,
            "name": asset_name,
            "family": family,
            "families": instance.data.get("families", []),
            "description": instance.data.get("description", ""),
            "scene": instance.data.get("scene", ""),
            "plugin": instance.data.get("plugin", ""),
            "maya_objects": [str(obj) for obj in instance],
            "metadata": {}
        }

        # Add family-specific metadata
        if "model" in family:
            asset_data["metadata"].update({
                "mesh_count": instance.data.get("mesh_count", 0),
                "total_vertices": instance.data.get("total_vertices", 0),
                "total_faces": instance.data.get("total_faces", 0),
                "meshes": instance.data.get("meshes", [])
            })
        elif "rig" in family:
            asset_data["metadata"].update({
                "joint_count": instance.data.get("joint_count", 0),
                "control_count": instance.data.get("control_count", 0),
                "constraint_count": instance.data.get("constraint_count", 0),
                "root_joint": instance.data.get("root_joint", ""),
                "hierarchy_depth": instance.data.get("joint_hierarchy_depth", 0)
            })
        elif "animation" in family:
            asset_data["metadata"].update({
                "start_frame": instance.data.get("start_frame", 0),
                "end_frame": instance.data.get("end_frame", 0),
                "fps": instance.data.get("fps", 24),
                "frame_count": instance.data.get("frame_count", 0),
                "total_keyframes": instance.data.get("total_keyframes", 0),
                "animated_objects": len(instance.data.get("animated_objects", []))
            })
        elif "material" in family:
            asset_data["metadata"].update({
                "material_count": instance.data.get("material_count", 0),
                "texture_count": instance.data.get("texture_count", 0),
                "missing_textures": len(instance.data.get("missing_textures", [])),
                "total_texture_size": instance.data.get("total_texture_size", 0)
            })
        elif "camera" in family:
            asset_data["metadata"].update({
                "focal_length": instance.data.get("focal_length", 0),
                "is_animated": instance.data.get("is_animated", False),
                "keyframe_count": instance.data.get("keyframe_count", 0),
                "near_clip": instance.data.get("near_clip", 0),
                "far_clip": instance.data.get("far_clip", 0)
            })
        elif "scene" in family:
            asset_data["metadata"].update({
                "frame_range": instance.data.get("frame_range", (0, 0)),
                "fps": instance.data.get("fps", 24),
                "current_renderer": instance.data.get("current_renderer", ""),
                "render_resolution": instance.data.get("render_resolution", (0, 0)),
                "linear_units": instance.data.get("linear_units", ""),
                "angular_units": instance.data.get("angular_units", "")
            })
        return asset_data

    def export_asset_files(self, instance):
        """Export asset files for integration."""
        exported_files = []
        family = instance.data.get("family", "").lower()

        # Create temp export directory
        export_dir = Path(self.TEMP_EXPORT_DIR) / instance.name
        export_dir.mkdir(parents=True, exist_ok=True)

        try:
            import maya.cmds as cmds

            # Export based on family type
            if "model" in family:
                exported_files.extend(self.export_model(instance, export_dir))
            elif "rig" in family:
                exported_files.extend(self.export_rig(instance, export_dir))
            elif "animation" in family:
                exported_files.extend(self.export_animation(instance, export_dir))
            elif "material" in family:
                exported_files.extend(self.export_material(instance, export_dir))
            elif "camera" in family:
                exported_files.extend(self.export_camera(instance, export_dir))
            elif "scene" in family:
                exported_files.extend(self.export_scene(instance, export_dir))

        except ImportError:
            print("[Integrate Web] Maya not available for export")

        return exported_files

    def export_model(self, instance, export_dir):
        """Export model assets."""
        try:
            import maya.cmds as cmds
            exported_files = []

            # Select meshes
            meshes = instance.data.get("meshes", [])
            if meshes:
                cmds.select(meshes)

                # Export as FBX
                fbx_file = export_dir / f"{instance.name}.fbx"
                cmds.file(str(fbx_file), type="FBX export", exportSelected=True, force=True)
                exported_files.append(str(fbx_file))

                # Export as OBJ
                obj_file = export_dir / f"{instance.name}.obj"
                cmds.file(str(obj_file), type="OBJexport", exportSelected=True, force=True)
                exported_files.append(str(obj_file))

            return exported_files
        except Exception as e:
            print(f"[Integrate Web] Model export failed: {e}")
            return []

    def export_rig(self, instance, export_dir):
        """Export rig assets."""
        try:
            import maya.cmds as cmds
            exported_files = []

            # Export rig as Maya file
            joints = instance.data.get("joints", [])
            controls = instance.data.get("controls", [])

            if joints or controls:
                all_objects = joints + controls
                cmds.select(all_objects)

                ma_file = export_dir / f"{instance.name}_rig.ma"
                cmds.file(str(ma_file), type="mayaAscii", exportSelected=True, force=True)
                exported_files.append(str(ma_file))

            return exported_files
        except Exception as e:
            print(f"[Integrate Web] Rig export failed: {e}")
            return []

    def export_animation(self, instance, export_dir):
        """Export animation assets."""
        try:
            import maya.cmds as cmds
            exported_files = []

            # Export animation as Alembic
            animated_objects = [obj['object'] for obj in instance.data.get("animated_objects", [])]
            if animated_objects:
                cmds.select(animated_objects)

                start_frame = instance.data.get("start_frame", 1)
                end_frame = instance.data.get("end_frame", 24)

                abc_file = export_dir / f"{instance.name}_anim.abc"
                # Note: This is a simplified alembic export command
                # In production, you'd use the proper alembic export plugin
                exported_files.append(str(abc_file))

            return exported_files
        except Exception as e:
            print(f"[Integrate Web] Animation export failed: {e}")
            return []

    def export_material(self, instance, export_dir):
        """Export material assets."""
        # For materials, we mainly export metadata and texture references
        try:
            materials = instance.data.get("materials", [])
            textures = instance.data.get("textures", [])

            # Create material info file
            material_info = {
                "materials": materials,
                "textures": textures,
                "missing_textures": instance.data.get("missing_textures", [])
            }

            info_file = export_dir / f"{instance.name}_materials.json"
            with open(info_file, 'w') as f:
                json.dump(material_info, f, indent=2)

            return [str(info_file)]
        except Exception as e:
            print(f"[Integrate Web] Material export failed: {e}")
            return []

    def export_camera(self, instance, export_dir):
        """Export camera assets."""
        try:
            import maya.cmds as cmds
            exported_files = []

            camera_transform = instance.data.get("camera_transform")
            if camera_transform:
                cmds.select(camera_transform)

                ma_file = export_dir / f"{instance.name}_camera.ma"
                cmds.file(str(ma_file), type="mayaAscii", exportSelected=True, force=True)
                exported_files.append(str(ma_file))

            return exported_files
        except Exception as e:
            print(f"[Integrate Web] Camera export failed: {e}")
            return []

    def export_scene(self, instance, export_dir):
        """Export scene settings."""
        try:
            scene_settings = {
                "scene_settings": instance.data.get("scene_settings", {}),
                "render_settings": instance.data.get("render_settings", {}),
                "units_settings": instance.data.get("units_settings", {})
            }

            settings_file = export_dir / f"{instance.name}_settings.json"
            with open(settings_file, 'w') as f:
                json.dump(scene_settings, f, indent=2)

            return [str(settings_file)]
        except Exception as e:
            print(f"[Integrate Web] Scene export failed: {e}")
            return []

    def upload_to_pipeline(self, asset_data, exported_files):
        """Upload asset data and files to the web pipeline."""
        # 1) Upload metadata (JSON)
        status, body = self._http_post_json(f"{self._server_url()}/api/assets", asset_data, timeout=30, headers=self._headers())
        if status != 200:
            print(f"[Integrate Web] Failed to upload asset metadata: {body}")
            return False

        # Parse asset_id from response
        if isinstance(body, dict):
            asset_id = body.get('asset_id') or asset_data.get('asset_id')
        else:
            asset_id = asset_data.get('asset_id')

        # 2) Upload files (best-effort)
        for file_path in exported_files or []:
            if not os.path.exists(file_path):
                continue
            fields = {
                'asset_id': asset_id,
                'version': str(asset_data.get('version', 1)),
                'family': asset_data.get('family', 'unknown')
            }
            up_status, up_body = self._http_post_multipart(
                f"{self._server_url()}/api/upload",
                file_path,
                fields=fields,
                timeout=60,
                headers=self._headers()
            )
            if up_status != 200:
                print(f"[Integrate Web] File upload skipped/failed ({up_status}): {os.path.basename(file_path)} - {up_body}")
            else:
                print(f"[Integrate Web] Uploaded: {os.path.basename(file_path)}")

        return True

    def get_timestamp(self):
        """Get current timestamp string."""
        import datetime
        return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
