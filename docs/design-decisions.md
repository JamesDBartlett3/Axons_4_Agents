# Design Decisions

This document explains the reasoning behind the architectural and technical choices made for the Claude Memory Graph System.

## Why a Graph Database?

### The Problem with Flat Files

Storing memories in markdown files is simple and human-readable, but has significant limitations:

1. **No native relationships**: Finding related memories requires text search, which misses semantic connections
2. **No traversal**: You can't ask "what memories are 2 hops away from this concept?"
3. **Scaling issues**: As memories grow, searching becomes slower
4. **No contradiction detection**: Hard to identify when new information conflicts with old

### Why Graphs Solve This

Graph databases store data as nodes and edges (relationships), which naturally models how memories connect:

```
(Memory A)--[:HAS_CONCEPT]-->(Concept: "authentication")
                                      ^
                                      |
                              [:HAS_CONCEPT]
                                      |
(Memory B)--[:HAS_CONCEPT]-->(Concept: "security")--[:RELATED_TO]-->(Concept: "authentication")
```

This allows queries like:
- "Find all memories related to 'authentication' within 2 relationship hops"
- "What decisions were informed by memories about 'security'?"
- "Which memories contradict each other?"

## Why Memgraph?

We evaluated several graph databases:

| Database | Pros | Cons |
|----------|------|------|
| **Neo4j** | Most mature, best tooling, huge community | JVM-based (500MB+ RAM), slower startup |
| **Memgraph** | C++ (fast, low memory), Cypher-compatible | Smaller community |
| **ArangoDB** | Multi-model | AQL less intuitive for graphs |
| **SurrealDB** | Modern, Rust-based | Very new, still maturing |
| **FalkorDB** | Extremely fast | Limited Cypher support |

### Decision: Memgraph

**Primary reasons:**

1. **Speed**: C++ implementation means faster queries and lower latency than JVM-based alternatives
2. **Low memory footprint**: ~100-200MB at idle vs 500MB+ for Neo4j
3. **Cypher compatibility**: Uses the same query language as Neo4j, so skills transfer and there's abundant documentation
4. **Fast startup**: ~1 second vs Neo4j's 10-30 seconds
5. **Extensibility**: MAGE library provides 60+ graph algorithms, and custom query modules can be written in Python/C++

**Trade-offs accepted:**
- Smaller community than Neo4j
- Fewer tutorials and examples
- Must run in WSL on Windows (no native Windows binary)

## Why WSL?

Memgraph doesn't have a native Windows installer. The options were:

1. **Docker**: Requires Docker Desktop, adds complexity
2. **WSL**: Ubuntu runs natively in WSL2, Memgraph installs normally
3. **Remote server**: Adds latency and infrastructure

### Decision: WSL2 with Ubuntu

- Already available on most Windows developer machines
- No additional software required beyond WSL itself
- Memgraph runs as a systemd service (standard Linux administration)
- Network is bridged, so localhost:7687 works from Windows

## Database Design: Why These Node Types?

### Core Nodes

| Node Type | Purpose |
|-----------|---------|
| **Memory** | The actual memory content - the fundamental unit |
| **Concept** | Abstract ideas that memories relate to (e.g., "authentication", "performance") |
| **Keyword** | Specific terms for exact matching (e.g., "OAuth", "Redis") |
| **Topic** | Broader subject areas (e.g., "Software Architecture", "User Preferences") |

**Rationale**: Concepts, keywords, and topics provide three levels of granularity for finding related memories:
- Keywords: exact term matching
- Concepts: semantic grouping
- Topics: high-level categorization

### Entity Nodes

| Node Type | Purpose |
|-----------|---------|
| **Entity** | People, projects, tools, technologies, organizations |
| **Source** | Where information came from (conversations, files, URLs) |

**Rationale**: Entities create natural hubs - many memories mention the same person or tool. Sources enable provenance tracking ("where did I learn this?").

### Intentional Nodes

| Node Type | Purpose |
|-----------|---------|
| **Decision** | Choices made and their rationale |
| **Goal** | User objectives (active, achieved, abandoned) |
| **Question** | Unresolved items, things to investigate |

**Rationale**: These capture the "why" and "what next" aspects of memory:
- Decisions can be traced back to the memories that informed them
- Goals can be linked to supporting memories
- Questions can be partially answered by multiple memories

### Contextual Nodes

| Node Type | Purpose |
|-----------|---------|
| **Context** | Projects, tasks, conversations, sessions |
| **Preference** | User likes/dislikes, working styles |
| **TemporalMarker** | Time periods, sequences, "before/after" |

**Rationale**: Context disambiguates - the same keyword might mean different things in different projects. Preferences accumulate over time. Temporal markers enable time-based queries.

### Meta Nodes

| Node Type | Purpose |
|-----------|---------|
| **Contradiction** | When new information conflicts with old |

**Rationale**: Explicit contradiction tracking prevents serving outdated information and enables resolution workflows.

## Hybrid Storage: Graph + Markdown

### The Design

- **Graph database**: Stores everything - full content, metadata, all relationships (source of truth)
- **Markdown directory**: Lightweight index listing all nodes (quick scanning at conversation start)

### Why Not Graph-Only?

The markdown directory serves a specific purpose: allowing Claude to quickly understand what exists without running complex queries. At the start of each conversation, scanning a text file is faster than querying every node type.

### Why Not Markdown-Only for Content?

Early design considered storing summaries in the graph and full content in markdown. This was rejected because:
1. Graph databases handle large text properties fine
2. Having content in the graph enables full-text search within Cypher
3. Single source of truth prevents sync issues

## Python Client Design

### Why neo4j Driver?

Memgraph speaks the Bolt protocol (same as Neo4j). Options were:

| Library | Pros | Cons |
|---------|------|------|
| **neo4j** (Python driver) | Lightweight, well-maintained, works with Memgraph | Name is confusing |
| **gqlalchemy** | Memgraph's official ORM | Heavier, more dependencies |
| **pymgclient** | Low-level C bindings | Requires compilation |

**Decision**: neo4j driver - lightest option that works.

### API Design: Data Classes + Client

The client uses:
- **Data classes** for type safety and IDE completion
- **MERGE for idempotency** - creating the same concept twice returns the existing one
- **Explicit relationship methods** - clear what connections are being made

```python
# Clear, explicit API
memory_id = client.create_memory(memory)
concept_id = client.create_concept(concept)
client.link_memory_to_concept(memory_id, concept_id, relevance=0.9)
```

### Convenience Function

`quick_store_memory()` provides a one-call interface for the common case:

```python
quick_store_memory(
    client,
    content="...",
    summary="...",
    concepts=["auth", "security"],
    keywords=["OAuth", "JWT"],
    topics=["Security"],
    entities=[("James", "person")]
)
```

## Auto-Start Design

### Requirements

1. Memgraph should be running whenever the user might need it
2. No manual intervention after Windows reboot
3. Minimal resource usage when idle

### Solution

1. **systemd in WSL**: `systemctl enable memgraph` makes it start when Ubuntu starts
2. **WSL auto-start**: Windows Task Scheduler runs `wsl -d Ubuntu -- sleep infinity` at boot
3. **sleep infinity**: Keeps WSL alive so systemd services remain running

This is the cleanest approach because:
- Uses standard Linux service management
- Uses standard Windows task scheduling
- No custom scripts or hacks
