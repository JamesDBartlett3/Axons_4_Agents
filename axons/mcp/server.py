"""Axons MCP Server — exposes the memory graph system as MCP tools.

Usage:
    claude mcp add --transport stdio axons-memory -- python -m axons.mcp.server
"""

import os
from contextlib import asynccontextmanager
from typing import Optional

from fastmcp import FastMCP, Context

from axons import (
    MemoryGraphClient,
    Memory, Concept, Keyword, Topic, Entity, Source,
    Decision, Goal, Question, Context as AxonsContext, Preference,
    TemporalMarker, Contradiction, Compartment,
    EntityType, SourceType, GoalStatus, QuestionStatus,
    ContextType, ContextStatus, TemporalType,
    PlasticityConfig, Curve, Permeability,
    quick_store_memory,
)

# Global client reference, initialized during lifespan
_client: Optional[MemoryGraphClient] = None


@asynccontextmanager
async def lifespan(server):
    """Initialize and clean up the MemoryGraphClient."""
    global _client
    db_path = os.environ.get("AXONS_DB_PATH", None)
    _client = MemoryGraphClient(db_path=db_path)
    _client.initialize_schema()
    try:
        yield
    finally:
        _client.close()
        _client = None


mcp = FastMCP(
    "axons-memory",
    instructions=(
        "Axons is a graph-based memory system. Use these tools to store, recall, "
        "search, and manage memories with rich associations (concepts, keywords, "
        "topics, entities), brain-like plasticity, and data compartmentalization."
    ),
    lifespan=lifespan,
)


def _get_client() -> MemoryGraphClient:
    """Get the active client, raising if not initialized."""
    if _client is None:
        raise RuntimeError("Axons client not initialized — server lifespan not started")
    return _client


# ============================================================================
# MEMORY TOOLS
# ============================================================================


@mcp.tool
def store_memory(
    content: str,
    summary: str,
    concepts: list[str] | None = None,
    keywords: list[str] | None = None,
    topics: list[str] | None = None,
    entities: list[list[str]] | None = None,
    confidence: float = 1.0,
    compartment_id: str | None = None,
) -> dict:
    """Store a new memory with associated concepts, keywords, topics, and entities.

    Use this when the user explicitly asks to remember something, or when you
    observe important information worth retaining across conversations.

    Args:
        content: Full content of the memory.
        summary: Brief one-line summary.
        concepts: Abstract concepts (e.g. ["authentication", "security"]).
        keywords: Specific terms (e.g. ["OAuth2", "JWT"]).
        topics: Broad categories (e.g. ["Software Architecture"]).
        entities: List of [name, type] pairs. Types: person, organization,
                  project, tool, technology, place.
        confidence: Certainty level from 0 to 1.
        compartment_id: Optional compartment to store the memory in.

    Returns:
        Dict with the memory_id of the created memory.
    """
    client = _get_client()
    entity_tuples = [tuple(e) for e in entities] if entities else None
    memory_id = quick_store_memory(
        client,
        content=content,
        summary=summary,
        concepts=concepts,
        keywords=keywords,
        topics=topics,
        entities=entity_tuples,
        confidence=confidence,
        compartment_id=compartment_id,
    )
    return {"memory_id": memory_id}


@mcp.tool
def recall_memory(memory_id: str) -> dict:
    """Retrieve a specific memory by its ID.

    Also updates access tracking and applies retrieval-induced plasticity
    (strengthening connections to this memory).

    Args:
        memory_id: The UUID of the memory to recall.

    Returns:
        The memory's content, summary, metadata, or an error if not found.
    """
    client = _get_client()
    result = client.get_memory(memory_id)
    if result is None:
        return {"error": f"Memory {memory_id} not found"}
    return result


@mcp.tool
def search_memories(search_term: str, limit: int = 10) -> list[dict]:
    """Search memories by content or summary text.

    Uses full-text search when available, falls back to substring matching.

    Args:
        search_term: Text to search for.
        limit: Maximum number of results (default 10).

    Returns:
        List of matching memories with id, content, summary, and metadata.
    """
    client = _get_client()
    return client.search_memories(search_term, limit)


