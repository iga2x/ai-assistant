from typing import Dict, Type
from assistant.plugins.manager import BasePlugin

class PluginRegistry:
    _instance = None
    _plugins: Dict[str, BasePlugin] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PluginRegistry, cls).__new__(cls)
        return cls._instance

    def register(self, plugin: BasePlugin):
        self._plugins[plugin.name] = plugin

    def get_plugin(self, name: str) -> BasePlugin:
        return self._plugins.get(name)

    def list_plugins(self) -> Dict[str, BasePlugin]:
        return self._plugins

plugin_registry = PluginRegistry()
