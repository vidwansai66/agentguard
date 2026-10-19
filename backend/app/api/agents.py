import json
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.agent import Agent, AgentVersion
from app.models.run import TestRun
from app.schemas.agent import AgentResponse, AgentCreate, AgentUpdate, AgentVersionResponse
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
        "status": agent.status,
        "current_version": agent.current_version,
        "supported_tools": agent.supported_tools,
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
        status="active",
        current_version="1.0.0",
        supported_tools_json=json.dumps(payload.supported_tools),
        config_schema_json=json.dumps(payload.config_schema)
    )
    db.add(agent)
    db.flush()

    v1 = AgentVersion(
        id=f"ver-{agent.id}-100",
        agent_id=agent.id,
        version_tag="1.0.0",
        strategy="baseline",
        config_json=json.dumps({}),
        description="Initial baseline version",
        is_candidate=False
    )
    db.add(v1)
    db.commit()
    db.refresh(agent)
    return _to_agent_response(agent)

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
