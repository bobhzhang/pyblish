# -*- coding: ascii -*-
"""
Post-Collect Instance Selector (ContextPlugin)

Purpose (ASCII only):
- After Collection, let user choose which MODEL instances to publish.
- Writes selection to instance.data['publish'] (default True).
- Persist selection per scene on disk so next runs remember your choice.
- Skip popup when PYBLISH_NO_SELECTOR=1 (automation) but still apply persisted choices.

Note:
- ASCII-only content for Maya 2022 compatibility.
- This plugin only toggles 'publish' flag, no data structure changes.

Order:
- Runs at the end of Collection (order=99), before Validation.
"""

import os
import json
from pathlib import Path
import pyblish.api


class PostCollectInstanceSelector(pyblish.api.ContextPlugin):
    label = "Post-Collect Instance Selector"
    order = 99  # end of collect range (see config)
    hosts = ["maya"]

    # -------------------------
    # Public entry
    # -------------------------
    def process(self, context):
        # Always initialize defaults
        self._ensure_default_publish(context)

        # Load persisted choices and apply before any UI
        persisted = self._load_persisted()
        self._apply_persisted(context, persisted)

        # Honor bypass: still keep persisted choices
        if os.getenv("PYBLISH_NO_SELECTOR", "0") in ("1", "true", "True"):
            print("[Selector] Bypassed by PYBLISH_NO_SELECTOR (persisted applied)")
            return

        # Try Maya UI
        try:
            import maya.cmds as cmds  # noqa
        except Exception:
            print("[Selector] Maya UI not available; only persisted choices applied")
            return

        instances = list(context)
        if not instances:
            print("[Selector] No instances found")
            return

        # Simple popup (ASCII text)
        window = "PostCollectInstanceSelectorWin"
        if cmds.window(window, exists=True):
            cmds.deleteUI(window)
        win = cmds.window(window, title="Instance Selector", sizeable=True, widthHeight=(420, 460))
        cmds.columnLayout(adjustableColumn=True)
        cmds.text(label="Select MODEL instances to publish (checked = run)")
        cmds.separator(h=6, style="in")

        cmds.scrollLayout(h=340)
        cmds.columnLayout(adjustableColumn=True)
        cbs = []
        model_instances = [i for i in instances if self._is_model_instance(i)]
        for inst in model_instances:
            cbs.append(cmds.checkBox(label=inst.name, value=bool(inst.data.get("publish", True))))
        if not cbs:
            cmds.text(label="No model instances found; nothing to select")
        cmds.setParent("..")
        cmds.setParent("..")

        cmds.separator(h=6, style="in")
        cmds.rowLayout(numberOfColumns=4, adjustableColumn=3)
        def _set_all(val):
            for cb in cbs:
                try:
                    cmds.checkBox(cb, e=True, value=val)
                except Exception:
                    pass
        cmds.button(label="All", w=60, c=lambda *_: _set_all(True))
        cmds.button(label="None", w=60, c=lambda *_: _set_all(False))
        status = cmds.text(label=" ")
        def _apply_and_close(*_):
            try:
                # Write selection back to instances
                for inst, cb in zip(model_instances, cbs):
                    inst.data["publish"] = bool(cmds.checkBox(cb, q=True, value=True))
                # Persist to disk
                self._save_persisted(context)
                cmds.deleteUI(win)
            except Exception:
                cmds.text(status, e=True, label="Apply failed")
        cmds.button(label="Apply & Continue", w=160, c=_apply_and_close)
        cmds.setParent("..")

        cmds.showWindow(win)

        # Wait for user
        while cmds.window(win, exists=True):
            try:
                cmds.pause(sec=0.1)
            except Exception:
                break

    # -------------------------
    # Helpers
    # -------------------------
    def _ensure_default_publish(self, context):
        for inst in context:
            if "publish" not in inst.data:
                inst.data["publish"] = True

    def _is_model_instance(self, instance):
        # Treat as model if families contains 'model' (collector sets it)
        fams = instance.data.get("families") or []
        return any(str(f).lower() == "model" for f in fams)

    def _store_path(self):
        # Env override or fall back to repo_root/cache
        env = os.getenv("PYBLISH_SELECTION_STORE")
        if env:
            p = Path(env)
        else:
            p = Path(__file__).resolve().parents[2] / "cache" / "pyblish_instance_selection.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def _scene_key(self):
        # Use absolute scene path if available, else 'untitled'
        try:
            import maya.cmds as cmds  # noqa
            path = cmds.file(q=True, sn=True) or "untitled"
        except Exception:
            path = "untitled"
        return str(Path(path).resolve()) if path and path != "untitled" else "untitled"

    def _load_persisted(self):
        try:
            p = self._store_path()
            if p.exists():
                with open(p, "r") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _apply_persisted(self, context, data):
        # Apply only for model instances
        key = self._scene_key()
        mapping = (data or {}).get(key, {})
        if not mapping:
            return
        applied = 0
        for inst in context:
            if self._is_model_instance(inst) and inst.name in mapping:
                inst.data["publish"] = bool(mapping[inst.name])
                applied += 1
        if applied:
            print(f"[Selector] Applied persisted selections to {applied} instance(s)")

    def _save_persisted(self, context):
        try:
            p = self._store_path()
            data = self._load_persisted()
            key = self._scene_key()
            data.setdefault(key, {})
            for inst in context:
                if self._is_model_instance(inst):
                    data[key][inst.name] = bool(inst.data.get("publish", True))
            with open(p, "w") as f:
                json.dump(data, f, indent=2)
            print(f"[Selector] Persisted selections to {p}")
        except Exception as e:
            print(f"[Selector] Warning: could not persist selections: {e}")

