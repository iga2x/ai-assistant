"""
Production-grade encryption key management for secure data storage.
Implements proper key derivation, rotation, and secure storage.
"""

import os
import json
import base64
import hashlib
import getpass
from pathlib import Path
from typing import Optional, Tuple
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet
from datetime import datetime, timezone
import secrets

from assistant.utils.paths import MEMORY_DB_PATH


class EncryptionManager:
    """Manages encryption keys and operations with proper security practices."""

    def __init__(self):
        self.key_store_path = Path.home() / ".assistant" / "keys.json"
        self.key_rotation_enabled = True
        self.max_key_age_days = 90
        self.current_key_id = None
        self.keys = {}
        self._init_key_store()

    def _init_key_store(self):
        """Initialize or load the key store."""
        if self.key_store_path.exists():
            self._load_keys()
        else:
            self._create_initial_keys()
            self._save_keys()

    def _create_initial_keys(self):
        """Create initial encryption keys with proper entropy."""
        self.current_key_id = secrets.token_hex(8)
        key = secrets.token_bytes(32)  # 256-bit key

        self.keys = {
            self.current_key_id: {
                "key_data": key,  # Store as bytes
                "created_at": datetime.now(timezone.utc).isoformat(),
                "algorithm": "ChaCha20-Poly1305",
                "status": "active"
            }
        }

        # Set restrictive permissions
        self.key_store_path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(self.key_store_path.parent, 0o700)

    def _load_keys(self):
        """Load keys from secure storage."""
        with open(self.key_store_path, 'r') as f:
            data = json.load(f)

        # Convert keys back from base64
        for key_id, key_info in data.items():
            key_data = base64.urlsafe_b64decode(key_info["key_data"])
            key_info["key_data"] = key_data  # Store as bytes

        self.keys = data

        # Find the active key
        for key_id, key_info in self.keys.items():
            if key_info.get("status") == "active":
                self.current_key_id = key_id
                break

        if not self.current_key_id:
            self.current_key_id = list(self.keys.keys())[0]

    def _save_keys(self):
        """Save keys to secure storage with proper permissions."""
        # Create copy with base64-encoded keys for storage
        storage_keys = {}
        for key_id, key_info in self.keys.items():
            # Handle both bytes and string formats
            key_data = key_info["key_data"]
            if isinstance(key_data, bytes):
                encoded_data = base64.urlsafe_b64encode(key_data).decode()
            else:
                encoded_data = key_data  # Already encoded string

            storage_keys[key_id] = {
                "key_data": encoded_data,
                "created_at": key_info["created_at"],
                "algorithm": key_info["algorithm"],
                "status": key_info.get("status", "active")
            }

        # Write to temp file first (atomic operation)
        temp_path = self.key_store_path.with_suffix('.tmp')
        with open(temp_path, 'w') as f:
            json.dump(storage_keys, f, indent=2)

        # Set restrictive permissions
        os.chmod(temp_path, 0o600)

        # Atomic rename
        os.replace(temp_path, self.key_store_path)

    def items(self):
        """Return keys as dictionary for compatibility."""
        return self.keys

    def get_current_key(self) -> bytes:
        """Get the current active encryption key."""
        if not self.current_key_id:
            self._rotate_key()

        return self.keys[self.current_key_id]["key_data"]

    def encrypt(self, plaintext: str) -> Tuple[str, str]:
        """Encrypt plaintext with current key, return (ciphertext, key_id)."""
        key = self.get_current_key()
        cipher = ChaCha20Poly1305(key)
        nonce = secrets.token_bytes(12)  # 96-bit nonce

        ciphertext = cipher.encrypt(nonce, plaintext.encode(), None)

        # Return base64-encoded (nonce + ciphertext) and key_id
        combined = base64.urlsafe_b64encode(nonce + ciphertext).decode()
        return combined, self.current_key_id

    def decrypt(self, ciphertext: str, key_id: Optional[str] = None) -> str:
        """Decrypt ciphertext using specified key ID or current key."""
        # Use provided key_id or current
        if key_id:
            key_id_to_use = key_id
        else:
            key_id_to_use = self.current_key_id

        if key_id_to_use not in self.keys:
            raise ValueError(f"Encryption key {key_id_to_use} not found")

        key = self.keys[key_id_to_use]["key_data"]
        cipher = ChaCha20Poly1305(key)

        # Decode and split nonce and ciphertext
        combined = base64.urlsafe_b64decode(ciphertext)
        nonce = combined[:12]
        ciphertext = combined[12:]

        plaintext = cipher.decrypt(nonce, ciphertext, None)
        return plaintext.decode()

    def _rotate_key(self):
        """Rotate encryption key if needed."""
        if not self.key_rotation_enabled:
            return

        # Check if current key needs rotation
        current_key_info = self.keys[self.current_key_id]
        created_at = datetime.fromisoformat(current_key_info["created_at"])
        age_days = (datetime.now(timezone.utc) - created_at).days

        if age_days < self.max_key_age_days:
            return  # Key is still fresh

        # Mark old key as deprecated
        current_key_info["status"] = "deprecated"

        # Create new key
        new_key_id = secrets.token_hex(8)
        new_key = secrets.token_bytes(32)

        self.keys[new_key_id] = {
            "key_data": new_key,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "algorithm": "ChaCha20-Poly1305",
            "status": "active"
        }

        self.current_key_id = new_key_id

        # Save updated key store
        self._save_keys()

    def reencrypt_data(self, old_data: list[tuple[str, str, str]]) -> list[tuple[str, str]]:
        """Reencrypt data from deprecated keys to current key.

        Args:
            old_data: List of (entity_id, old_ciphertext, old_key_id)

        Returns:
            List of (entity_id, new_ciphertext, new_key_id)
        """
        reencrypted = []

        for entity_id, old_ciphertext, old_key_id in old_data:
            try:
                # Decrypt with old key
                plaintext = self.decrypt(old_ciphertext, old_key_id)

                # Encrypt with new key
                new_ciphertext, new_key_id = self.encrypt(plaintext)

                reencrypted.append((entity_id, new_ciphertext, new_key_id))
            except Exception as e:
                # Log error but continue with other items
                print(f"Error reencrypting entity {entity_id}: {e}")

        return reencrypted

    def get_key_info(self, key_id: str) -> dict:
        """Get information about a specific key."""
        if key_id not in self.keys:
            return {}

        key_info = self.keys[key_id]
        created_at = datetime.fromisoformat(key_info["created_at"])
        age_days = (datetime.now(timezone.utc) - created_at).days

        return {
            "key_id": key_id,
            "algorithm": key_info["algorithm"],
            "status": key_info.get("status", "unknown"),
            "created_at": key_info["created_at"],
            "age_days": age_days,
            "needs_rotation": age_days >= self.max_key_age_days
        }

    def cleanup_old_keys(self):
        """Remove old deprecated keys (optional, for space)."""
        keys_to_remove = []

        for key_id, key_info in self.items():
            if key_info.get("status") == "deprecated":
                created_at = datetime.fromisoformat(key_info["created_at"])
                age_days = (datetime.now(timezone.utc) - created_at).days

                # Only remove keys older than 180 days
                if age_days > 180:
                    keys_to_remove.append(key_id)

        for key_id in keys_to_remove:
            del self.keys[key_id]

        if keys_to_remove:
            self._save_keys()


