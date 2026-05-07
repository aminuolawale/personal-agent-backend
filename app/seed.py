from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Agent, AgentConnection, AgentTool


ROOT_PROMPT = """You are the Personal Planner.
Plan the user's request, delegate to attached worker planners when useful, and return a concise answer."""

HELLO_PROMPT = """You are the Hello World Worker.
Your only job is to use the hello_world builtin tool and return its result directly."""


def seed_defaults(session: Session) -> None:
    existing_root = session.scalar(select(Agent).where(Agent.slug == "personal-planner"))
    existing_worker = session.scalar(select(Agent).where(Agent.slug == "hello-world-worker"))

    root = existing_root or Agent(
        name="Personal Planner",
        slug="personal-planner",
        description="Root planner that delegates work to attached planner agents.",
        system_prompt=ROOT_PROMPT,
        model_provider="mock",
        model_name="mock-planner",
        is_root=True,
    )
    worker = existing_worker or Agent(
        name="Hello World Worker",
        slug="hello-world-worker",
        description="Default worker planner that returns Hello world.",
        system_prompt=HELLO_PROMPT,
        model_provider="mock",
        model_name="mock-hello-world",
    )

    session.add_all([root, worker])
    session.flush()

    connection = session.scalar(
        select(AgentConnection).where(
            AgentConnection.parent_agent_id == root.id,
            AgentConnection.child_agent_id == worker.id,
        )
    )
    if connection is None:
        session.add(
            AgentConnection(
                parent_agent_id=root.id,
                child_agent_id=worker.id,
                alias="ask_hello_world_worker",
                description="Ask the Hello World Worker to provide the default smoke-test response.",
                memory_mode="per_invocation",
            )
        )

    tool = session.scalar(
        select(AgentTool).where(AgentTool.agent_id == worker.id, AgentTool.name == "hello_world")
    )
    if tool is None:
        session.add(
            AgentTool(
                agent_id=worker.id,
                name="hello_world",
                description="Return the literal text Hello world.",
                kind="builtin",
                config={},
            )
        )

    session.commit()


def main() -> None:
    with SessionLocal() as session:
        seed_defaults(session)


if __name__ == "__main__":
    main()

