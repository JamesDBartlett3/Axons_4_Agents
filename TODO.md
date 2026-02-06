# TODO: MCP Server Implementation for Memory Graph System

## Overview

Transform the Memory Graph System into an MCP (Model Context Protocol) server so Claude Code can use memory operations as native tools.

**Goal**: When complete, Claude will be able to store, query, and manage memories directly through MCP tool calls, without needing to invoke Python scripts manually.

---

## Research Summary

### What is MCP?
- Open-source standard by Anthropic for connecting AI to external data/tools
- Uses JSON-RPC 2.0 for communication
- Claude Code acts as **host**, connects to MCP **servers**
- Servers expose **tools** (executable functions), **resources** (read-only data), and **prompts** (templates)

### Recommended Stack
- **Framework**: FastMCP (Python) - handles protocol complexity with simple decorators
- **Transport**: stdio for local development, HTTP for production
- **Language**: Python (matches existing memory_client.py)
- **Database**: KùzuDB (embedded, cross-platform)

---

## Implementation Plan

### Phase 1: Basic MCP Server Setup
**Estimated Complexity**: Low

- [ ] Install FastMCP: `pip install fastmcp`
- [ ] Create `kuzu_mcp_server.py` in `src/` directory
- [ ] Set up basic server structure with FastMCP
- [ ] Implement health check tool to verify connectivity
- [ ] Test with stdio transport locally

**Files to Create**:
- `src/kuzu_mcp_server.py` - Main MCP server

**Verification**:
```powershell
claude mcp add --transport stdio axons-memory -- python src/kuzu_mcp_server.py
claude mcp list  # Should show axons-memory
```

---

### Phase 2: Core Memory Tools
**Estimated Complexity**: Medium

Implement the primary memory operations as MCP tools:

- [ ] **`store_memory`** - Store a new memory with concepts/keywords/topics/entities
  - Input: content, summary, concepts[], keywords[], topics[], entities[], confidence
  - Output: memory_id
  - Wraps: `quick_store_memory()`

- [ ] **`search_memories`** - Text search across memories
  - Input: search_term, limit
  - Output: list of matching memories with summaries
  - Wraps: `search_memories()`

- [ ] **`get_memory`** - Retrieve a specific memory by ID
  - Input: memory_id
  - Output: full memory content and metadata
  - Wraps: `get_memory()`

- [ ] **`get_related_memories`** - Find memories within N hops
  - Input: memory_id, hops, limit
  - Output: list of related memories
  - Wraps: `get_related_memories()`

- [ ] **`query_by_concept`** - Get memories by concept name
  - Input: concept_name, limit
  - Output: list of memories
  - Wraps: `get_memories_by_concept()`

- [ ] **`query_by_keyword`** - Get memories by keyword
  - Input: keyword, limit
  - Output: list of memories
  - Wraps: `get_memories_by_keyword()`

- [ ] **`query_by_topic`** - Get memories by topic
  - Input: topic_name, limit
  - Output: list of memories
  - Wraps: `get_memories_by_topic()`

- [ ] **`query_by_entity`** - Get memories mentioning an entity
  - Input: entity_name, limit
  - Output: list of memories
  - Wraps: `get_memories_by_entity()`

---

### Phase 3: Goal and Question Tools
**Estimated Complexity**: Low

- [ ] **`create_goal`** - Create a new goal
  - Input: description, priority, target_date (optional)
  - Output: goal_id

- [ ] **`get_active_goals`** - List all active goals
  - Output: list of goals with status

- [ ] **`create_question`** - Create a new open question
  - Input: text
  - Output: question_id

- [ ] **`get_open_questions`** - List unanswered questions
  - Output: list of questions with status

- [ ] **`link_memory_to_goal`** - Associate memory with goal
  - Input: memory_id, goal_id, strength

- [ ] **`link_memory_to_question`** - Mark memory as partial answer
  - Input: memory_id, question_id, completeness

---

### Phase 4: Context and Preference Tools
**Estimated Complexity**: Low

- [ ] **`create_context`** - Create project/task context
  - Input: name, type, description
  - Output: context_id

- [ ] **`record_preference`** - Record a user preference
  - Input: category, preference, strength
  - Output: preference_id

- [ ] **`get_preferences`** - Get preferences by category
  - Input: category
  - Output: list of preferences

---

### Phase 5: Decision and Contradiction Tools
**Estimated Complexity**: Medium

- [ ] **`record_decision`** - Record a decision with rationale
  - Input: description, rationale, reversible
  - Output: decision_id

- [ ] **`get_decision_chain`** - Trace decisions
  - Input: decision_id
  - Output: chain of related decisions

- [ ] **`mark_contradiction`** - Flag conflicting memories
  - Input: description, memory_id_1, memory_id_2
  - Output: contradiction_id

- [ ] **`get_contradictions`** - List unresolved contradictions
  - Output: list of contradictions with conflicting memories

- [ ] **`resolve_contradiction`** - Resolve a contradiction
  - Input: contradiction_id, superseding_memory_id, resolution

---

### Phase 6: MCP Resources
**Estimated Complexity**: Low

Expose read-only data as MCP resources:

- [ ] **`memory://directory`** - Current node directory (markdown format)
  - Returns: directory.md content

- [ ] **`memory://stats`** - Database statistics
  - Returns: node counts by type

