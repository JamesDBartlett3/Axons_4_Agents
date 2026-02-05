# Axons for Agents

A graph-based memory system for AI agents, using Memgraph as the backend database. This system stores memories as nodes with rich relationships between them, enabling associative recall based on shared concepts, keywords, topics, entities, and more.

**MCP Support**: This system is being enhanced to support the Model Context Protocol (MCP), allowing AI assistants to interact with memories through native tool calls.

## Table of Contents

1. [Overview](#overview)
2. [Design Decisions](./docs/design-decisions.md)
3. [Database Schema](./docs/schema.md)
4. [Infrastructure](./docs/infrastructure.md)
5. [Setup Instructions](./docs/setup-instructions.md)
6. [Usage Guide](./docs/usage-guide.md)

## Overview

### The Problem

Storing AI agent memories in flat markdown files works for simple recall, but fails when you need to:
- Find memories related to a specific concept across multiple topics
- Trace the reasoning chain behind a decision
- Identify contradictions between old and new information
- Discover connections between seemingly unrelated memories

### The Solution

A graph database where:
- **Memories** are stored as nodes with full content
- **Relationships** connect memories to concepts, keywords, topics, entities, and each other
- **Queries** can traverse the graph to find related information within N hops
- **A markdown directory** provides a quick index of all nodes for scanning at conversation start

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Host Machine                            │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Python Client (memory_client.py)                   │    │
│  │  - Connects via Bolt protocol (localhost:7687)      │    │
│  │  - Creates/queries memories and relationships       │    │
│  │  - Exports directory.md for quick scanning          │    │
│  └─────────────────────────────────────────────────────┘    │
│                            │                                │
│                     Bolt Protocol                           │
│                            │                                │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Memgraph Database (WSL2/Docker/Native)             │    │
│  │  ┌───────────────────────────────────────────────┐  │    │
│  │  │  Memgraph                                     │  │    │
│  │  │  - Listens on port 7687                       │  │    │
│  │  │  - In-memory with WAL persistence             │  │    │
│  │  └───────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

If you just want to get up and running, see [Setup Instructions](./docs/setup-instructions.md).

## File Structure

```
Axons_4_Agents/
├── README.md                 # This file
├── TODO.md                   # MCP implementation roadmap
├── docs/
│   ├── design-decisions.md   # Why we made the choices we did
│   ├── schema.md             # Database schema documentation
│   ├── infrastructure.md     # Infrastructure details
│   ├── setup-instructions.md # Step-by-step setup guide
│   └── usage-guide.md        # How to use the system
└── src/
    ├── schema.cypher         # Database schema initialization
    ├── memory_client.py      # Python client library
    ├── test_memory_system.py # Test suite
    └── directory.md          # Memory graph directory index
```

## Requirements

- Python 3.10+
- Memgraph (via WSL2, Docker, or native installation)
- ~200MB RAM for Memgraph at idle (scales with data)

## License

This project is provided as-is for personal use.
