import os
from pydantic import BaseModel

class Settings(BaseModel):
    PROJECT_NAME: str = "AgentGuard"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./agentguard.db")
    MAX_EXECUTION_STEPS: int = int(os.getenv("MAX_EXECUTION_STEPS", "20"))
    MAX_TOOL_TIMEOUT_SECONDS: float = float(os.getenv("MAX_TOOL_TIMEOUT_SECONDS", "5.0"))
    RUN_OVERALL_TIMEOUT_SECONDS: float = float(os.getenv("RUN_OVERALL_TIMEOUT_SECONDS", "30.0"))
    MAX_TRACE_PAYLOAD_BYTES: int = int(os.getenv("MAX_TRACE_PAYLOAD_BYTES", "32768"))
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*"
    ]

settings = Settings()
