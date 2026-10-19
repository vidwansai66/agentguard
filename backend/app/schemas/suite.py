from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class SuiteScenarioCreate(BaseModel):
    scenario_id: str
    order: int = 0

class SuiteCreate(BaseModel):
    id: str | None = None
    name: str
    description: str | None = None
    is_regression_suite: bool = False
    scenario_ids: list[str] = Field(default_factory=list)

class SuiteUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_regression_suite: bool | None = None
    scenario_ids: list[str] | None = None

class SuiteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    description: str | None = None
    is_regression_suite: bool
    scenario_ids: list[str] = Field(default_factory=list)
    scenario_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None
