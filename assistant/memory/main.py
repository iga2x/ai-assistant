import sqlite3
import os
import json
import hashlib
import base64
import socket
import getpass
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from pathlib import Path
from assistant.utils.paths import MEMORY_DB_PATH
from .interface import IMemoryStore, IMemoryManager
from .metadata_manager import (
    MetadataManager,
    WorkspaceIsolation,
    DeduplicationManager,
    metadata_manager,
    workspace_isolation,
    deduplication_manager
)
from assistant.db.models import (
    SensitivityLevel,
    DataClassification,
    RetentionPolicy
)
from assistant.security.encryption_manager import encryption_manager

class EncryptedDB:
    def __init__(self, db_path: Path = MEMORY_DB_PATH):
        self.db_path = db_path
        self.encryption_manager = encryption_manager
        self._init_db()
        self.migrate_existing_data()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Entities table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                entity_type TEXT,
                encrypted_value TEXT,
                confidence REAL,
                created_at TIMESTAMP,
                last_used TIMESTAMP,
                success_count INTEGER DEFAULT 0,
                sensitivity TEXT,
                classification TEXT,
                retention_policy TEXT,
                source TEXT,
                workspace_project TEXT,
                command_tool_used TEXT,
                user_intent TEXT,
                tags TEXT,
                related_session_ids TEXT,
                data_hash TEXT,
                expires_at TIMESTAMP
            )
        ''')
        
        # User profile / facts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                key TEXT,
                encrypted_value TEXT,
                updated_at TIMESTAMP
            )
        ''')
        
        # Command history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS command_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command TEXT,
                timestamp TIMESTAMP
            )
        ''')

        # Indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_entities_last_used ON entities(last_used)')
        cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_facts_cat_key ON facts(category, key)')
        
        conn.commit()
        conn.close()

    def encrypt(self, value: str) -> str:
        """Encrypt value using new encryption manager."""
        if not value: return ""
        ciphertext, key_id = self.encryption_manager.encrypt(value)
        # Store both ciphertext and key_id for proper decryption
        return f"{key_id}:{ciphertext}"

    def decrypt(self, encrypted_value: str) -> str:
        """Decrypt value using new encryption manager."""
        if not encrypted_value: return ""
        try:
            # Split key_id and ciphertext
            parts = encrypted_value.split(":", 1)
            if len(parts) != 2:
                # Legacy format (old Fernet), try direct decryption
                return self._legacy_decrypt(encrypted_value)

            key_id, ciphertext = parts
            return self.encryption_manager.decrypt(ciphertext, key_id)
        except Exception:
            return "[DECRYPTION_FAILED]"

    def _legacy_decrypt(self, encrypted_value: str) -> str:
        """Decrypt legacy Fernet-encrypted values (migration)."""
        try:
            # Try legacy Fernet decryption
            from cryptography.fernet import Fernet
            # Try using old key derivation
            hostname = socket.gethostname()
            username = getpass.getuser()
            salt = b"ai-assistant-salt-v1"
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key_material = f"{hostname}:{username}".encode()
            key = base64.urlsafe_b64encode(kdf.derive(key_material))
            fernet = Fernet(key)
            return fernet.decrypt(encrypted_value.encode()).decode()
        except Exception:
            return "[DECRYPTION_FAILED]"

    def migrate_existing_data(self):
        """Migrate existing data to new schema if needed."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check if new columns exist
        cursor.execute("PRAGMA table_info(entities)")
        columns = [column[1] for column in cursor.fetchall()]

        # Add missing columns if needed
        new_columns = {
            'sensitivity': 'TEXT',
            'classification': 'TEXT',
            'retention_policy': 'TEXT',
            'source': 'TEXT',
            'workspace_project': 'TEXT',
            'command_tool_used': 'TEXT',
            'user_intent': 'TEXT',
            'tags': 'TEXT',
            'related_session_ids': 'TEXT',
            'data_hash': 'TEXT',
            'expires_at': 'TIMESTAMP'
        }

        for column, column_type in new_columns.items():
            if column not in columns:
                cursor.execute(f'ALTER TABLE entities ADD COLUMN {column} {column_type}')

                # Set default values for existing records
                if column == 'sensitivity':
                    cursor.execute("UPDATE entities SET sensitivity = 'internal' WHERE sensitivity IS NULL")
                elif column == 'classification':
                    cursor.execute("UPDATE entities SET classification = 'reusable_knowledge' WHERE classification IS NULL")
                elif column == 'retention_policy':
                    cursor.execute("UPDATE entities SET retention_policy = 'long_term' WHERE retention_policy IS NULL")
                elif column == 'source':
                    cursor.execute("UPDATE entities SET source = 'legacy' WHERE source IS NULL")
                elif column == 'workspace_project':
                    cursor.execute("UPDATE entities SET workspace_project = 'global' WHERE workspace_project IS NULL")

        conn.commit()
        conn.close()

    def execute(self, query: str, params: tuple = ()) -> List[Tuple]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchall()
        conn.commit()
        conn.close()
        return result

class EntityStore(IMemoryStore):
    """Unified entity store implementing IMemoryStore interface."""

    def __init__(self, db: EncryptedDB):
        self.db = db
        self.cache = {} # Simple LRU cache would be better, using dict for now

    def set(self, name: str, value: str, entity_type: str, confidence: float = 1.0, source: str = "unknown"):
        """Store entity with comprehensive metadata."""
        # Generate metadata using MetadataManager
        metadata = metadata_manager.generate_metadata(
            content=value,
            source=source,
            user_intent="entity_storage",
            confidence=confidence
        )

        # Check if should store based on classification rules
        if not metadata_manager.should_store(value, metadata):
            # Don't store, just cache temporarily
            self.cache[name] = value
            return

        # Summarize if needed
        stored_value = metadata_manager.summarize_for_storage(value, metadata["classification"])

        # Check for duplicates
        data_hash = metadata["data_hash"]
        existing_entity_id = deduplication_manager.check_duplicate(data_hash)
        if existing_entity_id:
            # Duplicate exists, just update last_used
            now = datetime.now(timezone.utc).isoformat()
            self.db.execute('UPDATE entities SET last_used = ? WHERE id = ?', (now, existing_entity_id))
            return

        encrypted_value = self.db.encrypt(stored_value)
        now = datetime.now(timezone.utc).isoformat()

        # Store with full metadata
        self.db.execute('''
            INSERT INTO entities (name, entity_type, encrypted_value, confidence, created_at, last_used,
                                sensitivity, classification, retention_policy, source, workspace_project,
                                command_tool_used, user_intent, tags, related_session_ids, data_hash, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                encrypted_value=excluded.encrypted_value,
                confidence=excluded.confidence,
                last_used=excluded.last_used,
                sensitivity=excluded.sensitivity,
                classification=excluded.classification,
                retention_policy=excluded.retention_policy
        ''', (
            name, entity_type, encrypted_value, confidence, now, now,
            metadata["sensitivity"].value if isinstance(metadata["sensitivity"], str) else metadata["sensitivity"].value,
            metadata["classification"].value if isinstance(metadata["classification"], str) else metadata["classification"].value,
            metadata["retention_policy"].value if isinstance(metadata["retention_policy"], str) else metadata["retention_policy"].value,
            metadata["source"], metadata["workspace_project"], metadata["command_tool_used"],
            metadata["user_intent"], json.dumps(metadata["tags"]), json.dumps(metadata["related_session_ids"]),
            metadata["data_hash"], metadata["expires_at"]
        ))

        self.cache[name] = value

    def update(self, key: str, value: str, confidence: float = 1.0):
        """Update method for compatibility with context/resolver.py."""
        # Determine entity type from key
        entity_type = key.split('_')[1] if '_' in key else "general"
        self.set(key, value, entity_type, confidence)

    def get(self, name: str) -> Optional[str]:
        """Retrieve entity with workspace isolation and retention checks."""
        if name in self.cache:
            return self.cache[name]

        result = self.db.execute('''
            SELECT encrypted_value, entity_type, sensitivity, classification, retention_policy,
                   workspace_project, expires_at, data_hash
            FROM entities WHERE name = ?
        ''', (name,))
        if not result:
            return None

        encrypted_value, entity_type, sensitivity, classification, retention_policy, workspace, expires_at, data_hash = result[0]

        # Check retention policy
        if expires_at:
            now = datetime.now(timezone.utc)
            if now > datetime.fromisoformat(expires_at):
                # Entity expired, delete it
                self.delete(name)
                return None

        # Check workspace isolation
        entity_data = {
            "workspace_project": workspace,
            "sensitivity": sensitivity
        }
        if not workspace_isolation.is_accessible_in_current_workspace(entity_data):
            return None

        value = self.db.decrypt(encrypted_value)

        # Validate before use (with safety check)
        if self._validate_safely(value, entity_type):
            self._mark_used(name, success=True)
            self.cache[name] = value
            return value
        else:
            self._mark_used(name, success=False)
            return None

    def _mark_used(self, name: str, success: bool = True):
        now = datetime.now(timezone.utc).isoformat()
        if success:
            self.db.execute('UPDATE entities SET last_used = ?, success_count = success_count + 1 WHERE name = ?', (now, name))
        else:
            self.db.execute('UPDATE entities SET last_used = ? WHERE name = ?', (now, name))

    def _validate_safely(self, value: str, entity_type: str) -> bool:
        """Safe validation without subprocess calls (will use SafetyGate in Phase 2)."""
        if entity_type == "ip":
            # Basic IP format validation only (no ping)
            import ipaddress
            try:
                ipaddress.ip_address(value)
                return True
            except ValueError:
                return False
        elif entity_type == "file_path":
            return os.path.exists(os.path.expanduser(value))
        elif entity_type == "url":
            # Basic URL format validation (no HEAD request)
            import re
            url_pattern = re.compile(
                r'^https?://'  # http:// or https://
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
                r'localhost|'  # localhost
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ip
                r'(?::\d+)?'  # optional port
                r'(?:/?|[/?]\S+)$', re.IGNORECASE)
            return url_pattern.match(value) is not None
        elif entity_type == "username":
            # Basic username validation (no subprocess check)
            return len(value) > 0 and value.isalnum()

        return True # Default to true for unknown types

    def delete(self, name: str):
        self.db.execute('DELETE FROM entities WHERE name = ?', (name,))
        if name in self.cache:
            del self.cache[name]

    def get_all(self) -> Dict[str, str]:
        results = self.list_all()
        return {r["name"]: r["value"] for r in results}

    def clear(self):
        self.db.execute('DELETE FROM entities')
        self.cache = {}

    def list_all(self, category: str = None) -> List[Dict]:
        query = 'SELECT name, entity_type, confidence, last_used, success_count, encrypted_value FROM entities'
        params = ()
        if category:
            query += ' WHERE entity_type = ?'
            params = (category,)

        rows = self.db.execute(query, params)
        results = []
        for row in rows:
            results.append({
                "name": row[0],
                "type": row[1],
                "confidence": row[2],
                "last_used": row[3],
                "success_count": row[4],
                "value": self.db.decrypt(row[5])
            })
        return results

class MemoryManager(IMemoryManager):
    """Unified memory manager implementing IMemoryManager interface."""

    def __init__(self):
        self.db = EncryptedDB()
        self.entities = EntityStore(self.db)
        self.session_state = {}
        self.suggested_memories = [] # Facts waiting for approval

    def auto_extract(self, text: str, source: str = "unknown"):
        """Extract entities from text using unified patterns with proper metadata."""
        import re

        # Determine source if not provided
        if source == "unknown":
            source = "terminal_output" if any(cmd in text for cmd in ['nmap', 'curl', 'ping', 'nslookup']) else "conversation"

        # 1. IP Addresses
        ips = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', text)
        for ip in set(ips):
            if ip != "127.0.0.1":
                self._suggest(ip, "ip", source)

        # 2. File Paths
        paths = re.findall(r'(/[a-zA-Z0-9\._/-]+|~/[a-zA-Z0-9\._/-]+)', text)
        for p in set(paths):
            if os.path.exists(os.path.expanduser(p)):
                self._suggest(p, "file_path", source)

        # 3. URLs
        urls = re.findall(r'https?://[a-zA-Z0-9\./_-]+', text)
        for url in set(urls):
            self._suggest(url, "url", source)

        # 4. Domains (unified pattern)
        domains = re.findall(r'\b([a-zA-Z0-9][a-zA-Z0-9\-\.]*[a-zA-Z0-9])\.(com|net|org|io|local|dev|test|app|cloud)\b', text)
        for domain_parts in set(domains):
            full_domain = f"{domain_parts[0]}.{domain_parts[1]}"
            self._suggest(full_domain, "domain", source)

        # 5. Explicit named entities: name = value
        named = re.findall(r'(\w+)\s*=\s*([a-zA-Z0-9\._/-]+)', text)
        for name, value in named:
            self.entities.set(name, value, "named_entity", source=source)

    def _suggest(self, value: str, entity_type: str, source: str = "unknown"):
        """Suggest entity for storage with proper metadata."""
        # Generate metadata for suggested entity
        metadata = metadata_manager.generate_metadata(
            content=value,
            source=source,
            user_intent="auto_detected",
            confidence=0.6  # Lower confidence for auto-detected entities
        )

        # Only suggest if not already in long-term memory
        existing = self.entities.list_all()
        if any(e['value'] == value for e in existing):
            return

        if value not in [s['value'] for s in self.suggested_memories]:
            # Add expiration for suggestions (24 hours)
            expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
            self.suggested_memories.append({
                "value": value,
                "type": entity_type,
                "metadata": metadata,
                "expires_at": expires_at
            })

    def cleanup(self):
        """Purge entities based on retention policies and metadata."""
        now = datetime.now(timezone.utc)

        # 1. Enforce expiration based on retention policies
        self.db.execute('DELETE FROM entities WHERE expires_at IS NOT NULL AND expires_at < ?', (now.isoformat(),))

        # 2. Delete low-confidence old entries (legacy cleanup)
        threshold_date = (now - timedelta(days=90)).isoformat()
        self.db.execute('''
            DELETE FROM entities
            WHERE (last_used < ? AND confidence < 0.8)
            OR (confidence < 0.4)
        ''', (threshold_date,))

        # 3. Limit total entities (keep most recent/used based on metadata)
        self.db.execute('''
            DELETE FROM entities WHERE id NOT IN (
                SELECT id FROM entities ORDER BY last_used DESC, success_count DESC LIMIT 200
            )
        ''')

        # 4. Cleanup expired suggestions
        self.suggested_memories = [
            mem for mem in self.suggested_memories
            if datetime.now(timezone.utc) < datetime.fromisoformat(mem.get('expires_at', datetime.now(timezone.utc).isoformat()))
        ]

        # Vacuum database
        self.db.execute('VACUUM')

    def get_all_facts(self) -> Dict[str, Dict[str, Any]]:
        """Retrieve all facts from the facts table, organized by category."""
        rows = self.db.execute('SELECT category, key, encrypted_value FROM facts')
        facts = {}
        for cat, key, enc_val in rows:
            if cat not in facts:
                facts[cat] = {}
            facts[cat][key] = self.db.decrypt(enc_val)
        return facts

    def set_secret(self, key: str, value: str):
        """Store a secret (like an API key) encrypted in the DB."""
        encrypted_value = self.db.encrypt(value)
        now = datetime.now(timezone.utc).isoformat()
        self.db.execute('''
            INSERT INTO facts (category, key, encrypted_value, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(category, key) DO UPDATE SET
                encrypted_value=excluded.encrypted_value,
                updated_at=excluded.updated_at
        ''', ("secrets", key, encrypted_value, now))

    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve and decrypt a secret from the DB."""
        rows = self.db.execute('SELECT encrypted_value FROM facts WHERE category = ? AND key = ?', ("secrets", key))
        if rows:
            return self.db.decrypt(rows[0][0])
        return None

    def export(self, export_path: Path):
        import shutil
        shutil.copy2(self.db.db_path, export_path)
        return f"Encrypted backup created at {export_path}"

def validate_memory_fact(func):
    """Decorator to validate named entities before tool execution."""
    import functools
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # Logic to intercept command and replace named entities with validated values
        # This is a simplified hook
        return func(self, *args, **kwargs)
    return wrapper
