import json
from pathlib import Path

def get_version() -> str:
    """Get the application version from package.json."""
    try:
        # Try to read package.json from the same directory as this file
        package_json_path = Path(__file__).parent / "package.json"
        if package_json_path.exists():
            with open(package_json_path, 'r') as f:
                data = json.load(f)
                return data.get("version", "unknown")
    except Exception:
        pass
    
    return "unknown"

__version__ = get_version()
