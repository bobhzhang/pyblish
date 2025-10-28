# -*- coding: ascii -*-
"""
Maya userSetup.py for Pyblish Production Pipeline - Maya 2022 SIMPLE FIXED

This script automatically sets up the Pyblish environment when Maya starts.
Uses immediate execution to avoid deferred execution issues.
"""

# Startup detection and logging
print("="*60)
print("[Pyblish Setup] userSetup.py LOADING...")
print("[Pyblish Setup] Maya 2022 Pyblish Pipeline Initialization")
print("="*60)

import sys
import os

# Import Maya modules with error handling
try:
    import maya.cmds as cmds
    import maya.mel as mel
    print("[Pyblish Setup] Maya modules imported successfully")
    MAYA_AVAILABLE = True
except ImportError as e:
    print("[Pyblish Setup] Warning: Maya modules not available: " + str(e))
    MAYA_AVAILABLE = False

# Global variables for menu functions
PYBLISH_FUNCTIONS = {}

def get_pipeline_directory():
    """Get the pipeline directory path."""
    primary_path = "D:\\pyblish"

    if os.path.exists(primary_path) and os.path.exists(os.path.join(primary_path, 'plugins')):
        return primary_path

    print("[Pyblish Setup] ERROR: Pipeline directory not found: " + primary_path)
    return None

def setup_pyblish_environment():
    """Set up Pyblish environment and register plugins."""
    try:
        import pyblish.api
        print("[Pyblish Setup] Setting up environment...")

        pipeline_dir = get_pipeline_directory()
        if not pipeline_dir:
            return False

        print("[Pyblish Setup] Using pipeline directory: " + pipeline_dir)

        # Register plugin paths
        plugins_dir = os.path.join(pipeline_dir, 'plugins')
        if os.path.exists(plugins_dir):
            for subdir in ['collect', 'validate', 'extract', 'integrate']:
                plugin_path = os.path.join(plugins_dir, subdir)
                if os.path.exists(plugin_path):
                    pyblish.api.register_plugin_path(plugin_path)
                    print("[Pyblish Setup] Registered: " + plugin_path)

        # Add to Python path
        if pipeline_dir not in sys.path:
            sys.path.insert(0, pipeline_dir)

        # Register Maya as host
        pyblish.api.register_host("maya")
        print("[Pyblish Setup] Registered Maya as Pyblish host")

        # Default: disable post-collect popup selector (prefer in-Lite selection)
        import os as _os
        if _os.getenv("PYBLISH_NO_SELECTOR") is None:
            _os.environ["PYBLISH_NO_SELECTOR"] = "1"

        return True

    except ImportError as e:
        print("[Pyblish Setup] Failed to import pyblish.api: " + str(e))
        return False
    except Exception as e:
        print("[Pyblish Setup] Setup error: " + str(e))
        return False
def _find_pyblish_window():
    try:
        from PySide2 import QtWidgets
    except Exception:
        return None
    for w in QtWidgets.QApplication.topLevelWidgets():
        try:
            title = str(w.windowTitle())
        except Exception:
            title = ""
        if title.lower().startswith("pyblish"):
            return w
    return None


def show_pyblish_lite():
    """Show Pyblish Lite interface."""
    try:
        try:
            import pyblish_lite
        except ImportError:
            import pyblish.tools.lite as pyblish_lite

        window = pyblish_lite.show()
        print("[Pyblish] Opened Pyblish Lite interface")
        try:
            _auto_collect(window)  # auto press Reset/Collect to populate instances
            _orient_lite_to_instances(window)
            _show_lite_hint(window)
            _show_instance_selector_panel(window)  # side selector with checkboxes
        except Exception:
            pass
        return window

    except Exception as e:
        error_msg = "Failed to show Pyblish Lite: " + str(e)
        print("[Pyblish] " + error_msg)
        if MAYA_AVAILABLE:
            cmds.confirmDialog(
                title='Pyblish Lite Error',
                message=error_msg,
                button=['OK']
            )
        return None
