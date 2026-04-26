import importlib.util
import sys
import os
from pathlib import Path
from assistant.utils.paths import PLUGINS_DIR
from assistant.plugins.registry import plugin_registry

def load_plugins():
    """Dynamically load plugins from the plugins directory."""
    if not PLUGINS_DIR.exists():
        return

    # Add plugins dir to sys.path
    sys.path.append(str(PLUGINS_DIR))

    for item in PLUGINS_DIR.iterdir():
        if item.is_dir() and (item / "__init__.py").exists():
            # Load as package
            module_name = item.name
            try:
                module = importlib.import_module(module_name)
                if hasattr(module, "setup"):
                    module.setup(plugin_registry)
            except Exception as e:
                print(f"Error loading plugin {module_name}: {e}")
        elif item.suffix == ".py" and item.name != "__init__.py":
            # Load as module
            module_name = item.stem
            spec = importlib.util.spec_from_file_location(module_name, item)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if hasattr(module, "setup"):
                    module.setup(plugin_registry)

def create_example_plugin():
    """Create a sample plugin for demonstration."""
    example_path = PLUGINS_DIR / "hello_plugin.py"
    if example_path.exists():
        return

    content = """
from assistant.plugins.manager import BasePlugin

class HelloPlugin(BasePlugin):
    def initialize(self):
        print("Hello Plugin Initialized!")
    
    def get_commands(self):
        return [{"name": "hello", "help": "Say hello from a plugin"}]

def setup(registry):
    plugin = HelloPlugin()
    plugin.initialize()
    registry.register(plugin)
"""
    with open(example_path, "w") as f:
        f.write(content)
