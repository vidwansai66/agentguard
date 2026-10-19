import json
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.agent import Agent, AgentVersion
from app.models.run import TestRun
from app.agents.registry import agent_registry
from app.schemas.agent import (
    AgentResponse,
    AgentCreate,
    AgentCustomRegister,
    ExistingAgentConnectRequest,
    AgentValidateConfigRequest,
    AgentValidateConfigResponse,
    AgentTestConnectionRequest,
    AgentTestConnectionResponse,
    AgentUpdate,
    AgentVersionResponse
)
from app.core.errors import NotFoundError, ValidationError

router = APIRouter(prefix="/agents", tags=["Agents"])

def _to_agent_response(agent: Agent) -> dict:
    versions = [
        AgentVersionResponse(
            id=v.id,
            agent_id=v.agent_id,
            version_tag=v.version_tag,
            strategy=v.strategy,
            config=v.config,
            description=v.description,
            is_candidate=v.is_candidate,
            created_at=v.created_at
        )
        for v in agent.versions
    ]
    return {
        "id": agent.id,
        "name": agent.name,
        "description": agent.description,
        "agent_type": agent.agent_type,
        "adapter_type": getattr(agent, "adapter_type", "python"),
        "registration_source": getattr(agent, "registration_source", "built_in"),
        "status": agent.status,
        "observability_level": getattr(agent, "observability_level", "level_3_instrumented_tools"),
        "current_version": agent.current_version,
        "supported_tools": agent.supported_tools,
        "declared_capabilities": agent.declared_capabilities,
        "adapter_config": agent.adapter_config,
        "created_at": agent.created_at,
        "updated_at": agent.updated_at,
        "versions": versions
    }

@router.get("", response_model=list[AgentResponse])
def list_agents(db: Session = Depends(get_db)):
    agents = db.query(Agent).all()
    return [_to_agent_response(a) for a in agents]

@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
def create_agent(payload: AgentCreate, db: Session = Depends(get_db)):
    existing = db.query(Agent).filter(Agent.id == payload.id).first()
    if existing:
        raise ValidationError(f"Agent with ID '{payload.id}' already exists.")

    agent = Agent(
        id=payload.id,
        name=payload.name,
        description=payload.description,
        agent_type=payload.agent_type,
        adapter_type=payload.adapter_type,
        registration_source=payload.registration_source,
        status="active",
        current_version="1.0.0",
        supported_tools_json=json.dumps(payload.supported_tools),
        declared_capabilities_json=json.dumps(payload.declared_capabilities),
        adapter_config_json=json.dumps(payload.adapter_config),
        config_schema_json=json.dumps(payload.config_schema)
    )
    db.add(agent)
    db.flush()

    v1 = AgentVersion(
        id=f"ver-{agent.id}-100",
        agent_id=agent.id,
        version_tag="1.0.0",
        strategy="baseline",
        config_json=json.dumps(payload.adapter_config or {}),
        description="Initial baseline version",
        is_candidate=False
    )
    db.add(v1)
    db.commit()
    db.refresh(agent)
    return _to_agent_response(agent)

