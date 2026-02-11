"""Shared pytest fixtures for the Axons memory graph system tests."""

import pytest

from axons import (
    MemoryGraphClient,
    Memory, Concept, Keyword, Topic, Entity, Source,
    Decision, Goal, Question, Context, Preference,
    TemporalMarker, Contradiction, Compartment,
    EntityType, SourceType, GoalStatus, QuestionStatus,
    ContextType, ContextStatus, TemporalType, ContradictionStatus,
    PlasticityConfig, Curve, Permeability,
    quick_store_memory,
)


@pytest.fixture
def client(tmp_path):
    """Fresh MemoryGraphClient with initialized schema, cleaned up after test."""
    db_path = str(tmp_path / "test_db")
    c = MemoryGraphClient(db_path=db_path)
    c.initialize_schema()
    yield c
    c.close()


@pytest.fixture
def populated_client(client):
    """Client pre-loaded with sample data for query/search tests.

    Creates:
    - 3 memories with concepts, keywords, topics, entities
    - 1 goal, 1 question, 1 decision, 1 context
    - Memory-to-memory links with plasticity
    """
    # Memory 1: about graph databases
    m1 = quick_store_memory(
        client,
        content="LadybugDB is an embedded graph database with Cypher support and cross-platform binaries.",
        summary="LadybugDB overview",
        concepts=["graph database", "embedded systems"],
        keywords=["ladybug", "cypher", "embedded"],
        topics=["Technology"],
        entities=[("LadybugDB", "technology")],
    )

    # Memory 2: about architecture decisions
    m2 = quick_store_memory(
        client,
        content="We chose an embedded database to avoid server setup complexity and enable cross-platform deployment.",
        summary="Architecture decision: embedded DB",
        concepts=["graph database", "architecture"],
        keywords=["embedded", "cross-platform"],
        topics=["Technology", "Architecture"],
        entities=[("LadybugDB", "technology")],
    )

    # Memory 3: about user preferences
    m3 = quick_store_memory(
        client,
        content="The user prefers lightweight tools that install via pip without Docker or server dependencies.",
        summary="User preference: lightweight tools",
        concepts=["user preferences", "tooling"],
        keywords=["pip", "lightweight"],
        topics=["Preferences"],
        entities=[("User", "person")],
    )

    # Link memories
    client.link_memories(m1, m2, strength=0.8, rel_type="context")
    client.link_memories(m2, m1, strength=0.8, rel_type="context")

    # Goal
    goal = Goal(description="Build a graph-based memory system for AI agents")
    goal_id = client.create_goal(goal)
    client.link_memory_to_goal(m1, goal_id, strength=0.9)

    # Question
    question = Question(text="What additional node types might be useful?")
    q_id = client.create_question(question)
    client.link_memory_to_question(m1, q_id, completeness=0.3)

    # Decision
    decision = Decision(
        description="Use LadybugDB for the memory database",
        rationale="Embedded, cross-platform, Cypher support",
    )
    d_id = client.create_decision(decision)
    client.link_memory_to_decision(m2, d_id)

    # Context
    context = Context(name="Axons Project", type=ContextType.PROJECT)
    ctx_id = client.create_context(context)
    client.link_memory_to_context(m1, ctx_id)
    client.link_memory_to_context(m2, ctx_id)

    # Store IDs for test access
    client._test_data = {
        "memory_ids": [m1, m2, m3],
        "goal_id": goal_id,
        "question_id": q_id,
        "decision_id": d_id,
        "context_id": ctx_id,
    }

    return client
