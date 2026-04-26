import re
from typing import Dict, Optional, Any
from assistant.db.database import DatabaseManager

class ContextManager:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.entities = {
            "last_ip": None,
            "last_domain": None,
            "last_file": None,
            "last_target": None
        }

    def update_context(self, text: str, output: str = ""):
        """Extract and update entities from user text or tool output."""
        # Regex for common entities
        ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        domain_pattern = r'\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]\b'
        
        # Check user text
        ips = re.findall(ip_pattern, text)
        if ips:
            self.entities["last_ip"] = ips[-1]
            self.entities["last_target"] = ips[-1]
            self.db.update_entity("last_ip", ips[-1])
            self.db.update_entity("last_target", ips[-1])

        domains = re.findall(domain_pattern, text)
        if domains:
            # Filter out common false positives like "127.0.0.1" which matches domain regex too
            clean_domains = [d for d in domains if not re.match(ip_pattern, d)]
            if clean_domains:
                self.entities["last_domain"] = clean_domains[-1]
                self.entities["last_target"] = clean_domains[-1]
                self.db.update_entity("last_domain", clean_domains[-1])
                self.db.update_entity("last_target", clean_domains[-1])

    def resolve_pronouns(self, text: str) -> str:
        """Replace 'it', 'that', 'same' with the last known target."""
        pronouns = [" it ", " that ", " same "]
        target = self.db.get_entity("last_target")
        
        if not target:
            return text
            
        resolved_text = text
        for p in pronouns:
            if p in f" {resolved_text} ":
                # Replace with target
                resolved_text = resolved_text.replace(p.strip(), target.value)
        
        return resolved_text

    def get_context_summary(self) -> Dict[str, str]:
        entities = self.db.get_all_entities()
        return {e.key: e.value for e in entities}
