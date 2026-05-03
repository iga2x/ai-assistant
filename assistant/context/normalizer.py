import re
from typing import Dict

class InputNormalizer:
    def __init__(self):
        # Common typos in commands or intent keywords
        self.typo_map = {
            r'\bscann\b': 'scan',
            r'\breconn\b': 'recon',
            r'\bstatuss\b': 'status',
            r'\bhelpp\b': 'help',
            r'\bwhiois\b': 'whois',
            r'\bdigg\b': 'dig',
            r'\bcurll\b': 'curl',
            r'\bpingg\b': 'ping',
            r'\bifconfigg\b': 'ifconfig',
            r'\bnmapp\b': 'nmap',
            r'\bwaht\b': 'what',
            r'\bfidn\b': 'find',
        }

    def normalize(self, text: str) -> str:
        """Clean up input, handle typos, and prepare for processing."""
        if not text:
            return ""

        # 1. Trim whitespace
        normalized = text.strip()

        # 2. Fix common typos using regex
        for pattern, replacement in self.typo_map.items():
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)

        # 3. Handle multiple spaces
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # 4. Redact sensitive patterns (Phase 2.8)
        sensitive_patterns = [
            r'(?:api_key|password|secret|token|key)\s*[:=]\s*["\']?([\w\-]{10,})["\']?',
            r'(?i)authorization:\s*bearer\s*([\w\.\-]{20,})'
        ]
        
        for pattern in sensitive_patterns:
            normalized = re.sub(pattern, lambda m: m.group(0).replace(m.group(1), "[REDACTED]"), normalized)

        return normalized
