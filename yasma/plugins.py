import sys
from pathlib import Path
from typing import Dict

class PluginManager:
    def __init__(self, plugin_map: Dict[str, str]):
        self.plugins = plugin_map
        self.plugin_dir = Path("/app/plugins")

    def run_plugin(self, name: str, data: dict) -> str:
        if name not in self.plugins:
            return "fail: unknown plugin"

        plugin_def = self.plugins[name]          # PluginDef object
        script = plugin_def.script               # <-- extract the string
        file_path = self.plugin_dir / script

        if not file_path.exists():
            return f"fail: plugin file not found: {file_path}"

        print(f"[PluginManager] Loading plugin '{name}' from {file_path}", flush=True)
        print(f"[PluginManager] image_paths: {data.get('image_paths')}", flush=True)

        try:
            # Read and execute the plugin in a completely clean namespace
            with open(file_path) as f:
                code = compile(f.read(), str(file_path), 'exec')
            namespace = {}
            exec(code, namespace)
            result = namespace['post'](data)
            if result["status"] == "success":
                return "success"
            else:
                return f"fail: {result.get('reason', 'unknown')}"
        except Exception as e:
            print(f"[PluginManager] Exception: {e}", flush=True)
            return f"fail: {str(e)}"

