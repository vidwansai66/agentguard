import os
from pydantic import BaseModel

def _get_database_url() -> str:
    url = os.getenv("DATABASE_URL", "sqlite:///./agentguard.db")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url

def _get_cors_origins() -> list[str]:
    origins_env = os.getenv("CORS_ORIGINS", "")
    base_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://agentguard-chi.vercel.app",
        "*"
    ]
    if origins_env:
        extra = [o.strip() for o in origins_env.split(",") if o.strip()]
        for o in extra:
            if o not in base_origins:
                base_origins.append(o)
    return base_origins

class Settings(BaseModel):
    PROJECT_NAME: str = "AgentGuard"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    DATABASE_URL: str = _get_database_url()
    MAX_EXECUTION_STEPS: int = int(os.getenv("MAX_EXECUTION_STEPS", "20"))
    MAX_TOOL_TIMEOUT_SECONDS: float = float(os.getenv("MAX_TOOL_TIMEOUT_SECONDS", "5.0"))
    RUN_OVERALL_TIMEOUT_SECONDS: float = float(os.getenv("RUN_OVERALL_TIMEOUT_SECONDS", "30.0"))
    MAX_TRACE_PAYLOAD_BYTES: int = int(os.getenv("MAX_TRACE_PAYLOAD_BYTES", "32768"))
    CORS_ORIGINS: list[str] = _get_cors_origins()

settings = Settings()