- [ ] **`memory://schema`** - Graph schema overview
  - Returns: list of node types and relationships

- [ ] **`memory://recent`** - Recently accessed memories
  - Returns: last 10 accessed memories

---

### Phase 7: Advanced Features
**Estimated Complexity**: High

- [ ] **`execute_cypher`** - Run arbitrary Cypher queries (with safety checks)
  - Input: query, parameters
  - Output: query results
  - Safety: Whitelist allowed operations, block destructive queries

- [ ] **`link_memories`** - Create relationship between memories
  - Input: memory_id_1, memory_id_2, strength, type

- [ ] **`bulk_store`** - Store multiple memories at once
  - Input: list of memory objects
  - Output: list of memory_ids

- [ ] **`export_subgraph`** - Export memories and relationships
  - Input: starting_memory_id, depth
  - Output: JSON graph structure

---

### Phase 8: Testing and Documentation
**Estimated Complexity**: Medium

- [ ] Create test suite for MCP server
- [ ] Test all tools with various inputs
- [ ] Test error handling (invalid IDs, connection failures)
- [ ] Document all tools in README
- [ ] Create example usage guide

---

### Phase 9: Claude Code Integration
**Estimated Complexity**: Low

- [ ] Test full workflow: store memory → query → retrieve
- [ ] Document configuration in README

**Installation Command**:
```powershell
claude mcp add --transport stdio axons-memory `
  --env AXONS_DB_PATH=C:\Users\James\.axons_memory_db `
  -- python C:\Users\James\GitHub\Axons_4_Agents\src\kuzu_mcp_server.py
```

---

## File Structure (After Implementation)

```
Axons_4_Agents/
├── README.md
├── TODO.md                      # This file
├── requirements.txt             # Python dependencies
├── docs/
│   ├── design-decisions.md
│   ├── schema.md
│   └── mcp-server-guide.md      # NEW: MCP-specific docs
└── src/
    ├── memory_client.py
    ├── kuzu_mcp_server.py       # NEW: MCP server
    ├── test_memory_system.py
    ├── test_mcp_server.py       # NEW: MCP tests
    └── directory.md
```

---

## Dependencies

```
# requirements.txt
kuzu>=0.4.0
fastmcp>=0.1.0
```

---

## Example MCP Server Structure (Reference)

```python
from fastmcp import FastMCP
from memory_client import MemoryGraphClient, quick_store_memory
import os

# Initialize MCP server
mcp = FastMCP("axons-memory")

# Initialize database client
db_path = os.environ.get("AXONS_DB_PATH", None)  # Uses default if not set
client = MemoryGraphClient(db_path=db_path)
client.initialize_schema()

@mcp.tool()
def store_memory(
    content: str,
    summary: str,
    concepts: list[str] = None,
    keywords: list[str] = None,
    topics: list[str] = None,
    entities: list[tuple[str, str]] = None,
    confidence: float = 1.0
) -> str:
    """Store a new memory with associated concepts, keywords, topics, and entities.

    Args:
        content: Full content of the memory
        summary: Brief one-line summary
        concepts: List of abstract concepts (e.g., ["authentication", "security"])
        keywords: List of specific terms (e.g., ["OAuth2", "JWT"])
        topics: List of broad categories (e.g., ["Software Architecture"])
        entities: List of (name, type) tuples (e.g., [("James", "person")])
        confidence: Certainty level from 0 to 1

    Returns:
        The UUID of the created memory
    """
    return quick_store_memory(
        client, content, summary, concepts, keywords, topics, entities, confidence
    )

@mcp.tool()
def search_memories(search_term: str, limit: int = 10) -> list[dict]:
    """Search memories by content or summary text.

    Args:
        search_term: Text to search for
        limit: Maximum results to return

    Returns:
        List of matching memories with id, summary, and created date
    """
    return client.search_memories(search_term, limit)

@mcp.resource("memory://directory")
def get_directory() -> str:
    """Get the current memory directory as markdown."""
    return client.export_directory_markdown()

# Run server
if __name__ == "__main__":
    mcp.run()
```

---

## Important Implementation Notes

1. **Never use `print()` in the MCP server** - breaks JSON-RPC protocol over stdio
2. **Use stderr for logging**: `import sys; print("debug", file=sys.stderr)`
3. **Type hints are required** - FastMCP uses them to generate input schemas
4. **Docstrings become tool descriptions** - Write clear, helpful descriptions
5. **Handle errors gracefully** - Return meaningful error messages, don't crash
6. **Test locally before registering** - Use `python kuzu_mcp_server.py` to check for syntax errors
7. **Environment variables for config** - Use `AXONS_DB_PATH` instead of hardcoding

---

## Success Criteria

When complete, the following should work:

1. Claude Code can list `axons-memory` in available MCP servers
2. I can say "store this as a memory" and Claude uses `store_memory` tool
3. I can say "what do you know about X" and Claude queries the graph
4. I can say "show me the memory directory" and Claude reads the resource
5. All tools have clear descriptions that help Claude understand when to use them
6. Errors are handled gracefully with helpful messages

---

## References

- [FastMCP Documentation](https://gofastmcp.com/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Claude Code MCP Guide](https://docs.anthropic.com/en/docs/claude-code/mcp)
- [KùzuDB Documentation](https://kuzudb.com/docs/)
- [MCP Specification](https://modelcontextprotocol.io/specification/2025-11-25)