@mcp.tool
def get_related(memory_id: str, limit: int = 20) -> list[dict]:
    """Find memories related to a given memory through shared concepts and keywords.

    Args:
        memory_id: UUID of the memory to find relations for.
        limit: Maximum number of results.

    Returns:
        List of related memories.
    """
    client = _get_client()
    return client.get_related_memories(memory_id, limit=limit)


# ============================================================================
# CONCEPT / ASSOCIATION TOOLS
# ============================================================================


@mcp.tool
def create_concept(name: str, description: str = "") -> dict:
    """Create a new concept node for grouping related memories.

    Concepts represent abstract ideas (e.g. "machine learning", "user experience").
    If a concept with the same name already exists, returns the existing ID.

    Args:
        name: The concept name.
        description: Optional description.

    Returns:
        Dict with the concept_id.
    """
    client = _get_client()
    concept = Concept(name=name, description=description)
    return {"concept_id": client.create_concept(concept)}


@mcp.tool
def create_keyword(term: str) -> dict:
    """Create a keyword for precise term matching.

    Keywords are specific terms like "OAuth2", "Redis", "pip install".
    Deduplicates automatically.

    Args:
        term: The keyword term.

    Returns:
        Dict with the keyword_id.
    """
    client = _get_client()
    keyword = Keyword(term=term)
    return {"keyword_id": client.create_keyword(keyword)}


@mcp.tool
def create_topic(name: str, description: str = "") -> dict:
    """Create a topic for broad categorization of memories.

    Topics are high-level categories like "Software Architecture" or "User Preferences".

    Args:
        name: The topic name.
        description: Optional description.

    Returns:
        Dict with the topic_id.
    """
    client = _get_client()
    topic = Topic(name=name, description=description)
    return {"topic_id": client.create_topic(topic)}


@mcp.tool
def create_entity(name: str, entity_type: str, description: str = "") -> dict:
    """Create an entity node (person, organization, tool, technology, etc.).

    Args:
        name: Entity name (e.g. "Claude", "PostgreSQL").
        entity_type: One of: person, organization, project, tool, technology, place.
        description: Optional description.

    Returns:
        Dict with the entity_id.
    """
    client = _get_client()
    entity = Entity(name=name, type=EntityType(entity_type), description=description)
    return {"entity_id": client.create_entity(entity)}


@mcp.tool
def link_concept(memory_id: str, concept_name: str, relevance: float = 1.0) -> dict:
    """Link a memory to a concept (creates the concept if it doesn't exist).

    Args:
        memory_id: UUID of the memory.
        concept_name: Name of the concept to link.
        relevance: Relevance weight 0-1.

    Returns:
        Dict with the concept_id.
    """
    client = _get_client()
    concept = Concept(name=concept_name)
    concept_id = client.create_concept(concept)
    client.link_memory_to_concept(memory_id, concept_id, relevance)
    return {"concept_id": concept_id}


@mcp.tool
def get_memories_by_concept(concept_name: str, limit: int = 20) -> list[dict]:
    """Get all memories associated with a concept.

    Args:
        concept_name: The concept to search for.
        limit: Maximum results.

    Returns:
        List of memories linked to this concept.
    """
    client = _get_client()
    return client.get_memories_by_concept(concept_name, limit)


@mcp.tool
def get_memories_by_keyword(keyword: str, limit: int = 20) -> list[dict]:
    """Get all memories associated with a keyword.

    Args:
        keyword: The keyword term to search for.
        limit: Maximum results.

    Returns:
        List of memories linked to this keyword.
    """
    client = _get_client()
    return client.get_memories_by_keyword(keyword, limit)