@router.post("/custom", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
def register_custom_agent(payload: AgentCustomRegister, db: Session = Depends(get_db)):
    """
    Registers a new custom agent with an explicit Python or HTTP adapter contract.
    Validates adapter configuration before persisting.
    """
    existing = db.query(Agent).filter(Agent.id == payload.id).first()
    if existing:
        raise ValidationError(f"Agent with ID '{payload.id}' already exists.")

    # Validate adapter configuration
    val_res = agent_registry.validate_adapter_config(payload.adapter_type, payload.adapter_config)

    agent = Agent(
        id=payload.id,
        name=payload.name,
        description=payload.description,
        agent_type=f"{payload.adapter_type}_custom_agent",
        adapter_type=payload.adapter_type,
        registration_source="custom",
        status="active",
        observability_level=payload.observability_level,
        current_version=payload.version,
        supported_tools_json=json.dumps(payload.supported_tools),
        declared_capabilities_json=json.dumps(payload.declared_capabilities),
        adapter_config_json=json.dumps(payload.adapter_config),
        config_schema_json=json.dumps({})
    )
    db.add(agent)
    db.flush()

    v1 = AgentVersion(
        id=f"ver-{agent.id}-{payload.version.replace('.', '')}",
        agent_id=agent.id,
        version_tag=payload.version,
        strategy=payload.strategy,
        config_json=json.dumps(payload.adapter_config),
        description=f"Initial registration for {payload.name}",
        is_candidate=False
    )
    db.add(v1)
    db.commit()
    db.refresh(agent)
    return _to_agent_response(agent)

@router.post("/connect-existing", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
def connect_existing_agent(payload: ExistingAgentConnectRequest, db: Session = Depends(get_db)):
    """
    Connect an existing AI agent via HTTP endpoint or Python SDK wrapper
    without requiring modifications to the agent's core code.
    """
    existing = db.query(Agent).filter(Agent.id == payload.id).first()
    if existing:
        raise ValidationError(f"Agent with ID '{payload.id}' already exists.")

    if payload.connection_method == "http_endpoint" and payload.http_config:
        adapter_type = "http"
        adapter_config = payload.http_config.model_dump()
        adapter_config["observability_level"] = payload.observability_level
    elif payload.connection_method == "python_sdk_wrapper" and payload.sdk_config:
        adapter_type = "python_sdk_wrapper"
        adapter_config = payload.sdk_config.model_dump()
        adapter_config["observability_level"] = payload.observability_level
    elif payload.connection_method in ["agent_framework", "framework"]:
        adapter_type = "langgraph"
        if payload.framework_config:
            adapter_config = payload.framework_config.model_dump()
        else:
            adapter_config = {"framework": "langgraph", "graph_target": "customer_support_graph"}
        adapter_config["observability_level"] = "level_3_instrumented_tools"
    elif payload.connection_method == "model_backed":
        adapter_type = "model_backed"
        if payload.llm_config:
            adapter_config = payload.llm_config.model_dump()
        else:
            adapter_config = {"provider": "openai_compatible", "model": "gpt-4o-mini"}
        adapter_config["observability_level"] = "level_3_instrumented_tools"

    else:
        adapter_type = "http" if payload.connection_method == "http_endpoint" else "python_sdk_wrapper"
        adapter_config = {"observability_level": payload.observability_level}

    # Validate
    agent_registry.validate_adapter_config(adapter_type, adapter_config)

    agent = Agent(
        id=payload.id,
        name=payload.name,
        description=payload.description or f"Existing agent connected via {payload.connection_method}",
        agent_type=f"{adapter_type}_connected_agent",
        adapter_type=adapter_type,
        registration_source="connected_existing",
        status="active",
        observability_level=adapter_config.get("observability_level", payload.observability_level),
        current_version=payload.version,
        supported_tools_json=json.dumps(payload.supported_tools or ["ticket_create", "ticket_query", "ticket_get"]),
        declared_capabilities_json=json.dumps(payload.declared_capabilities or ["ticket_create", "ticket_query", "ticket_get"]),
        adapter_config_json=json.dumps(adapter_config),
        config_schema_json=json.dumps({})
    )
    db.add(agent)
    db.flush()

    v1 = AgentVersion(
        id=f"ver-{agent.id}-{payload.version.replace('.', '')}",
        agent_id=agent.id,
        version_tag=payload.version,
        strategy="baseline",
        config_json=json.dumps(adapter_config),
        description=f"Connected version for {payload.name} ({agent.observability_level})",
        is_candidate=False
    )
    db.add(v1)
    db.commit()
    db.refresh(agent)
    return _to_agent_response(agent)

@router.get("/frameworks/catalog")
def get_framework_catalog():
    """Returns framework support catalog: implemented vs planned frameworks."""
    return agent_registry.get_framework_catalog()


@router.post("/validate-config", response_model=AgentValidateConfigResponse)
def validate_adapter_config(payload: AgentValidateConfigRequest):
    """
    Validates adapter configuration for security boundaries, schema correctness, and accessibility.
    """
    try:
        details = agent_registry.validate_adapter_config(payload.adapter_type, payload.adapter_config)
        return AgentValidateConfigResponse(
            valid=True,
            adapter_type=payload.adapter_type,
            details=details
        )
    except Exception as e:
        return AgentValidateConfigResponse(
            valid=False,
            error=str(e),
            adapter_type=payload.adapter_type,
            details={}
        )

@router.post("/{agent_id}/test-connection", response_model=AgentTestConnectionResponse)
def test_agent_connection(
    agent_id: str,
    payload: AgentTestConnectionRequest | None = None,
    db: Session = Depends(get_db)
):
    """
    Tests initialization, connectivity, and declared capability handshake for an agent.
    """
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise NotFoundError("Agent", agent_id)

    adapter_type = payload.adapter_type if (payload and payload.adapter_type) else agent.adapter_type
    adapter_config = payload.adapter_config if (payload and payload.adapter_config is not None) else agent.adapter_config

    try:
        adapter_instance = agent_registry.get_agent(
            agent_id=agent.id,
            version=agent.current_version,
            strategy="baseline",
            config=adapter_config,
            adapter_type=adapter_type
        )
        test_res = adapter_instance.test_connection()
        try:
            adapter_instance.dispose()
        except Exception:
            pass

        return AgentTestConnectionResponse(
            status=test_res.get("status", "healthy"),
            message=test_res.get("message", "Adapter test completed successfully."),
            adapter_type=adapter_type,
            declared_capabilities=getattr(adapter_instance, "declared_capabilities", agent.declared_capabilities),
            details=test_res
        )
    except Exception as e:
        return AgentTestConnectionResponse(
            status="error",
            message=f"Adapter connection test failed: {str(e)}",
            adapter_type=adapter_type,
            declared_capabilities=agent.declared_capabilities,
            details={"error": str(e)}
        )

@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: str, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise NotFoundError("Agent", agent_id)
    return _to_agent_response(agent)

@router.patch("/{agent_id}", response_model=AgentResponse)
def update_agent(agent_id: str, payload: AgentUpdate, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise NotFoundError("Agent", agent_id)

    if payload.name is not None:
        agent.name = payload.name
    if payload.description is not None:
        agent.description = payload.description
    if payload.status is not None:
        agent.status = payload.status
    if payload.current_version is not None:
        agent.current_version = payload.current_version
    if payload.declared_capabilities is not None:
        agent.declared_capabilities = payload.declared_capabilities
    if payload.adapter_config is not None:
        agent.adapter_config = payload.adapter_config

    db.commit()
    db.refresh(agent)
    return _to_agent_response(agent)

@router.get("/{agent_id}/runs")
def get_agent_runs(agent_id: str, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise NotFoundError("Agent", agent_id)
    runs = db.query(TestRun).filter(TestRun.agent_id == agent_id).order_by(TestRun.created_at.desc()).all()
    return runs
