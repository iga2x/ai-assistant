import re
from typing import Optional
from assistant.context.entities import EntityStore

class ContextResolver:
    def __init__(self, store: EntityStore):
        self.store = store

    def resolve(self, text: str) -> str:
        """Resolve pronouns like 'it', 'that', 'same', 'again', 'there'."""
        resolved = text.lower()
        
        target = self.store.get("last_target")
        ip = self.store.get("last_ip")
        domain = self.store.get("last_domain")
        
        # Mapping pronouns to their likely entities
        pronoun_map = {
            r'\bit\b': target,
            r'\bthat\b': target,
            r'\bsame\b': target,
            r'\bthere\b': target or ip or domain,
            r'\bagain\b': target,
        }

        for pattern, replacement in pronoun_map.items():
            if replacement:
                # Use regex to replace pronouns while preserving punctuation
                resolved = re.sub(pattern, replacement, resolved)

        return resolved

    def extract_entities(self, text: str):
        """Simple regex extraction for IP and Domains with confidence levels."""
        ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        domain_pattern = r'\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]\b'
        
        lower_text = text.lower()
        is_explicit = any(word in lower_text for word in ["target", "host", "domain", "ip", "scan", "analyze"])
        confidence = 0.9 if is_explicit else 0.6

        # Update last_ip
        ips = re.findall(ip_pattern, text)
        if ips:
            last_ip = ips[-1]
            self.store.update("last_ip", last_ip, confidence=confidence)
            self.store.update("last_target", last_ip, confidence=confidence)

        # Update last_domain
        domains = re.findall(domain_pattern, text)
        if domains:
            clean_domains = []
            for d in domains:
                if re.match(r'^[\d\.]+$', d):
                    continue
                clean_domains.append(d)
                
            if clean_domains:
                last_domain = clean_domains[-1]
                self.store.update("last_domain", last_domain, confidence=confidence)
                self.store.update("last_target", last_domain, confidence=confidence)
                
        # Update last_file
        file_match = re.search(r'\b[\w\.-]+\.(?:txt|md|py|sh|log|csv|json)\b', text)
        if file_match:
            self.store.update("last_file", file_match.group(0), confidence=0.8)