def _auto_collect(window):
    """Auto press Reset/Collect in Lite to populate instances."""
    try:
        from PySide2 import QtWidgets, QtCore
    except Exception:
        return

    def _press():
        try:
            # Try to find a button with tooltip/text mentioning Collect or Reset
            for btn in window.findChildren(QtWidgets.QAbstractButton):
                txts = []
                for attr in ("toolTip", "text", "objectName"):
                    try:
                        v = getattr(btn, attr)()
                    except Exception:
                        v = getattr(btn, attr, "")
                    txts.append(str(v))
                txt = (" ".join(txts)).lower()
                if ("collect" in txt) or ("reset" in txt):
                    try:
                        btn.click()
                        return
                    except Exception:
                        pass
        except Exception:
            pass

    try:
        from PySide2 import QtCore  # noqa
        QtCore.QTimer.singleShot(250, _press)
    except Exception:
        _press()

    return
def _orient_lite_to_instances(window):
    """Try to switch Lite to Instances view and focus it.
    Uses heuristics to find a button or action containing 'Instance'.
    ASCII-only to be safe in Maya.
    """
    try:
        from PySide2 import QtWidgets, QtCore
    except Exception:
        return

    def _click_instances():
        try:
            # Try actions first
            for action in window.findChildren(QtWidgets.QAction):
                txt = (action.text() or "") + " " + (action.toolTip() or "") + " " + (action.objectName() or "")
                if "instance" in txt.lower():
                    action.trigger()
                    window.activateWindow()
                    return
            # Try buttons
            for btn in window.findChildren(QtWidgets.QAbstractButton):
                parts = []
                for attr in ("text", "toolTip", "objectName"):
                    try:
                        v = getattr(btn, attr)()
                    except Exception:
                        v = getattr(btn, attr, "")
                    parts.append(str(v))
                if "instance" in (" ".join(parts)).lower():
                    try:
                        btn.click()
                        window.activateWindow()
                        return
                    except Exception:
                        pass
        except Exception:
            pass

    # Defer a bit to allow widgets to build
    try:
        from PySide2 import QtCore  # noqa
        QtCore.QTimer.singleShot(200, _click_instances)
    except Exception:
        _click_instances()


def _show_lite_hint(window):
    """Show a small ASCII help panel near Lite window (left side)."""
    try:
        from PySide2 import QtWidgets, QtCore
    except Exception:
        return

    # Build panel
    w = QtWidgets.QWidget()
    w.setWindowTitle("Pyblish Tips")
    w.setWindowFlags(w.windowFlags() | QtCore.Qt.Tool)
    layout = QtWidgets.QVBoxLayout(w)

    text_lines = [
        "1) Click Reset/Collect (bottom-left)",
        "2) Ensure Instances tab (top-left 2nd icon)",
        "3) Uncheck to skip this instance",
        "4) Press Run (bottom-right)",
        "Icons: [Filter]=Filter, [Squares]=Instances, [Puzzle]=Plugins, [>_]=Log",
    ]
    for line in text_lines:
        layout.addWidget(QtWidgets.QLabel(line))

    btn_row = QtWidgets.QHBoxLayout()
    layout.addLayout(btn_row)

    btn_focus = QtWidgets.QPushButton("Go To Instances")
    btn_close = QtWidgets.QPushButton("Hide")
    btn_row.addWidget(btn_focus)
    btn_row.addWidget(btn_close)

    def _focus_instances():
        _orient_lite_to_instances(window)
    btn_focus.clicked.connect(_focus_instances)
    btn_close.clicked.connect(w.close)

    # Position near Lite (left side)
    try:
        g = window.frameGeometry()
        x = max(0, g.left() - 280)
        y = g.top()
        w.setGeometry(x, y, 260, 180)
    except Exception:
        w.resize(260, 180)

    w.show()
    try:
        w.raise_(); w.activateWindow()
    except Exception:
        pass

