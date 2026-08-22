from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
import enum

class HILTStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"

class HiltTaskBase(BaseModel):
    user_id: str
    task_type: str
    payload: Dict[str, Any]
    status: HILTStatus = HILTStatus.PENDING

class HiltTaskCreate(HiltTaskBase):
    pass

class HiltTaskResponse(HiltTaskBase):
    id: str
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolution_data: Optional[Dict[str, Any]] = None
    resolver_user_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

# Aliases for compatibility
HILTTask = HiltTaskResponse
HILTTaskCreate = HiltTaskCreate
