from typing import List, Dict, Any
from assistant.analysis.parsers import ParsedService

class DiffEngine:
    def compare_services(self, old_services: List[ParsedService], new_services: List[ParsedService]) -> Dict[str, Any]:
        """Compare two lists of services and return the differences."""
        old_map = {f"{s.port}/{s.protocol}": s for s in old_services}
        new_map = {f"{s.port}/{s.protocol}": s for s in new_services}
        
        added = []
        removed = []
        changed = []
        unchanged = []
        
        all_keys = set(old_map.keys()) | set(new_map.keys())
        
        for key in all_keys:
            if key not in old_map:
                added.append(new_map[key])
            elif key not in new_map:
                removed.append(old_map[key])
            else:
                if old_map[key].state != new_map[key].state or old_map[key].service_name != new_map[key].service_name:
                    changed.append({"old": old_map[key], "new": new_map[key]})
                else:
                    unchanged.append(new_map[key])
                    
        return {
            "added": added,
            "removed": removed,
            "changed": changed,
            "unchanged": unchanged
        }