@mcp.tool
def get_memories_by_topic(topic_name: str, limit: int = 20) -> list[dict]:
    """Get all memories belonging to a topic.

    Args:
        topic_name: The topic name to search for.
        limit: Maximum results.

    Returns:
        List of memories in this topic.
    """
    client = _get_client()
    return client.get_memories_by_topic(topic_name, limit)


@mcp.tool
def get_memories_by_entity(entity_name: str, limit: int = 20) -> list[dict]:
    """Get all memories mentioning an entity.

    Args:
        entity_name: The entity name to search for.
        limit: Maximum results.

    Returns:
        List of memories mentioning this entity.
    """
    client = _get_client()
    return client.get_memories_by_entity(entity_name, limit)


# ============================================================================
# PLASTICITY TOOLS
# ============================================================================


@mcp.tool
def strengthen_connection(memory_id_1: str, memory_id_2: str, amount: float | None = None) -> dict:
    """Strengthen the connection between two memories.

    Emulates synaptic potentiation. Use when two memories are relevant to each other.

    Args:
        memory_id_1: First memory UUID.
        memory_id_2: Second memory UUID.
        amount: Override for the strengthening amount. If None, uses plasticity config.

    Returns:
        Dict with the new connection strength.
    """
    client = _get_client()
    client.strengthen_memory_link(memory_id_1, memory_id_2, amount)
    strength = client.get_memory_link_strength(memory_id_1, memory_id_2)
    return {"strength": strength}


@mcp.tool
def weaken_connection(memory_id_1: str, memory_id_2: str, amount: float | None = None) -> dict:
    """Weaken the connection between two memories.

    Emulates synaptic depression. Use when memories are less relevant than previously thought.

    Args:
        memory_id_1: First memory UUID.
        memory_id_2: Second memory UUID.
        amount: Override for the weakening amount. If None, uses plasticity config.

    Returns:
        Dict with the new connection strength.
    """
    client = _get_client()
    client.weaken_memory_link(memory_id_1, memory_id_2, amount)
    strength = client.get_memory_link_strength(memory_id_1, memory_id_2)
    return {"strength": strength}


@mcp.tool
def run_maintenance() -> dict:
    """Run a maintenance cycle: decay weak connections and prune dead ones.

    Call periodically (e.g. at session end) to simulate time passing.
    Weak connections decay and near-zero connections are pruned.

    Returns:
        Dict with connection statistics after maintenance.
    """
    client = _get_client()
    client.run_maintenance_cycle()
    return client.get_connection_statistics()


@mcp.tool
def get_connection_stats() -> dict:
    """Get statistics about all memory connections.

    Returns:
        Dict with count, min, max, avg strength, distribution buckets,
        and counts of connections below decay threshold and pruning candidates.
    """
    client = _get_client()
    return client.get_connection_statistics()


@mcp.tool
def configure_plasticity(preset: str | None = None, learning_rate: float | None = None) -> dict:
    """Configure the plasticity behavior of the memory system.

    Args:
        preset: Optional preset name: "aggressive", "conservative", "no_plasticity", "high_decay".
                Overrides learning_rate if provided.
        learning_rate: Global learning rate multiplier (0=disabled, 1=normal).
                       Only used if preset is not provided.

    Returns:
        Dict with the current plasticity configuration summary.
    """
    client = _get_client()
    if preset:
        presets = {
            "aggressive": PlasticityConfig.aggressive_learning,
            "conservative": PlasticityConfig.conservative_learning,
            "no_plasticity": PlasticityConfig.no_plasticity,
            "high_decay": PlasticityConfig.high_decay,
        }
        factory = presets.get(preset)
        if factory is None:
            return {"error": f"Unknown preset '{preset}'. Options: {list(presets.keys())}"}
        client.set_plasticity_config(factory())
    elif learning_rate is not None:
        config = client.get_plasticity_config()
        config.learning_rate = learning_rate
        client.set_plasticity_config(config)

    config = client.get_plasticity_config()
    return {
        "learning_rate": config.learning_rate,
        "curve": config.curve.value,
        "decay_all": config.decay_all,
        "auto_prune": config.auto_prune,
        "retrieval_strengthens": config.retrieval_strengthens,
    }


