"""
Secure knowledge base with encryption, access controls, and audit trails.
Replaces plaintext knowledge base with encrypted storage.
"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from assistant.security.encryption_manager import encryption_manager
from assistant.memory.metadata_manager import metadata_manager
from assistant.utils.logger import get_logger

logger = get_logger(__name__)


class SecureKnowledgeManager:
    """Manages secure knowledge base with encryption and access controls."""

    def __init__(self):
        self.knowledge_root = Path.home() / ".assistant" / "knowledge_secure"
        self.knowledge_root.mkdir(parents=True, exist_ok=True)
        os.chmod(self.knowledge_root, 0o700)  # Restrictive permissions

        # Metadata database for tracking
        self.metadata_db = self.knowledge_root / "metadata.json"
        self._init_metadata()

        # Access control matrix
        self.access_matrix = self._load_access_matrix()

    def _init_metadata(self):
        """Initialize metadata database."""
        if not self.metadata_db.exists():
            with open(self.metadata_db, 'w') as f:
                json.dump({}, f, indent=2)

    def _load_access_matrix(self) -> Dict[str, Any]:
        """Load access control matrix."""
        access_file = self.knowledge_root / "access_matrix.json"
        if not access_file.exists():
            # Create default access matrix
            default_matrix = {
                "public": ["everyone"],
                "internal": ["workspace_members"],
                "private": ["owner_only"],
                "secret_critical": ["explicit_authorization"]
            }
            with open(access_file, 'w') as f:
                json.dump(default_matrix, f, indent=2)
            return default_matrix

        with open(access_file, 'r') as f:
            return json.load(f)

    def _save_access_matrix(self):
        """Save access control matrix."""
        access_file = self.knowledge_root / "access_matrix.json"
        with open(access_file, 'w') as f:
            json.dump(self.access_matrix, f, indent=2)

    def add_document(self, filename: str, content: str, source: str = "manual_entry") -> Dict[str, Any]:
        """Add document with encryption and metadata."""
        try:
            # Validate input
            if not filename or not content:
                raise ValueError("Filename and content are required")

            # Generate comprehensive metadata
            doc_metadata = metadata_manager.generate_metadata(
                content=content,
                source=source,
                user_intent="knowledge_storage",
                confidence=1.0
            )

            # Calculate file path
            safe_filename = self._sanitize_filename(filename)
            doc_path = self.knowledge_root / f"{safe_filename}.enc"

            # Check access permissions
            if not self._has_access_permission(doc_metadata["sensitivity"]):
                raise PermissionError(f"No permission to store {doc_metadata['sensitivity'].value} data")

            # Encrypt content
            ciphertext, key_id = encryption_manager.encrypt(content)

            # Store encrypted document
            with open(doc_path, 'w') as f:
                f.write(ciphertext)

            # Update metadata
            metadata = self._load_metadata()
            metadata[safe_filename] = {
                "original_filename": filename,
                "encrypted_path": str(doc_path),
                "key_id": key_id,
                "metadata": {
                    "sensitivity": doc_metadata["sensitivity"].value,
                    "classification": doc_metadata["classification"].value,
                    "retention_policy": doc_metadata["retention_policy"].value,
                    "source": doc_metadata["source"],
                    "workspace_project": doc_metadata["workspace_project"],
                    "command_tool_used": doc_metadata["command_tool_used"],
                    "user_intent": doc_metadata["user_intent"],
                    "tags": doc_metadata["tags"],
                    "data_hash": doc_metadata["data_hash"],
                    "expires_at": str(doc_metadata["expires_at"]) if doc_metadata["expires_at"] else None
                },
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_accessed": None,
                "access_count": 0
            }
            self._save_metadata(metadata)

            logger.info(f"Secure document added: {filename} (sensitivity: {doc_metadata['sensitivity'].value})")

            return {
                "success": True,
                "filename": safe_filename,
                "sensitivity": doc_metadata["sensitivity"].value,
                "metadata": metadata[safe_filename]
            }

        except Exception as e:
            logger.error(f"Failed to add document {filename}: {e}")
            return {"success": False, "error": str(e)}

    def get_document(self, filename: str) -> Optional[Dict[str, Any]]:
        """Retrieve and decrypt document with access control check."""
        try:
            metadata = self._load_metadata()
            safe_filename = self._sanitize_filename(filename)

            if safe_filename not in metadata:
                return None

            doc_info = metadata[safe_filename]

            # Check access permissions
            sensitivity = doc_info["metadata"]["sensitivity"]
            if not self._has_access_permission(sensitivity):
                logger.warning(f"Access denied for {filename} (sensitivity: {sensitivity})")
                return None

            # Read encrypted document
            doc_path = Path(doc_info["encrypted_path"])
            if not doc_path.exists():
                return None

            with open(doc_path, 'r') as f:
                ciphertext = f.read()

            # Decrypt content
            key_id = doc_info["key_id"]
            content = encryption_manager.decrypt(ciphertext, key_id)

            # Update access tracking
            doc_info["last_accessed"] = datetime.now(timezone.utc).isoformat()
            doc_info["access_count"] += 1
            self._save_metadata(metadata)

            return {
                "filename": filename,
                "content": content,
                "metadata": doc_info["metadata"]
            }

        except Exception as e:
            logger.error(f"Failed to retrieve document {filename}: {e}")
            return None

    def search(self, query: str, sensitivity_filter: Optional[str] = None) -> List[Dict[str, str]]:
        """Search encrypted knowledge base with access control filtering."""
        results = []
        metadata = self._load_metadata()

        query_words = set(query.lower().split())

        for safe_filename, doc_info in metadata.items():
            # Apply sensitivity filter
            sensitivity = doc_info["metadata"]["sensitivity"]
            if sensitivity_filter and sensitivity != sensitivity_filter:
                continue

            # Check access permissions
            if not self._has_access_permission(sensitivity):
                continue

            # Search in metadata (can't search encrypted content efficiently)
            searchable_text = f"{doc_info['original_filename']} {' '.join(doc_info['metadata'].get('tags', []))}"

            score = 0
            for word in query_words:
                if word in searchable_text.lower():
                    score += 1

            if score > 0:
                results.append({
                    "filename": doc_info["original_filename"],
                    "safe_filename": safe_filename,
                    "sensitivity": sensitivity,
                    "score": score,
                    "tags": doc_info["metadata"].get("tags", []),
                    "created_at": doc_info["created_at"]
                })

        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:10]  # Limit to 10 results

    def delete_document(self, filename: str) -> bool:
        """Delete document with proper cleanup."""
        try:
            metadata = self._load_metadata()
            safe_filename = self._sanitize_filename(filename)

            if safe_filename not in metadata:
                return False

            doc_info = metadata[safe_filename]

            # Delete encrypted file
            doc_path = Path(doc_info["encrypted_path"])
            if doc_path.exists():
                doc_path.unlink()

            # Remove metadata entry
            del metadata[safe_filename]
            self._save_metadata(metadata)

            logger.info(f"Secure document deleted: {filename}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete document {filename}: {e}")
            return False

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for secure storage."""
        # Remove path components and special characters
        safe = Path(filename).name
        safe = "".join(c for c in safe if c.isalnum() or c in '._-')
        # Add hash for uniqueness
        safe_hash = hashlib.md5(filename.encode()).hexdigest()[:8]
        return f"{safe}_{safe_hash}"

    def _load_metadata(self) -> Dict[str, Any]:
        """Load metadata database."""
        with open(self.metadata_db, 'r') as f:
            return json.load(f)

    def _save_metadata(self, metadata: Dict[str, Any]):
        """Save metadata database."""
        with open(self.metadata_db, 'w') as f:
            json.dump(metadata, f, indent=2)

    def _has_access_permission(self, sensitivity: str) -> bool:
        """Check if current user has access permission."""
        # TODO: Implement proper user authentication/authorization
        # For now, use workspace-based rules
        from assistant.db.models import SensitivityLevel

        workspace = metadata_manager.workspace_project

        # Public: always accessible
        if sensitivity == SensitivityLevel.PUBLIC.value:
            return True

        # Internal: workspace members
        if sensitivity == SensitivityLevel.INTERNAL.value:
            return True  # Assume workspace access

        # Private: owner only (current workspace)
        if sensitivity == SensitivityLevel.PRIVATE.value:
            return workspace != "unknown"

        # Secret: explicit authorization required
        if sensitivity == SensitivityLevel.SECRET_CRITICAL.value:
            # TODO: Check for explicit authorization
            return workspace != "unknown"

        return False

    def import_documents(self, source_path: Path, recursive: bool = False) -> Dict[str, Any]:
        """Import documents from directory with encryption."""
        results = {
            "imported": 0,
            "skipped": 0,
            "errors": []
        }

        if not source_path.exists():
            results["errors"].append(f"Source path does not exist: {source_path}")
            return results

        files = source_path.rglob("*") if recursive else source_path.glob("*")

        for file_path in files:
            if file_path.is_file():
                try:
                    # Read file content
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    # Add as secure document
                    result = self.add_document(
                        filename=file_path.name,
                        content=content,
                        source="import"
                    )

                    if result["success"]:
                        results["imported"] += 1
                    else:
                        results["skipped"] += 1
                        results["errors"].append(result.get("error", "Unknown error"))

                except Exception as e:
                    results["errors"].append(f"Failed to import {file_path.name}: {str(e)}")

        return results

    def export_documents(self, dest_path: Path, sensitivity_filter: Optional[str] = None) -> Dict[str, Any]:
        """Export documents with access control filtering."""
        results = {
            "exported": 0,
            "skipped": 0,
            "errors": []
        }

        dest_path.mkdir(parents=True, exist_ok=True)

        metadata = self._load_metadata()

        for safe_filename, doc_info in metadata.items():
            try:
                # Apply sensitivity filter
                sensitivity = doc_info["metadata"]["sensitivity"]
                if sensitivity_filter and sensitivity != sensitivity_filter:
                    results["skipped"] += 1
                    continue

                # Check access permissions
                if not self._has_access_permission(sensitivity):
                    results["skipped"] += 1
                    continue

                # Decrypt and export
                doc = self.get_document(doc_info["original_filename"])
                if not doc:
                    results["skipped"] += 1
                    continue

                export_path = dest_path / doc_info["original_filename"]
                with open(export_path, 'w', encoding='utf-8') as f:
                    f.write(doc["content"])

                results["exported"] += 1

            except Exception as e:
                results["errors"].append(f"Failed to export {safe_filename}: {str(e)}")

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        metadata = self._load_metadata()

        stats = {
            "total_documents": len(metadata),
            "by_sensitivity": {},
            "storage_used_bytes": 0,
            "most_accessed": None
        }

        max_access = 0

        for doc_info in metadata.values():
            sensitivity = doc_info["metadata"]["sensitivity"]
            stats["by_sensitivity"][sensitivity] = stats["by_sensitivity"].get(sensitivity, 0) + 1

            # Calculate storage
            doc_path = Path(doc_info["encrypted_path"])
            if doc_path.exists():
                stats["storage_used_bytes"] += doc_path.stat().st_size

            # Track most accessed
            access_count = doc_info["access_count"]
            if access_count > max_access:
                max_access = access_count
                stats["most_accessed"] = doc_info["original_filename"]

        stats["storage_used_mb"] = stats["storage_used_bytes"] / (1024 * 1024)

        return stats


# Global instance
secure_knowledge_manager = SecureKnowledgeManager()