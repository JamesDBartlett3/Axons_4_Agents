"""Integration tests for the Axons MCP server.

Tests the MCP tools by calling them directly (they're regular Python functions
that use the global _client). This validates the tool logic and argument handling
without requiring the full MCP protocol transport.
"""

import pytest

import axons.mcp.server as server_module
from axons.mcp import server as srv
from axons import MemoryGraphClient


@pytest.fixture
def mcp_client(tmp_path):
    """Initialize the MCP server's global client for testing."""
    db_path = str(tmp_path / "mcp_test_db")
    client = MemoryGraphClient(db_path=db_path)
    client.initialize_schema()
    server_module._client = client
    yield client
    client.close()
    server_module._client = None


# Direct references to tool functions for testing
_tools = {
    "store_memory": srv.store_memory,
    "recall_memory": srv.recall_memory,
    "search_memories": srv.search_memories,
    "get_related": srv.get_related,
    "create_concept": srv.create_concept,
    "create_keyword": srv.create_keyword,
    "create_topic": srv.create_topic,
    "create_entity": srv.create_entity,
    "link_concept": srv.link_concept,
    "get_memories_by_concept": srv.get_memories_by_concept,
    "get_memories_by_keyword": srv.get_memories_by_keyword,
    "get_memories_by_topic": srv.get_memories_by_topic,
    "get_memories_by_entity": srv.get_memories_by_entity,
    "strengthen_connection": srv.strengthen_connection,
    "weaken_connection": srv.weaken_connection,
    "run_maintenance": srv.run_maintenance,
    "get_connection_stats": srv.get_connection_stats,
    "configure_plasticity": srv.configure_plasticity,
    "create_compartment": srv.create_compartment,
    "add_to_compartment": srv.add_to_compartment,
    "set_active_compartment": srv.set_active_compartment,
    "set_permeability": srv.set_permeability,
    "check_data_flow": srv.check_data_flow,
}


def _call(tool_name, args=None):
    """Call an MCP tool function directly by name."""
    tool = _tools[tool_name]
    fn = tool.fn if hasattr(tool, 'fn') else tool
    return fn(**(args or {}))


# ============================================================================
# SERVER SETUP
# ============================================================================


class TestServerSetup:
    def test_server_has_all_tools(self):
        """All expected tools are importable."""
        assert len(_tools) == 23

    def test_client_not_initialized_raises(self):
        """Calling tools without initialized client raises RuntimeError."""
        old = server_module._client
        server_module._client = None
        try:
            with pytest.raises(RuntimeError, match="not initialized"):
                _call("search_memories", {"search_term": "test"})
        finally:
            server_module._client = old


# ============================================================================
# MEMORY TOOLS
# ============================================================================


class TestMemoryTools:
    def test_store_and_recall(self, mcp_client):
        result = _call("store_memory", {
            "content": "Python is great for AI.",
            "summary": "Python for AI",
            "concepts": ["programming", "AI"],
            "keywords": ["python"],
            "entities": [["Python", "technology"]],
            "confidence": 0.95,
        })
        assert "memory_id" in result
        mid = result["memory_id"]

        recalled = _call("recall_memory", {"memory_id": mid})
        assert recalled["summary"] == "Python for AI"
        assert recalled["confidence"] == 0.95

    def test_search_memories(self, mcp_client):
        _call("store_memory", {
            "content": "LadybugDB is an embedded graph database.",
            "summary": "LadybugDB overview",
        })
        results = _call("search_memories", {"search_term": "LadybugDB"})
        assert len(results) >= 1

    def test_recall_nonexistent(self, mcp_client):
        result = _call("recall_memory", {"memory_id": "nonexistent-id"})
        assert "error" in result

    def test_get_related(self, mcp_client):
        r1 = _call("store_memory", {
            "content": "Redis caching", "summary": "Redis",
            "concepts": ["caching"],
        })
        r2 = _call("store_memory", {
            "content": "Memcached caching", "summary": "Memcached",
            "concepts": ["caching"],
        })
        related = _call("get_related", {"memory_id": r1["memory_id"]})
        assert any("Memcached" in str(r) for r in related)

    def test_store_with_compartment(self, mcp_client):
        comp = _call("create_compartment", {"name": "StoreComp"})
        result = _call("store_memory", {
            "content": "Compartmentalized memory", "summary": "In compartment",
            "compartment_id": comp["compartment_id"],
        })
        assert "memory_id" in result


# ============================================================================
# CONCEPT / ASSOCIATION TOOLS
# ============================================================================


class TestAssociationTools:
    def test_create_concept(self, mcp_client):
        result = _call("create_concept", {"name": "testing", "description": "QA"})
        assert "concept_id" in result

    def test_create_keyword(self, mcp_client):
        result = _call("create_keyword", {"term": "pytest"})
        assert "keyword_id" in result

    def test_create_topic(self, mcp_client):
        result = _call("create_topic", {"name": "Software QA"})
        assert "topic_id" in result

    def test_create_entity(self, mcp_client):
        result = _call("create_entity", {"name": "Claude", "entity_type": "tool"})
        assert "entity_id" in result

    def test_link_concept_and_query(self, mcp_client):
        r = _call("store_memory", {"content": "Linkable", "summary": "Linkable"})
        _call("link_concept", {"memory_id": r["memory_id"], "concept_name": "linked_test"})
        results = _call("get_memories_by_concept", {"concept_name": "linked_test"})
        assert len(results) >= 1

    def test_get_memories_by_keyword(self, mcp_client):
        _call("store_memory", {
            "content": "KW test", "summary": "KW",
            "keywords": ["mcp_kw_unique"],
        })
        results = _call("get_memories_by_keyword", {"keyword": "mcp_kw_unique"})
        assert len(results) >= 1

    def test_get_memories_by_topic(self, mcp_client):
        _call("store_memory", {
            "content": "Topic test", "summary": "Topic",
            "topics": ["MCP_Topic_Unique"],
        })
        results = _call("get_memories_by_topic", {"topic_name": "MCP_Topic_Unique"})
        assert len(results) >= 1

    def test_get_memories_by_entity(self, mcp_client):
        _call("store_memory", {
            "content": "Entity test", "summary": "Entity",
            "entities": [["TestBot", "tool"]],
        })
        results = _call("get_memories_by_entity", {"entity_name": "TestBot"})
        assert len(results) >= 1