# ============================================================================
# COMPARTMENTALIZATION TOOLS
# ============================================================================


@mcp.tool
def create_compartment(
    name: str,
    permeability: str = "open",
    allow_external_connections: bool = True,
    description: str = "",
) -> dict:
    """Create a compartment for memory isolation and data flow control.

    Compartments enable project/context isolation. Permeability controls data flow:
    - open: bidirectional (default)
    - closed: no data flow
    - osmotic_inward: can read external data, but doesn't leak
    - osmotic_outward: shares data out, but can't pull external data in

    Args:
        name: Compartment name.
        permeability: Data flow policy.
        allow_external_connections: Whether organic connections can form across boundaries.
        description: Optional description.

    Returns:
        Dict with the compartment_id.
    """
    client = _get_client()
    comp = Compartment(
        name=name,
        permeability=Permeability(permeability),
        allow_external_connections=allow_external_connections,
        description=description,
    )
    return {"compartment_id": client.create_compartment(comp)}


@mcp.tool
def add_to_compartment(memory_id: str, compartment_id: str) -> dict:
    """Add a memory to a compartment.

    A memory can belong to multiple compartments. Adding to one it's already
    in is a no-op.

    Args:
        memory_id: UUID of the memory.
        compartment_id: UUID of the compartment.

    Returns:
        Confirmation dict.
    """
    client = _get_client()
    client.add_memory_to_compartment(memory_id, compartment_id)
    return {"status": "ok"}


@mcp.tool
def set_active_compartment(compartment_id: str | None = None) -> dict:
    """Set the active compartment for new memories.

    All memories created after this call will be automatically added to
    this compartment. Pass null/None to clear.

    Args:
        compartment_id: Compartment UUID, or null to clear.

    Returns:
        Dict with the active compartment ID.
    """
    client = _get_client()
    client.set_active_compartment(compartment_id)
    return {"active_compartment": client.get_active_compartment()}


@mcp.tool
def set_permeability(
    compartment_id: str | None = None,
    memory_id: str | None = None,
    permeability: str = "open",
) -> dict:
    """Set the permeability of a compartment or memory.

    Controls data flow direction. Provide either compartment_id or memory_id.

    Args:
        compartment_id: UUID of compartment to update.
        memory_id: UUID of memory to update.
        permeability: One of: open, closed, osmotic_inward, osmotic_outward.

    Returns:
        Confirmation dict.
    """
    client = _get_client()
    perm = Permeability(permeability)
    if compartment_id:
        client.update_compartment(compartment_id, permeability=perm)
        return {"status": "ok", "target": "compartment", "permeability": permeability}
    elif memory_id:
        client.set_memory_permeability(memory_id, perm)
        return {"status": "ok", "target": "memory", "permeability": permeability}
    return {"error": "Provide either compartment_id or memory_id"}


@mcp.tool
def check_data_flow(from_memory_id: str, to_memory_id: str) -> dict:
    """Check if data can flow between two memories.

    Evaluates the full 5-layer permeability model:
    1. Source memory permeability
    2. Source compartment permeability
    3. Destination compartment permeability
    4. Destination memory permeability
    5. Connection permeability (if applicable)

    Args:
        from_memory_id: Source memory UUID.
        to_memory_id: Destination memory UUID.

    Returns:
        Dict with allowed (bool) and direction info.
    """
    client = _get_client()
    forward = client.can_data_flow(from_memory_id, to_memory_id)
    reverse = client.can_data_flow(to_memory_id, from_memory_id)
    return {
        "forward_allowed": forward,
        "reverse_allowed": reverse,
        "bidirectional": forward and reverse,
    }


# ============================================================================
# ENTRY POINT
# ============================================================================


if __name__ == "__main__":
    mcp.run()
