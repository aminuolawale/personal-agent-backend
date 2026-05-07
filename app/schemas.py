from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AgentBase(BaseModel):
    name: str
    slug: str
    description: str = ""
    system_prompt: str
    model_provider: str = "mock"
    model_name: str = "mock-planner"
    temperature: float = 0.2
    max_iterations: int = 8
    recursion_limit: int = 4
    is_root: bool = False
    is_enabled: bool = True


class AgentCreate(AgentBase):
    pass


class AgentUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    model_provider: str | None = None
    model_name: str | None = None
    temperature: float | None = None
    max_iterations: int | None = None
    recursion_limit: int | None = None
    is_root: bool | None = None
    is_enabled: bool | None = None


class AgentRead(AgentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class ConnectionBase(BaseModel):
    parent_agent_id: UUID
    child_agent_id: UUID
    alias: str
    description: str
    memory_mode: str = "per_invocation"
    is_enabled: bool = True


class ConnectionCreate(ConnectionBase):
    pass


class ConnectionUpdate(BaseModel):
    alias: str | None = None
    description: str | None = None
    memory_mode: str | None = None
    is_enabled: bool | None = None


class ConnectionRead(ConnectionBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class ToolBase(BaseModel):
    agent_id: UUID
    name: str
    description: str
    kind: str = "builtin"
    config: dict = Field(default_factory=dict)
    is_enabled: bool = True


class ToolCreate(ToolBase):
    pass


class ToolUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    kind: str | None = None
    config: dict | None = None
    is_enabled: bool | None = None


class ToolRead(ToolBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class GraphNode(BaseModel):
    id: UUID
    label: str
    description: str
    is_root: bool
    is_enabled: bool
    model_provider: str
    model_name: str


class GraphEdge(BaseModel):
    id: UUID
    source: UUID
    target: UUID
    alias: str
    description: str
    is_enabled: bool
    memory_mode: str


class AgentGraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class RunCreate(BaseModel):
    root_agent_id: UUID
    input: str
    thread_id: str = "default"


class RunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    root_agent_id: UUID
    thread_id: str
    status: str
    input: str
    output: str | None = None
    started_at: datetime
    finished_at: datetime | None = None


class RunResult(BaseModel):
    run: RunRead
    events: list["TraceEventRead"]


class TraceEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    run_id: UUID
    parent_event_id: UUID | None = None
    agent_id: UUID
    event_type: str
    payload: dict
    created_at: datetime


RunResult.model_rebuild()