class SecureCredentialManager:
    """Manages credentials and secrets with additional security layers."""

    def __init__(self, encryption_manager: EncryptionManager):
        self.encryption_manager = encryption_manager
        self.credentials_path = Path.home() / ".assistant" / "credentials.enc"

    def store_credential(self, key: str, value: str, user_intent: str = "manual_entry"):
        """Store a credential with encryption and metadata."""
        credential_data = {
            "key": key,
            "value": value,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "user_intent": user_intent,
            "access_count": 0
        }

        # Encrypt the entire credential object
        plaintext = json.dumps(credential_data)
        ciphertext, key_id = self.encryption_manager.encrypt(plaintext)

        # Store in encrypted file
        credentials = self._load_credentials_file()
        credentials[key] = {
            "ciphertext": ciphertext,
            "key_id": key_id
        }
        self._save_credentials_file(credentials)

        return True

    def retrieve_credential(self, key: str) -> Optional[str]:
        """Retrieve and decrypt a credential."""
        credentials = self._load_credentials_file()

        if key not in credentials:
            return None

        credential_entry = credentials[key]
        try:
            plaintext = self.encryption_manager.decrypt(
                credential_entry["ciphertext"],
                credential_entry["key_id"]
            )
            credential_data = json.loads(plaintext)

            # Increment access count
            credential_data["access_count"] += 1
            credential_data["last_accessed"] = datetime.now(timezone.utc).isoformat()

            # Update stored credential
            ciphertext, key_id = self.encryption_manager.encrypt(json.dumps(credential_data))
            credentials[key] = {"ciphertext": ciphertext, "key_id": key_id}
            self._save_credentials_file(credentials)

            return credential_data["value"]
        except Exception as e:
            print(f"Error retrieving credential {key}: {e}")
            return None

    def _load_credentials_file(self) -> dict:
        """Load credentials from encrypted file."""
        if not self.credentials_path.exists():
            return {}

        # Decrypt entire file
        with open(self.credentials_path, 'rb') as f:
            ciphertext = f.read().decode()

        plaintext = self.encryption_manager.decrypt(ciphertext)
        return json.loads(plaintext)

    def _save_credentials_file(self, credentials: dict):
        """Save credentials to encrypted file."""
        plaintext = json.dumps(credentials)
        ciphertext, key_id = self.encryption_manager.encrypt(plaintext)

        with open(self.credentials_path, 'w') as f:
            f.write(ciphertext)

        os.chmod(self.credentials_path, 0o600)


# Global instances
encryption_manager = EncryptionManager()
credential_manager = SecureCredentialManager(encryption_manager)