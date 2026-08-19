from datetime import datetime
from pydantic import BaseModel
from typing import Optional, Dict, Any

class ScenarioBase(BaseModel):
    title: str
    principal: float
    duration_months: int
    interest_rate: Optional[float] = None
    parameters: Dict[str, Any] = {}

class ScenarioCreate(ScenarioBase):
    user_id: int

class ScenarioResponse(ScenarioBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True