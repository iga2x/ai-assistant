import re
import os
from typing import Optional, Any

class ContextResolver:
    def __init__(self, store: Any):
        self.store = store

    def resolve(self, text: str) -> str:
        """Resolve pronouns like 'it', 'that', 'same', 'again', 'there', 'my machine'."""
        # DO NOT lowercase the whole string; Linux paths are case-sensitive.
        resolved = text

        # Try to resolve common targets
        target = self.store.get("last_target")
        ip = self.store.get("last_ip")
        domain = self.store.get("last_domain")

        # Build a set of replacement values to check for cascading replacements
        replacement_values = {v for v in [target, ip, domain, "localhost"] if v}

        # Mapping pronouns and phrases to their likely entities
        # ORDER MATTERS: Most specific patterns first to avoid double replacement
        pronoun_map = [
            (r'\b(?:the|that) same\b', f'{target} {target}'),  # "that same" -> "target.com target.com"
            (r'\bthe previous result\b', target),
            (r'\bmy ip\b', ip),
            (r'\bthat ip\b', ip or target),
            (r'\bthis host\b', target or ip or domain or "localhost"),
            (r'\bmy machine\b', "localhost"),
            (r'\bmy computer\b', "localhost"),
            (r'\bthere\b', target or ip or domain),
            (r'\bit\b', target),
            (r'\bthat\b', target),  # Less specific, after "that ip"
            (r'\bsame\b', target),  # Least specific, last
            (r'\bagain\b', target),
        ]

        for pattern, replacement in pronoun_map:
            if replacement:
                # Use regex to replace pronouns while preserving punctuation
                # Use count=1 to replace only first occurrence per pattern
                # Use IGNORECASE to match "It" or "IT" or "it" without destroying the rest of the string case
                resolved = re.sub(pattern, replacement, resolved, count=1, flags=re.IGNORECASE)

        return resolved

    def extract_entities(self, text: str):
        """Extract and store entities from text (IPs, domains, file paths)."""
        import ipaddress

        # 1. IP Addresses
        ips = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', text)
        for ip in set(ips):
            if ip != "127.0.0.1":
                try:
                    # Validate it's a real IP
                    ipaddress.ip_address(ip)
                    # Use update method which already exists in EntityStore
                    self.store.update("last_ip", ip)
                    self.store.update("last_target", ip)
                except ValueError:
                    pass # Skip invalid IPs

        # 2. Domains/hostnames
        # Simple pattern: word.word or word with common TLD
        domains = re.findall(r'\b([a-zA-Z0-9][a-zA-Z0-9\-\.]*[a-zA-Z0-9])\.(com|net|org|io|local|dev|test|app|cloud)\b', text)
        for domain in set(domains):
            # Reconstruct full domain
            full_domain = f"{domain[0]}.{domain[1]}"
            self.store.update("last_domain", full_domain)
            self.store.update("last_target", full_domain)

        # 3. File paths
        paths = re.findall(r'(/[a-zA-Z0-9\._/-]+|~/[a-zA-Z0-9\._/-]+|[a-zA-Z0-9_\-\.]+\.[a-zA-Z]{2,4})', text)
        for p in set(paths):
            self.store.update("last_file", p)
