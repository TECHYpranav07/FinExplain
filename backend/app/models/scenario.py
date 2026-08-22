from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any

class ScenarioBase(BaseModel):
    title: str
    principal: float
    duration_months: int
    interest_rate: Optional[float] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)

class ScenarioCreate(ScenarioBase):
    user_id: str

class ScenarioResponse(ScenarioBase):
    id: str
    user_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
