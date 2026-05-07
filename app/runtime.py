from datetime import UTC, datetime
from typing import Annotated, TypedDict
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Agent, AgentConnection, AgentRun, AgentTool, TraceEvent


class PlannerState(TypedDict):
    messages: Annotated[list, add_messages]
    active_agent_id: str
    run_id: str
    thread_id: str
    depth: int


class AgentRuntime:
    def __init__(self, session: Session):
        self.session = session

    def run(self, root_agent_id: UUID, user_input: str, thread_id: str) -> tuple[AgentRun, list[TraceEvent]]:
        run = AgentRun(
            root_agent_id=root_agent_id,
            thread_id=thread_id,
            status="running",
            input=user_input,
        )
        self.session.add(run)
        self.session.flush()

        try:
            graph = self._compile_agent()
            result = graph.invoke(
                {
                    "messages": [{"role": "user", "content": user_input}],
                    "active_agent_id": str(root_agent_id),
                    "run_id": str(run.id),
                    "thread_id": thread_id,
                    "depth": 0,
                },
                config={"configurable": {"thread_id": thread_id}},
            )
            output = result["messages"][-1].content
            run.output = output
            run.status = "succeeded"
            run.finished_at = datetime.now(UTC)
        except Exception as exc:
            run.status = "failed"
            run.output = str(exc)
            run.finished_at = datetime.now(UTC)
            self._trace(run.id, root_agent_id, "error", {"message": str(exc)})

        self.session.commit()
        events = list(
            self.session.scalars(
                select(TraceEvent)
                .where(TraceEvent.run_id == run.id)
                .order_by(TraceEvent.created_at, TraceEvent.id)
            )
        )
        return run, events

    def _compile_agent(self):
        graph = StateGraph(PlannerState)
        graph.add_node("planner", self._planner_node)
        graph.add_edge(START, "planner")
        graph.add_edge("planner", END)
        return graph.compile()

    def _planner_node(self, state: PlannerState) -> dict:
        agent_id = UUID(state["active_agent_id"])
        run_id = UUID(state["run_id"])
        depth = state["depth"]
        user_text = self._last_user_text(state["messages"])
        agent = self._load_agent(agent_id)

        if not agent.is_enabled:
            raise RuntimeError(f"Agent {agent.name} is disabled")
        if depth > agent.recursion_limit:
            raise RuntimeError(f"Recursion limit exceeded for {agent.name}")

        self._trace(run_id, agent.id, "planner_started", {"agent": agent.name, "depth": depth})

        output = self._invoke_builtin_tool(agent, run_id)
        if output is None:
            output = self._delegate_to_child(agent, run_id, user_text, state["thread_id"], depth)
        if output is None:
            output = self._direct_response(agent, user_text)

        self._trace(run_id, agent.id, "planner_finished", {"agent": agent.name, "output": output})
        return {"messages": [{"role": "assistant", "content": output}]}

    def _load_agent(self, agent_id: UUID) -> Agent:
        agent = self.session.scalar(
            select(Agent)
            .where(Agent.id == agent_id)
            .options(
                selectinload(Agent.tools),
                selectinload(Agent.child_connections).selectinload(AgentConnection.child_agent),
            )
        )
        if agent is None:
            raise RuntimeError(f"Agent {agent_id} was not found")
        return agent

    def _invoke_builtin_tool(self, agent: Agent, run_id: UUID) -> str | None:
        enabled_tools = [tool for tool in agent.tools if tool.is_enabled]
        hello_tool = next((tool for tool in enabled_tools if tool.name == "hello_world"), None)
        if hello_tool is None:
            return None

        self._trace(
            run_id,
            agent.id,
            "tool_call_started",
            {"tool": hello_tool.name, "description": hello_tool.description},
        )
        result = "Hello world"
        self._trace(run_id, agent.id, "tool_call_finished", {"tool": hello_tool.name, "output": result})
        return result

    def _delegate_to_child(
        self,
        agent: Agent,
        run_id: UUID,
        task: str,
        thread_id: str,
        depth: int,
    ) -> str | None:
        enabled_connections = [
            connection
            for connection in agent.child_connections
            if connection.is_enabled and connection.child_agent.is_enabled
        ]
        if not enabled_connections:
            return None

        connection = enabled_connections[0]
        child = connection.child_agent
        self._trace(
            run_id,
            agent.id,
            "tool_call_started",
            {
                "tool": connection.alias,
                "child_agent_id": str(child.id),
                "task": task,
                "memory_mode": connection.memory_mode,
            },
        )
        self._trace(run_id, child.id, "worker_started", {"agent": child.name, "depth": depth + 1})

        graph = self._compile_agent()
        result = graph.invoke(
            {
                "messages": [{"role": "user", "content": task}],
                "active_agent_id": str(child.id),
                "run_id": str(run_id),
                "thread_id": thread_id,
                "depth": depth + 1,
            },
            config={"configurable": {"thread_id": thread_id}},
        )
        output = result["messages"][-1].content

        self._trace(run_id, child.id, "worker_finished", {"agent": child.name, "output": output})
        self._trace(run_id, agent.id, "tool_call_finished", {"tool": connection.alias, "output": output})
        return output

    def _direct_response(self, agent: Agent, user_text: str) -> str:
        if agent.model_provider == "mock":
            return (
                f"{agent.name} received: {user_text}. "
                "No enabled builtin tools or child planners were available."
            )
        return (
            f"{agent.name} is configured for provider '{agent.model_provider}', "
            "but this runtime only implements the mock execution path so far."
        )

    def _trace(self, run_id: UUID, agent_id: UUID, event_type: str, payload: dict) -> None:
        self.session.add(
            TraceEvent(
                run_id=run_id,
                agent_id=agent_id,
                event_type=event_type,
                payload=payload,
            )
        )
        self.session.flush()

    @staticmethod
    def _last_user_text(messages: list) -> str:
        for message in reversed(messages):
            if isinstance(message, dict) and message.get("role") == "user":
                return str(message.get("content", ""))
            if getattr(message, "type", None) == "human":
                return str(message.content)
        return ""