# ============================================================================
# PLASTICITY TOOLS
# ============================================================================


class TestPlasticityTools:
    def test_strengthen_and_weaken(self, mcp_client):
        r1 = _call("store_memory", {"content": "A", "summary": "A"})
        r2 = _call("store_memory", {"content": "B", "summary": "B"})
        mcp_client.link_memories(r1["memory_id"], r2["memory_id"], strength=0.5)

        result = _call("strengthen_connection", {
            "memory_id_1": r1["memory_id"],
            "memory_id_2": r2["memory_id"],
        })
        assert result["strength"] > 0.5

        result = _call("weaken_connection", {
            "memory_id_1": r1["memory_id"],
            "memory_id_2": r2["memory_id"],
        })
        assert result["strength"] < 0.7

    def test_run_maintenance(self, mcp_client):
        result = _call("run_maintenance")
        assert "count" in result

    def test_get_connection_stats(self, mcp_client):
        result = _call("get_connection_stats")
        assert "count" in result

    def test_configure_preset(self, mcp_client):
        result = _call("configure_plasticity", {"preset": "aggressive"})
        assert result["learning_rate"] == 1.0

    def test_configure_learning_rate(self, mcp_client):
        result = _call("configure_plasticity", {"learning_rate": 0.42})
        assert result["learning_rate"] == 0.42

    def test_configure_invalid_preset(self, mcp_client):
        result = _call("configure_plasticity", {"preset": "nonexistent"})
        assert "error" in result


# ============================================================================
# COMPARTMENTALIZATION TOOLS
# ============================================================================


class TestCompartmentTools:
    def test_create_compartment(self, mcp_client):
        result = _call("create_compartment", {
            "name": "Secure",
            "permeability": "osmotic_inward",
            "allow_external_connections": False,
        })
        assert "compartment_id" in result

    def test_add_to_compartment(self, mcp_client):
        comp = _call("create_compartment", {"name": "AddTest"})
        mem = _call("store_memory", {"content": "test", "summary": "test"})
        result = _call("add_to_compartment", {
            "memory_id": mem["memory_id"],
            "compartment_id": comp["compartment_id"],
        })
        assert result["status"] == "ok"

    def test_set_active_compartment(self, mcp_client):
        comp = _call("create_compartment", {"name": "Active"})
        result = _call("set_active_compartment", {
            "compartment_id": comp["compartment_id"],
        })
        assert result["active_compartment"] == comp["compartment_id"]
        # Clear
        _call("set_active_compartment", {})

    def test_set_permeability_compartment(self, mcp_client):
        comp = _call("create_compartment", {"name": "PermTest"})
        result = _call("set_permeability", {
            "compartment_id": comp["compartment_id"],
            "permeability": "closed",
        })
        assert result["permeability"] == "closed"

    def test_set_permeability_memory(self, mcp_client):
        mem = _call("store_memory", {"content": "test", "summary": "test"})
        result = _call("set_permeability", {
            "memory_id": mem["memory_id"],
            "permeability": "osmotic_outward",
        })
        assert result["target"] == "memory"

    def test_set_permeability_no_target(self, mcp_client):
        result = _call("set_permeability", {"permeability": "closed"})
        assert "error" in result

    def test_check_data_flow(self, mcp_client):
        comp = _call("create_compartment", {"name": "Sealed", "permeability": "closed"})
        m1 = _call("store_memory", {"content": "inside", "summary": "inside"})
        m2 = _call("store_memory", {"content": "outside", "summary": "outside"})
        _call("add_to_compartment", {
            "memory_id": m1["memory_id"],
            "compartment_id": comp["compartment_id"],
        })
        result = _call("check_data_flow", {
            "from_memory_id": m1["memory_id"],
            "to_memory_id": m2["memory_id"],
        })
        assert result["forward_allowed"] is False
        assert result["bidirectional"] is False


# ============================================================================
# END-TO-END
# ============================================================================


class TestEndToEnd:
    def test_full_workflow(self, mcp_client):
        """Store -> recall -> search -> relate."""
        # Store
        r = _call("store_memory", {
            "content": "The Axons project uses LadybugDB for graph storage.",
            "summary": "Axons uses LadybugDB",
            "concepts": ["graph database"],
            "keywords": ["axons", "ladybug"],
        })
        mid = r["memory_id"]

        # Recall
        recalled = _call("recall_memory", {"memory_id": mid})
        assert "LadybugDB" in recalled["content"]

        # Search
        found = _call("search_memories", {"search_term": "Axons"})
        assert any("LadybugDB" in str(f) for f in found)

        # Store related
        r2 = _call("store_memory", {
            "content": "LadybugDB supports Cypher and FTS.",
            "summary": "LadybugDB features",
            "concepts": ["graph database"],
        })

        # Get related
        related = _call("get_related", {"memory_id": mid})
        assert len(related) >= 1
