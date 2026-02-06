# Design Decisions

This document explains the reasoning behind the architectural and technical choices made for the Axons Memory Graph System.

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

## Why KùzuDB?

We evaluated several graph databases:

| Database | Pros | Cons |
|----------|------|------|
| **Neo4j** | Most mature, best tooling, huge community | JVM-based (500MB+ RAM), requires server setup |
| **Memgraph** | C++ (fast, low memory), Cypher-compatible | Requires WSL on Windows, no macOS support |
| **ArangoDB** | Multi-model | AQL less intuitive for graphs, server required |
| **SurrealDB** | Modern, Rust-based | Very new, still maturing |
| **KùzuDB** | Embedded, cross-platform, pip install | Smaller community |

### Decision: KùzuDB

**Primary reasons:**

1. **Zero Setup**: Just `pip install kuzu` - no server, no Docker, no WSL, no configuration
2. **Cross-Platform**: Native binaries for Windows, macOS, and Linux without any workarounds
3. **Embedded**: Runs in-process like SQLite, data stored in a local directory
4. **Speed**: C++ implementation means fast queries and low memory usage
5. **Cypher Support**: Uses a Cypher-like query language, so existing knowledge transfers
6. **Lightweight**: Small footprint, no background processes to manage

**Trade-offs accepted:**
- Smaller community than Neo4j
- Fewer advanced features than enterprise databases
- Some Cypher syntax differences (minor)

### Previous Choice: Memgraph (Deprecated)

We previously used Memgraph, which required:
- WSL2 on Windows (doesn't work on macOS)
- systemd service management
- Windows Task Scheduler for auto-start
- Multiple configuration steps

This created a 9-step setup process and platform lock-in. KùzuDB eliminates all of this complexity.

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

### Why KùzuDB's Native Python Bindings?

KùzuDB provides native Python bindings via pip:

| Library | Pros | Cons |
|---------|------|------|
| **kuzu** (official) | Native, lightweight, well-maintained | Name matches database |

**Decision**: Use the official kuzu package - it's the only option and works well.

### API Design: Data Classes + Client

The client uses:
- **Data classes** for type safety and IDE completion
- **Check-then-create for idempotency** - creating the same concept twice returns the existing one
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

## Embedded Database Benefits

### No Auto-Start Needed

Unlike server-based databases, KùzuDB:
- Runs in your Python process
- Starts automatically when you create a client
- Stops when your program ends
- No background services to manage

### Data Persistence

KùzuDB stores data in a directory you specify:
- Default: `~/.axons_memory_db`
- Custom: Pass `db_path` to `MemoryGraphClient`

Data persists between sessions automatically.

### Cross-Platform Consistency

The same code works identically on:
- Windows
- macOS
- Linux

No platform-specific setup or workarounds required.
