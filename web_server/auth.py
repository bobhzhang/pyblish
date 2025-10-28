"""
Very small API key based auth + roles.
- Configure keys via environment or local json file web_server/api_keys.json
- Header: X-API-Key
Roles: viewer, editor, admin
"""
from __future__ import annotations
import os
import json
from functools import wraps
from typing import Dict
from flask import request, jsonify

DEFAULT_KEYS = {
    "demo-view": "viewer",
    "demo-edit": "editor",
    "demo-admin": "admin",
}

KEY_FILE = os.path.join(os.path.dirname(__file__), "api_keys.json")


def load_keys() -> Dict[str, str]:
    if os.path.exists(KEY_FILE):
        try:
            with open(KEY_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return {str(k): str(v) for k, v in data.items()}
        except Exception:
            pass
    return DEFAULT_KEYS.copy()


def require_role(min_role: str = "viewer"):
    role_rank = {"viewer": 1, "editor": 2, "admin": 3}

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            api_key = request.headers.get("X-API-Key", "")
            keys = load_keys()
            role = keys.get(api_key)
            if not role:
                return jsonify({"error": "Unauthorized"}), 401
            if role_rank.get(role, 0) < role_rank.get(min_role, 1):
                return jsonify({"error": "Forbidden"}), 403
            # attach role for downstream if needed
            request.user_role = role  # type: ignore
            return func(*args, **kwargs)
        return wrapper
    return decorator

