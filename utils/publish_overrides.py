# -*- coding: ascii -*-
"""
Utilities to persist per-instance publish overrides between UI and plugins.
ASCII-only for Maya 2022 compatibility.
"""
import os
import json

_DEF_DIRNAME = ".runtime"
_DEF_FILENAME = "publish_overrides.json"


def _repo_root():
    # utils/ is under repo root; go up one
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def overrides_path():
    root = _repo_root()
    d = os.path.join(root, _DEF_DIRNAME)
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        pass
    return os.path.join(d, _DEF_FILENAME)


def load_overrides():
    path = overrides_path()
    try:
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return {str(k): bool(v) for k, v in data.items()}
    except Exception:
        pass
    return {}


def save_overrides(mapping):
    path = overrides_path()
    try:
        with open(path, "w") as f:
            json.dump({str(k): bool(v) for k, v in mapping.items()}, f, indent=2, sort_keys=True)
        return True
    except Exception:
        return False


def set_override(name, value):
    data = load_overrides()
    data[str(name)] = bool(value)
    save_overrides(data)


def get_override(name, default=True):
    return load_overrides().get(str(name), bool(default))

