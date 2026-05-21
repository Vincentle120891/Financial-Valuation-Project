"""
Data Versioning Service
Tracks changes to historical data over time, enabling rollback and comparison.
"""
import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

class DataVersion(BaseModel):
    version_id: str
    timestamp: datetime
    metric_id: str
    value: Any
    source: str
    changed_by: str # "system", "user", "ai"
    previous_version_id: Optional[str] = None
    metadata: Dict = {}

class DataVersioningService:
    def __init__(self, session_id: str):
        self.session_id = session_id
        # In production, this would be a DB connection
        self.version_history: Dict[str, List[DataVersion]] = {}

    def create_version(
        self,
        metric_id: str,
        value: Any,
        source: str,
        changed_by: str,
        metadata: Dict = {}
    ) -> DataVersion:
        """Creates a new version entry for a metric."""
        previous_version = None
        if metric_id in self.version_history and len(self.version_history[metric_id]) > 0:
            previous_version = self.version_history[metric_id][-1]

        version_content = f"{metric_id}{value}{datetime.utcnow().isoformat()}"
        version_id = hashlib.sha256(version_content.encode()).hexdigest()[:12]

        new_version = DataVersion(
            version_id=version_id,
            timestamp=datetime.utcnow(),
            metric_id=metric_id,
            value=value,
            source=source,
            changed_by=changed_by,
            previous_version_id=previous_version.version_id if previous_version else None,
            metadata=metadata
        )

        if metric_id not in self.version_history:
            self.version_history[metric_id] = []
        self.version_history[metric_id].append(new_version)

        return new_version

    def get_version(self, metric_id: str, version_id: str) -> Optional[DataVersion]:
        """Retrieves a specific version of a metric."""
        if metric_id not in self.version_history:
            return None
        for v in self.version_history[metric_id]:
            if v.version_id == version_id:
                return v
        return None

    def get_current_value(self, metric_id: str) -> Optional[Any]:
        """Gets the latest value for a metric."""
        if metric_id not in self.version_history or len(self.version_history[metric_id]) == 0:
            return None
        return self.version_history[metric_id][-1].value

    def get_history(self, metric_id: str) -> List[DataVersion]:
        """Returns full history of changes for a metric."""
        return self.version_history.get(metric_id, [])

    def rollback(self, metric_id: str, target_version_id: str) -> bool:
        """Reverts a metric to a previous version (creates a new version copy)."""
        target_version = self.get_version(metric_id, target_version_id)
        if not target_version:
            return False

        # Create a new version with the old value
        self.create_version(
            metric_id=metric_id,
            value=target_version.value,
            source=f"rollback_to_{target_version_id}",
            changed_by="user",
            metadata={"rolled_back_from": self.get_current_value(metric_id)}
        )
        return True

    def compare_versions(self, metric_id: str, v1_id: str, v2_id: str) -> Dict:
        """Compares two versions of a metric."""
        v1 = self.get_version(metric_id, v1_id)
        v2 = self.get_version(metric_id, v2_id)

        if not v1 or not v2:
            return {"error": "Versions not found"}

        return {
            "v1": {"id": v1_id, "value": v1.value, "timestamp": v1.timestamp.isoformat()},
            "v2": {"id": v2_id, "value": v2.value, "timestamp": v2.timestamp.isoformat()},
            "difference": v2.value - v1.value if isinstance(v1.value, (int, float)) and isinstance(v2.value, (int, float)) else "N/A"
        }

# Global registry
_active_versioners: Dict[str, DataVersioningService] = {}

def get_versioning_service(session_id: str) -> DataVersioningService:
    if session_id not in _active_versioners:
        _active_versioners[session_id] = DataVersioningService(session_id)
    return _active_versioners[session_id]