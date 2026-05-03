"""
Retention policy enforcement system.
Handles automatic data expiry, cleanup scheduling, and manual purge operations.
"""

import threading
import time
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List

try:
    import schedule
    HAS_SCHEDULE = True
except ImportError:
    HAS_SCHEDULE = False

from assistant.memory.main import MemoryManager, EntityStore
from assistant.db.models import RetentionPolicy, DataClassification
from assistant.utils.logger import get_logger

logger = get_logger(__name__)


class RetentionManager:
    """Manages data retention policies and cleanup operations."""

    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
        self.cleanup_interval_hours = 6  # Run cleanup every 6 hours
        self.retention_config = self._load_retention_config()
        self.scheduler_running = False
        self.scheduler_thread = None

    def _load_retention_config(self) -> Dict[str, Any]:
        """Load retention policy configuration."""
        config_path = Path.home() / ".assistant" / "retention_config.json"

        if not config_path.exists():
            return self._create_default_config(config_path)

        with open(config_path, 'r') as f:
            return json.load(f)

    def _create_default_config(self, config_path: Path) -> Dict[str, Any]:
        """Create default retention configuration."""
        default_config = {
            "cleanup_interval_hours": 6,
            "retention_periods": {
                "session_only": {
                    "duration_hours": 24,
                    "description": "Temporary session data, auto-delete after 24 hours"
                },
                "short_term": {
                    "duration_hours": 72,
                    "description": "Short-term data, delete after 3 days"
                },
                "long_term": {
                    "duration_days": 90,
                    "description": "Long-term data, keep for 90 days"
                },
                "permanent_manual": {
                    "duration_days": None,
                    "description": "Manual deletion only, never auto-expire"
                }
            },
            "storage_limits": {
                "max_entities": 200,
                "max_total_size_mb": 100,
                "max_single_item_kb": 100
            },
            "classification_rules": {
                "session_only": ["session_state", "suggested_memories", "active_prompts"],
                "short_term": ["terminal_output_summaries", "partial_scan_results"],
                "long_term": ["validated_entities", "conversation_history", "audit_trails"],
                "permanent_manual": ["secrets", "critical_findings", "user_bookmarked"]
            }
        }

        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=2)

        return default_config

    def get_expiry_date(self, retention_policy: RetentionPolicy) -> Optional[datetime]:
        """Calculate expiry date based on retention policy."""
        if retention_policy == RetentionPolicy.PERMANENT_MANUAL:
            return None  # Never expires

        if retention_policy == RetentionPolicy.SESSION_ONLY:
            duration = timedelta(hours=self.retention_config["retention_periods"]["session_only"]["duration_hours"])
        elif retention_policy == RetentionPolicy.SHORT_TERM:
            duration = timedelta(hours=self.retention_config["retention_periods"]["short_term"]["duration_hours"])
        elif retention_policy == RetentionPolicy.LONG_TERM:
            duration = timedelta(days=self.retention_config["retention_periods"]["long_term"]["duration_days"])
        else:
            return None  # Unknown policy, don't expire

        return datetime.now(timezone.utc) + duration

    def enforce_retention(self) -> Dict[str, Any]:
        """Enforce retention policies across all stored data."""
        logger.info("Starting retention policy enforcement")

        results = {
            "deleted_entities": 0,
            "expired_entities": 0,
            "size_reduced_mb": 0,
            "errors": []
        }

        try:
            # Get all entities from database
            entities = self.memory_manager.entities.list_all()
            now = datetime.now(timezone.utc)

            entities_to_delete = []

            for entity in entities:
                entity_data = self._parse_entity_data(entity)
                expires_at = entity_data.get("expires_at")

                # Check if entity has expired
                if expires_at:
                    expiry_date = datetime.fromisoformat(expires_at)
                    if now > expiry_date:
                        entities_to_delete.append(entity["name"])
                        results["expired_entities"] += 1
                        logger.info(f"Entity {entity['name']} expired on {expiry_date}")

                # Check storage limits
                if self._exceeds_storage_limits(entity_data):
                    if not self._should_keep_despite_limits(entity_data):
                        entities_to_delete.append(entity["name"])
                        logger.info(f"Entity {entity['name']} exceeds storage limits")

            # Delete expired entities
            for entity_name in entities_to_delete:
                try:
                    size_before = self._get_entity_size(entity_name)
                    self.memory_manager.entities.delete(entity_name)
                    results["deleted_entities"] += 1
                    results["size_reduced_mb"] += size_before / (1024 * 1024)
                    logger.info(f"Deleted expired entity: {entity_name}")
                except Exception as e:
                    results["errors"].append(f"Failed to delete {entity_name}: {str(e)}")
                    logger.error(f"Failed to delete entity {entity_name}: {e}")

            # Run memory cleanup
            self.memory_manager.cleanup()

            logger.info(f"Retention enforcement complete. Deleted {results['deleted_entities']} entities")

        except Exception as e:
            results["errors"].append(f"Retention enforcement failed: {str(e)}")
            logger.error(f"Retention enforcement failed: {e}")

        return results

    def _parse_entity_data(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Parse entity data for retention checks."""
        return {
            "name": entity.get("name"),
            "type": entity.get("type"),
            "value": entity.get("value"),
            "size": len(str(entity.get("value", ""))),
            "expires_at": entity.get("last_used"),  # Use last_used for legacy data
            "confidence": entity.get("confidence", 1.0),
            "success_count": entity.get("success_count", 0)
        }

    def _exceeds_storage_limits(self, entity_data: Dict[str, Any]) -> bool:
        """Check if entity exceeds storage limits."""
        max_size_kb = self.retention_config["storage_limits"]["max_single_item_kb"]
        return entity_data["size"] > (max_size_kb * 1024)

    def _should_keep_despite_limits(self, entity_data: Dict[str, Any]) -> bool:
        """Check if entity should be kept despite exceeding limits."""
        # Keep high-confidence, frequently-used entities
        return (
            entity_data["confidence"] > 0.9 and
            entity_data["success_count"] > 10
        )

    def _get_entity_size(self, entity_name: str) -> int:
        """Get size of entity in bytes."""
        try:
            entity_value = self.memory_manager.entities.get(entity_name)
            return len(str(entity_value)) if entity_value else 0
        except:
            return 0

    def manual_purge(self,
                   entity_type: Optional[str] = None,
                   before_date: Optional[datetime] = None,
                   below_confidence: Optional[float] = None) -> Dict[str, Any]:
        """Manually purge entities based on criteria."""
        entities = self.memory_manager.entities.list_all()
        results = {
            "criteria": {
                "entity_type": entity_type,
                "before_date": str(before_date) if before_date else None,
                "below_confidence": below_confidence
            },
            "deleted": 0,
            "skipped": 0,
            "errors": []
        }

        for entity in entities:
            try:
                should_delete = True

                if entity_type and entity.get("type") != entity_type:
                    should_delete = False
                    results["skipped"] += 1

                if before_date:
                    entity_date = datetime.fromisoformat(entity.get("created_at", ""))
                    if entity_date >= before_date:
                        should_delete = False
                        results["skipped"] += 1

                if below_confidence and entity.get("confidence", 1.0) >= below_confidence:
                    should_delete = False
                    results["skipped"] += 1

                if should_delete:
                    self.memory_manager.entities.delete(entity["name"])
                    results["deleted"] += 1
                    logger.info(f"Manual purge: Deleted {entity['name']}")

            except Exception as e:
                results["errors"].append(f"Failed to purge {entity.get('name')}: {str(e)}")

        return results

    def start_scheduler(self):
        """Start automatic cleanup scheduler."""
        if not HAS_SCHEDULE:
            logger.warning("Schedule module not available, automatic cleanup disabled")
            return False

        if self.scheduler_running:
            logger.warning("Scheduler already running")
            return False

        self.scheduler_running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        logger.info(f"Retention scheduler started (interval: {self.cleanup_interval_hours}h)")
        return True

    def stop_scheduler(self):
        """Stop automatic cleanup scheduler."""
        self.scheduler_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=10)
            logger.info("Retention scheduler stopped")

    def _run_scheduler(self):
        """Run scheduled cleanup jobs."""
        # Schedule cleanup jobs
        schedule.every(self.cleanup_interval_hours).hours.do(self.enforce_retention)

        while self.scheduler_running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

    def update_config(self, new_config: Dict[str, Any]):
        """Update retention configuration."""
        # Validate configuration
        self._validate_config(new_config)

        # Merge with existing config
        self.retention_config.update(new_config)

        # Save updated config
        config_path = Path.home() / ".assistant" / "retention_config.json"
        with open(config_path, 'w') as f:
            json.dump(self.retention_config, f, indent=2)

        logger.info("Retention configuration updated")

    def _validate_config(self, config: Dict[str, Any]):
        """Validate retention configuration values."""
        if "cleanup_interval_hours" in config:
            interval = config["cleanup_interval_hours"]
            if not (1 <= interval <= 24):
                raise ValueError("Cleanup interval must be between 1 and 24 hours")

        if "storage_limits" in config:
            limits = config["storage_limits"]
            if "max_entities" in limits and limits["max_entities"] < 50:
                raise ValueError("Maximum entities must be at least 50")

    def get_retention_stats(self) -> Dict[str, Any]:
        """Get current retention statistics."""
        entities = self.memory_manager.entities.list_all()

        stats = {
            "total_entities": len(entities),
            "by_type": {},
            "by_confidence": {},
            "storage_used_bytes": 0,
            "near_expiry": 0,
            "retention_policies": {}
        }

        now = datetime.now(timezone.utc)

        for entity in entities:
            entity_type = entity.get("type", "unknown")
            confidence = entity.get("confidence", 1.0)

            # Count by type
            stats["by_type"][entity_type] = stats["by_type"].get(entity_type, 0) + 1

            # Count by confidence
            conf_range = "high" if confidence > 0.8 else "medium" if confidence > 0.5 else "low"
            stats["by_confidence"][conf_range] = stats["by_confidence"].get(conf_range, 0) + 1

            # Calculate storage
            stats["storage_used_bytes"] += len(str(entity.get("value", "")))

            # Check near expiry (within 7 days)
            last_used = entity.get("last_used")
            if last_used:
                last_used_date = datetime.fromisoformat(last_used)
                if (now - last_used_date).days > 83:  # 90 - 7 days
                    stats["near_expiry"] += 1

        stats["storage_used_mb"] = stats["storage_used_bytes"] / (1024 * 1024)

        return stats


# Global instance (initialized when needed)
_retention_manager = None


def get_retention_manager(memory_manager: MemoryManager) -> RetentionManager:
    """Get or create global retention manager instance."""
    global _retention_manager
    if _retention_manager is None:
        _retention_manager = RetentionManager(memory_manager)
    return _retention_manager