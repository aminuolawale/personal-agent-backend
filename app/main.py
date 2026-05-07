from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Agent, AgentConnection, AgentTool, TraceEvent
from app.runtime import AgentRuntime
from app.schemas import (
    AgentCreate,
    AgentGraphResponse,
    AgentRead,
    AgentUpdate,
    ConnectionCreate,
    ConnectionRead,
    ConnectionUpdate,
    GraphEdge,
    GraphNode,
    RunCreate,
    RunResult,
    ToolCreate,
    ToolRead,
    ToolUpdate,
    TraceEventRead,
)
from app.seed import seed_defaults
from app.settings import get_settings

settings = get_settings()

app = FastAPI(title="Personal Agent Runtime")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/admin/seed")
def seed(session: Session = Depends(get_session)) -> dict[str, str]:
    seed_defaults(session)
    return {"status": "seeded"}


@app.get("/api/agents", response_model=list[AgentRead])
def list_agents(session: Session = Depends(get_session)) -> list[Agent]:
    return list(session.scalars(select(Agent).order_by(Agent.is_root.desc(), Agent.name)))


@app.post("/api/agents", response_model=AgentRead, status_code=status.HTTP_201_CREATED)
def create_agent(payload: AgentCreate, session: Session = Depends(get_session)) -> Agent:
    agent = Agent(**payload.model_dump())
    session.add(agent)
    return _commit_or_409(session, agent)


@app.get("/api/agents/{agent_id}", response_model=AgentRead)
def get_agent(agent_id: UUID, session: Session = Depends(get_session)) -> Agent:
    return _get_agent_or_404(session, agent_id)


@app.patch("/api/agents/{agent_id}", response_model=AgentRead)
def update_agent(agent_id: UUID, payload: AgentUpdate, session: Session = Depends(get_session)) -> Agent:
    agent = _get_agent_or_404(session, agent_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(agent, key, value)
    return _commit_or_409(session, agent)


@app.delete("/api/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(agent_id: UUID, session: Session = Depends(get_session)) -> Response:
    agent = _get_agent_or_404(session, agent_id)
    session.delete(agent)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/agents/{agent_id}/tools", response_model=list[ToolRead])
def list_tools(agent_id: UUID, session: Session = Depends(get_session)) -> list[AgentTool]:
    return list(session.scalars(select(AgentTool).where(AgentTool.agent_id == agent_id)))


@app.post("/api/tools", response_model=ToolRead, status_code=status.HTTP_201_CREATED)
def create_tool(payload: ToolCreate, session: Session = Depends(get_session)) -> AgentTool:
    _get_agent_or_404(session, payload.agent_id)
    tool = AgentTool(**payload.model_dump())
    session.add(tool)
    return _commit_or_409(session, tool)


@app.patch("/api/tools/{tool_id}", response_model=ToolRead)
def update_tool(tool_id: UUID, payload: ToolUpdate, session: Session = Depends(get_session)) -> AgentTool:
    tool = session.get(AgentTool, tool_id)
    if tool is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(tool, key, value)
    return _commit_or_409(session, tool)


@app.delete("/api/tools/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tool(tool_id: UUID, session: Session = Depends(get_session)) -> Response:
    tool = session.get(AgentTool, tool_id)
    if tool is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")
    session.delete(tool)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/connections", response_model=list[ConnectionRead])
def list_connections(session: Session = Depends(get_session)) -> list[AgentConnection]:
    return list(session.scalars(select(AgentConnection).order_by(AgentConnection.alias)))


@app.post("/api/connections", response_model=ConnectionRead, status_code=status.HTTP_201_CREATED)
def create_connection(
    payload: ConnectionCreate, session: Session = Depends(get_session)
) -> AgentConnection:
    _get_agent_or_404(session, payload.parent_agent_id)
    _get_agent_or_404(session, payload.child_agent_id)
    connection = AgentConnection(**payload.model_dump())
    session.add(connection)
    return _commit_or_409(session, connection)


@app.patch("/api/connections/{connection_id}", response_model=ConnectionRead)
def update_connection(
    connection_id: UUID,
    payload: ConnectionUpdate,
    session: Session = Depends(get_session),
) -> AgentConnection:
    connection = _get_connection_or_404(session, connection_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(connection, key, value)
    return _commit_or_409(session, connection)


@app.delete("/api/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_connection(connection_id: UUID, session: Session = Depends(get_session)) -> Response:
    connection = _get_connection_or_404(session, connection_id)
    session.delete(connection)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/graph", response_model=AgentGraphResponse)
def get_graph(session: Session = Depends(get_session)) -> AgentGraphResponse:
    agents = list(session.scalars(select(Agent).order_by(Agent.is_root.desc(), Agent.name)))
    connections = list(session.scalars(select(AgentConnection).order_by(AgentConnection.alias)))
    return AgentGraphResponse(
        nodes=[
            GraphNode(
                id=agent.id,
                label=agent.name,
                description=agent.description,
                is_root=agent.is_root,
                is_enabled=agent.is_enabled,
                model_provider=agent.model_provider,
                model_name=agent.model_name,
            )
            for agent in agents
        ],
        edges=[
            GraphEdge(
                id=connection.id,
                source=connection.parent_agent_id,
                target=connection.child_agent_id,
                alias=connection.alias,
                description=connection.description,
                is_enabled=connection.is_enabled,
                memory_mode=connection.memory_mode,
            )
            for connection in connections
        ],
    )


@app.post("/api/runs", response_model=RunResult, status_code=status.HTTP_201_CREATED)
def run_agent(payload: RunCreate, session: Session = Depends(get_session)) -> RunResult:
    _get_agent_or_404(session, payload.root_agent_id)
    run, events = AgentRuntime(session).run(payload.root_agent_id, payload.input, payload.thread_id)
    return RunResult(
        run=run,
        events=[TraceEventRead.model_validate(event) for event in events],
    )


@app.get("/api/runs/{run_id}/events", response_model=list[TraceEventRead])
def list_run_events(run_id: UUID, session: Session = Depends(get_session)) -> list[TraceEvent]:
    return list(
        session.scalars(
            select(TraceEvent).where(TraceEvent.run_id == run_id).order_by(TraceEvent.created_at)
        )
    )


def _get_agent_or_404(session: Session, agent_id: UUID) -> Agent:
    agent = session.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


def _get_connection_or_404(session: Session, connection_id: UUID) -> AgentConnection:
    connection = session.get(AgentConnection, connection_id)
    if connection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")
    return connection


def _commit_or_409(session: Session, entity):
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Constraint violation") from exc
    session.refresh(entity)
    return entity
