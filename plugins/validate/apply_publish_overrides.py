# -*- coding: ascii -*-
"""
Apply Publish Overrides (ContextPlugin)

Purpose:
- Read persisted overrides and apply to instances before validation.
- Source: utils.publish_overrides (ASCII-only)

Order:
- Place at start of Validation (order=100) so all Validate/Extract/Integrate
  will respect the 'publish' state.
"""
import pyblish.api


class ApplyPublishOverrides(pyblish.api.ContextPlugin):
    label = "Apply Publish Overrides"
    order = 100
    hosts = ["maya"]

    def process(self, context):
        try:
            from utils import publish_overrides as po
        except Exception:
            print("[Apply Overrides] utils.publish_overrides not available")
            return

        mapping = po.load_overrides()
        if not mapping:
            print("[Apply Overrides] No overrides found")
            return

        changed = 0
        for inst in context:
            name = getattr(inst, "name", None) or inst.data.get("name") or ""
            if not name:
                continue
            if name in mapping:
                val = bool(mapping[name])
                prev = bool(inst.data.get("publish", True))
                inst.data["publish"] = val
                changed += int(val != prev)
                print("[Apply Overrides] {} -> publish={}".format(name, val))
        print("[Apply Overrides] Applied {} override(s)".format(changed))

