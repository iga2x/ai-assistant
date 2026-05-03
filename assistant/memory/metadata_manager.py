"""
Comprehensive metadata management system for data classification and retention.
Handles sensitivity tagging, deduplication, workspace isolation, and retention enforcement.
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
import os
import re

from assistant.db.models import (
    SensitivityLevel,
    DataClassification,
    RetentionPolicy
)


class MetadataManager:
    """Manages comprehensive metadata for all data stored in memory."""

    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.workspace_project = self._get_workspace_project()
        self.sensitivity_patterns = self._load_sensitivity_patterns()
        self.retention_durations = {
            RetentionPolicy.SESSION_ONLY: timedelta(hours=24),
            RetentionPolicy.SHORT_TERM: timedelta(days=3),
            RetentionPolicy.LONG_TERM: timedelta(days=90),
            RetentionPolicy.PERMANENT_MANUAL: None  # Never expires
        }

    def _get_workspace_project(self) -> str:
        """Extract current workspace/project ID."""
        try:
            cwd = os.getcwd()
            # Try to identify project from git repo
            if (Path(cwd) / '.git').exists():
                return cwd
            # Fallback to parent directory name
            return str(Path(cwd).name)
        except:
            return "unknown"

    def _load_sensitivity_patterns(self) -> Dict[str, SensitivityLevel]:
        """Load sensitivity classification patterns."""
        return {
            # SECRET_CRITICAL patterns (highest priority)
            r'(?i)\b(?:password|passwd|secret|api[_-]?key|token|credential|private[_-]?key)\b': SensitivityLevel.SECRET_CRITICAL,
            r'(?i)(?:vulnerability|exploit|weakness|cve-)\d{4}-\d{4,7}': SensitivityLevel.SECRET_CRITICAL,
            r'\b(?:192\.168\.(?:\d{1,3}\.){2}|10\.(?:\d{1,3}\.){2}|172\.(?:1[6-9]|2[0-9]|3[0-1])\.(?:\d{1,3}\.)\d{1,3})\b': SensitivityLevel.SECRET_CRITICAL,

            # PRIVATE patterns
            r'(?i)\b(?:username|email|phone|personal)\b': SensitivityLevel.PRIVATE,
            r'^~\/': SensitivityLevel.PRIVATE,
            r'(?i)(?:my|personal|private)[_\s-]*(?:file|data|info)': SensitivityLevel.PRIVATE,
            r'\.(?:ssh|config|pem|key)$': SensitivityLevel.PRIVATE,

            # INTERNAL patterns (default for codebase/project data)
            r'(?i)\b(?:codebase|project|development|test|local|dev|scan|result|output)\b': SensitivityLevel.INTERNAL,
        }

    def classify_sensitivity(self, content: str, source: str = "unknown") -> SensitivityLevel:
        """Automatically classify sensitivity level based on content patterns."""
        # Check source-based rules first
        if source in ["terminal_output", "tool_result"]:
            # Check for secrets in output
            for pattern, level in self.sensitivity_patterns.items():
                if re.search(pattern, content):
                    return level

        # Default to INTERNAL for system-generated content
        return SensitivityLevel.INTERNAL

    def classify_data(self, content: str, source: str = "unknown") -> DataClassification:
        """Classify data type based on content and source."""
        classification_map = {
            "user_input": DataClassification.USER_INSTRUCTION,
            "terminal_output": DataClassification.RAW_LOG,
            "tool_result": DataClassification.TOOL_RESULT,
            "ai_response": DataClassification.TEMPORARY_CONTEXT,
            "session_state": DataClassification.TEMPORARY_CONTEXT,
        }

        if source in classification_map:
            return classification_map[source]

        # Content-based classification
        if any(keyword in content.lower() for keyword in ["report", "analysis", "summary"]):
            return DataClassification.EVIDENCE_REPORT

        if any(keyword in content.lower() for keyword in ["ip", "domain", "host", "service"]):
            return DataClassification.TOOL_RESULT

        return DataClassification.RAW_LOG

    def determine_retention(self, classification: DataClassification, sensitivity: SensitivityLevel) -> RetentionPolicy:
        """Determine appropriate retention policy based on classification and sensitivity."""
        retention_map = {
            DataClassification.TEMPORARY_CONTEXT: RetentionPolicy.SESSION_ONLY,
            DataClassification.RAW_LOG: RetentionPolicy.SHORT_TERM,
            DataClassification.SENSITIVE_DATA: RetentionPolicy.PERMANENT_MANUAL,
            DataClassification.EVIDENCE_REPORT: RetentionPolicy.LONG_TERM,
        }

        # Check specific rules
        if classification in retention_map:
            return retention_map[classification]

        # Sensitivity-based defaults
        if sensitivity == SensitivityLevel.SECRET_CRITICAL:
            return RetentionPolicy.PERMANENT_MANUAL
        elif sensitivity == SensitivityLevel.PRIVATE:
            return RetentionPolicy.LONG_TERM

        # Default
        return RetentionPolicy.LONG_TERM

    def compute_data_hash(self, content: str) -> str:
        """Compute SHA-256 hash for deduplication."""
        return hashlib.sha256(content.encode()).hexdigest()

    def generate_metadata(self,
                         content: str,
                         source: str = "unknown",
                         user_intent: str = "unknown",
                         command_tool: str = None,
                         confidence: float = 1.0,
                         tags: List[str] = None) -> Dict[str, Any]:
        """Generate comprehensive metadata for a data item."""
        sensitivity = self.classify_sensitivity(content, source)
        classification = self.classify_data(content, source)
        retention_policy = self.determine_retention(classification, sensitivity)

        # Calculate expiry time
        duration = self.retention_durations.get(retention_policy)
        expires_at = None
        if duration:
            expires_at = datetime.now(timezone.utc) + duration

        return {
            "source": source,
            "workspace_project": self.workspace_project,
            "command_tool_used": command_tool,
            "user_intent": user_intent,
            "confidence": confidence,
            "sensitivity": sensitivity,
            "classification": classification,
            "retention_policy": retention_policy,
            "tags": tags or [],
            "related_session_ids": [self.session_id],
            "related_file_ids": [],
            "data_hash": self.compute_data_hash(content),
            "expires_at": expires_at
        }

    def should_store(self, content: str, metadata: Dict[str, Any]) -> bool:
        """Determine if content should be stored based on rules."""
        classification = metadata["classification"]
        sensitivity = metadata["sensitivity"]
        retention = metadata["retention_policy"]

        # Never store temporary context
        if retention == RetentionPolicy.SESSION_ONLY:
            return False

        # Check size limits (100KB threshold for raw logs)
        if classification == DataClassification.RAW_LOG and len(content) > 100000:
            return False

        # Never store sensitive data without explicit approval
        if sensitivity == SensitivityLevel.SECRET_CRITICAL:
            # TODO: Add user approval mechanism
            return False

        # Check duplicates
        existing_hash = metadata["data_hash"]
        # TODO: Check if hash already exists in database

        return True

    def summarize_for_storage(self, content: str, classification: DataClassification) -> str:
        """Summarize content for storage if needed."""
        if classification == DataClassification.RAW_LOG:
            # Extract key findings from terminal output
            lines = content.split('\n')
            # Keep only lines with significant information
            significant_lines = [
                line for line in lines
                if any(keyword in line.lower() for keyword in ['error', 'warning', 'failed', 'success', 'open', 'closed', 'found'])
            ][:20]  # Max 20 lines
            return '\n'.join(significant_lines)

        if classification == DataClassification.TOOL_RESULT:
            # Try to parse structured output
            try:
                import json
                if content.strip().startswith('{'):
                    parsed = json.loads(content)
                    return json.dumps(parsed, indent=2)
            except:
                pass

        return content

    def enforce_retention(self, entity_data: Dict[str, Any]) -> bool:
        """Check if entity should be retained based on expiry."""
        expires_at = entity_data.get("expires_at")
        if not expires_at:
            return True  # No expiry, keep it

        now = datetime.now(timezone.utc)
        if now > expires_at:
            return False  # Should be deleted

        return True  # Keep it


class WorkspaceIsolation:
    """Handles workspace/project isolation for data access."""

    def __init__(self, metadata_manager: MetadataManager):
        self.metadata_manager = metadata_manager

    def is_accessible_in_current_workspace(self, entity_data: Dict[str, Any]) -> bool:
        """Check if entity data is accessible in current workspace."""
        entity_workspace = entity_data.get("workspace_project")
        current_workspace = self.metadata_manager.workspace_project

        # Public data is accessible everywhere
        if entity_data.get("sensitivity") == SensitivityLevel.PUBLIC:
            return True

        # Internal data: check workspace match
        if entity_data.get("sensitivity") == SensitivityLevel.INTERNAL:
            return entity_workspace == current_workspace or entity_workspace == "global"

        # Private/Secret: only in original workspace
        return entity_workspace == current_workspace

    def filter_entities_by_workspace(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter entities to only include those accessible in current workspace."""
        return [
            entity for entity in entities
            if self.is_accessible_in_current_workspace(entity)
        ]


class DeduplicationManager:
    """Handles data deduplication based on content hashing."""

    def __init__(self):
        self.hash_index = {}  # data_hash -> entity_id

    def check_duplicate(self, data_hash: str) -> Optional[int]:
        """Check if data hash already exists, return entity ID if found."""
        return self.hash_index.get(data_hash)

    def register_entity(self, entity_id: int, data_hash: str):
        """Register new entity in hash index."""
        self.hash_index[data_hash] = entity_id

    def remove_entity(self, entity_id: int, data_hash: str):
        """Remove entity from hash index."""
        if self.hash_index.get(data_hash) == entity_id:
            del self.hash_index[data_hash]


# Global instances
metadata_manager = MetadataManager()
workspace_isolation = WorkspaceIsolation(metadata_manager)
deduplication_manager = DeduplicationManager()