def _show_instance_selector_panel(window):
    """Dock-like panel near Lite listing instances with checkboxes.
    It persists overrides to utils.publish_overrides for plugins to consume.
    """
    try:
        from PySide2 import QtWidgets, QtCore
        from utils import publish_overrides as po
        import pyblish.api
    except Exception:
        return

    # Build panel
    panel = QtWidgets.QWidget()
    panel.setWindowTitle("Instance Select (ASCII)")
    panel.setWindowFlags(panel.windowFlags() | QtCore.Qt.Tool)
    v = QtWidgets.QVBoxLayout(panel)

    info = QtWidgets.QLabel("Refresh after Collect; uncheck to skip")
    v.addWidget(info)

    scroll = QtWidgets.QScrollArea()
    scroll.setWidgetResizable(True)
    v.addWidget(scroll, 1)
    inner = QtWidgets.QWidget()
    scroll.setWidget(inner)
    layout = QtWidgets.QVBoxLayout(inner)
    layout.setContentsMargins(6, 6, 6, 6)

    cbs = []

    def populate():
        # Discover instances by running collection (fast); names only
        for i in reversed(range(layout.count())):
            w = layout.itemAt(i).widget()
            if w is not None:
                w.setParent(None)
        cbs[:] = []
        try:
            # Run discovery only (collect); do not modify current Lite context
            import pyblish.logic as logic
            import pyblish.api as api
            context = api.Context()
            for plugin in api.collectors():
                try:
                    logic.process(context, plugin())
                except Exception:
                    pass
            names = [inst.name for inst in context]
        except Exception:
            names = []
        if not names:
            names = []
        saved = po.load_overrides()
        for name in sorted(set(names)):
            cb = QtWidgets.QCheckBox(name)
            cb.setChecked(bool(saved.get(name, True)))
            layout.addWidget(cb)
            cbs.append(cb)
        layout.addStretch(1)

    def apply_and_save():
        mapping = {}
        for cb in cbs:
            mapping[str(cb.text())] = bool(cb.isChecked())
        po.save_overrides(mapping)
        info.setText("Saved overrides ({})".format(len(mapping)))

    # Buttons
    row = QtWidgets.QHBoxLayout()
    v.addLayout(row)
    btn_refresh = QtWidgets.QPushButton("Refresh")
    btn_save = QtWidgets.QPushButton("Apply")
    row.addWidget(btn_refresh)
    row.addWidget(btn_save)
    btn_refresh.clicked.connect(populate)
    btn_save.clicked.connect(apply_and_save)

    # Position left to Lite
    try:
        g = window.frameGeometry()
        x = max(0, g.left() - 320)
        y = g.top()
        panel.setGeometry(x, y, 300, 360)
    except Exception:
        panel.resize(300, 360)

    panel.show()
    try:
        panel.raise_(); panel.activateWindow()
    except Exception:
        pass

    # First fill
    populate()

def review_instances_post_collect():
    """Open Pyblish Lite for manual review between Collection and Validation.
    Users can uncheck instances to skip, or right-click to manage.
    """
    try:
        show_pyblish_lite()
        if MAYA_AVAILABLE:
            cmds.inViewMessage(amg='Pyblish: After collection, uncheck instances to skip validation/extraction. Open Details to view metadata.',
                               pos='topCenter', fade=True)
    except Exception as e:
        print("[Pyblish] Review open failed: " + str(e))

def test_pyblish_pipeline():
    """Test the Pyblish pipeline."""
    try:
        import pyblish.api

        plugins = pyblish.api.discover()
        print("[Pyblish Test] Found " + str(len(plugins)) + " plugins")

        for plugin in plugins:
            order = getattr(plugin, 'order', 0)
            print("  - " + plugin.__name__ + " (order: " + str(order) + ")")

        if MAYA_AVAILABLE:
            cmds.confirmDialog(
                title='Pipeline Test',
                message='Found ' + str(len(plugins)) + ' plugins.\nCheck Script Editor for details.',
                button=['OK']
            )

    except Exception as e:
        print("[Pyblish Test] Pipeline test failed: " + str(e))

def create_pyblish_menu():
    """Create Pyblish menu."""
    if not MAYA_AVAILABLE:
        return False

    try:
        print("[Pyblish Setup] Creating Pyblish menu...")

        # Store functions globally
        global PYBLISH_FUNCTIONS
        PYBLISH_FUNCTIONS['show_pyblish_lite'] = show_pyblish_lite
        PYBLISH_FUNCTIONS['test_pyblish_pipeline'] = test_pyblish_pipeline
        PYBLISH_FUNCTIONS['review_instances_post_collect'] = review_instances_post_collect
        PYBLISH_FUNCTIONS['open_instance_selector_panel'] = lambda: _show_instance_selector_panel(_find_pyblish_window())

        # Delete existing menu
        if cmds.menu('PyblishMenu', exists=True):
            cmds.deleteUI('PyblishMenu', menu=True)

        # Get main window
        main_window = mel.eval('$temp = $gMainWindow')

        # Create menu
        main_menu = cmds.menu(
            'PyblishMenu',
            label='Pyblish',
            parent=main_window,
            tearOff=True
        )

        # Add menu items
        cmds.menuItem(
            label='Show Pyblish Lite',
            command='import __main__; __main__.PYBLISH_FUNCTIONS["show_pyblish_lite"]()',
            parent=main_menu
        )

        cmds.menuItem(
            label='Review Instances (Post-Collect)',
            command='import __main__; __main__.PYBLISH_FUNCTIONS["review_instances_post_collect"]()',
            parent=main_menu
        )

        cmds.menuItem(
            label='Instance Selector (Side Panel)',
            command='import __main__; __main__.PYBLISH_FUNCTIONS["open_instance_selector_panel"]()',
            parent=main_menu
        )

        cmds.menuItem(divider=True, parent=main_menu)

        cmds.menuItem(
            label='Test Pipeline',
            command='import __main__; __main__.PYBLISH_FUNCTIONS["test_pyblish_pipeline"]()',
            parent=main_menu
        )

        print("[Pyblish Setup] Pyblish menu created successfully")
        return True

    except Exception as e:
        print("[Pyblish Setup] Failed to create menu: " + str(e))
        return False

def main():
    """Main setup function."""
    print("\n[Pyblish Setup] Initializing Pyblish Production Pipeline...")

    try:
        if setup_pyblish_environment():
            print("[Pyblish Setup] Environment setup completed")

            if create_pyblish_menu():
                print("[Pyblish Setup] Menu creation completed")
                print("[Pyblish Setup] Look for 'Pyblish' menu in Maya's main menu bar")
            else:
                print("[Pyblish Setup] Menu creation failed")
        else:
            print("[Pyblish Setup] Environment setup failed")

    except Exception as e:
        print("[Pyblish Setup] Setup failed: " + str(e))
        import traceback
        traceback.print_exc()

    print("[Pyblish Setup] Initialization completed")
    print("="*60)

# Store functions in main module
import __main__
__main__.PYBLISH_FUNCTIONS = PYBLISH_FUNCTIONS

# Execute setup immediately to avoid deferred execution issues
print("[Pyblish Setup] Executing setup...")

if MAYA_AVAILABLE:
    # Use a simple timer-based delay instead of executeDeferred
    try:
        def delayed_main():
            main()

        # Try to delay execution slightly
        cmds.scriptJob(runOnce=True, event=['idle', delayed_main])
        print("[Pyblish Setup] Scheduled with scriptJob idle event")
    except:
        # Fallback to immediate execution
        print("[Pyblish Setup] Immediate execution fallback")
        main()
else:
    main()

print("[Pyblish Setup] userSetup.py loading completed")
