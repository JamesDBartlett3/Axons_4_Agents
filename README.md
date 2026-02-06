# Axons for Agents

A graph-based memory system for AI agents that stores memories as nodes with rich relationships, enabling associative recall based on concepts, keywords, topics, and entities.

## Features

- **Graph-based Memory**: Store memories as interconnected nodes with relationships
- **Brain Plasticity**: Weighted connections that strengthen/weaken over time (Hebbian learning)
- **Multi-level Organization**: Concepts, keywords, topics, and entities
- **Associative Recall**: Find related memories through graph traversal
- **Contradiction Detection**: Track and resolve conflicting information
- **Decision Tracing**: Link decisions to the memories that informed them
- **Goal Tracking**: Monitor progress on objectives
- **Cross-Platform**: Works natively on Windows, macOS, and Linux

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/Axons_4_Agents.git
cd Axons_4_Agents

# Install dependencies
pip install -r requirements.txt
```

That's it! No database server setup required. KùzuDB is an embedded database that runs entirely within your Python process.

### Basic Usage

```python
from src.memory_client import MemoryGraphClient, quick_store_memory

# Create a client (database stored in ~/.axons_memory_db by default)
client = MemoryGraphClient()

# Initialize the schema (only needed once)
client.initialize_schema()

# Store a memory with associations
memory_id = quick_store_memory(
    client,
    content="The user prefers Python for data analysis tasks.",
    summary="User language preference",
    concepts=["programming", "data analysis"],
    keywords=["python", "preference"],
    topics=["Technology Preferences"],
    entities=[("User", "person"), ("Python", "technology")]
)

# Query memories by concept
python_memories = client.get_memories_by_concept("programming")

# Find related memories
related = client.get_related_memories(memory_id)

# Clean up
client.close()
```

### Custom Database Location

```python
# Store database in a specific location
client = MemoryGraphClient(db_path="/path/to/my/database")
```

### Run Tests

```bash
python src/test_memory_system.py
```

## Architecture

### Node Types

The system uses 13 different node types:

| Node | Purpose |
|------|---------|
| **Memory** | Core memory content with summary, confidence, and access tracking |
| **Concept** | Abstract ideas (e.g., "machine learning", "user experience") |
| **Keyword** | Specific terms for precise matching |
| **Topic** | Broad categories for organization |
| **Entity** | People, organizations, tools, technologies, places |
| **Source** | Information origin (conversation, file, URL, etc.) |
| **Decision** | Choices made with rationale and outcome |
| **Goal** | Objectives with status and priority |
| **Question** | Open items to be resolved |
| **Context** | Projects, tasks, sessions, domains |
| **Preference** | User likes/dislikes with strength |
| **TemporalMarker** | Time periods and sequences |
| **Contradiction** | Conflicting information to resolve |

### Relationships

Memories connect to other nodes through weighted relationships:
- `HAS_CONCEPT` (relevance), `HAS_KEYWORD`, `BELONGS_TO` (isPrimary)
- `MENTIONS` (role), `FROM_SOURCE` (excerpt), `IN_CONTEXT`
- `INFORMED` (decision), `SUPPORTS` (strength), `PARTIALLY_ANSWERS` (completeness)
- `RELATES_TO` (strength, relType) - memory-to-memory with synaptic-like weights
- `CONFLICTS_WITH`, `SUPERSEDES` (contradictions)

### Brain Plasticity

Relationship weights enable brain-like learning patterns:

```python
# Hebbian learning: memories accessed together strengthen their connection
client.apply_hebbian_learning([memory_id_1, memory_id_2, memory_id_3])

# Manual strengthening (synaptic potentiation)
client.strengthen_memory_link(memory_id_1, memory_id_2, amount=0.1)

# Weakening unused connections (synaptic depression)
client.weaken_memory_link(memory_id_1, memory_id_2, amount=0.1)

# Time-based decay of weak connections
client.decay_weak_connections(threshold=0.3, decay_amount=0.05)

# Prune near-zero connections (synaptic pruning)
client.prune_dead_connections(min_strength=0.01)

# Find strongly associated memories
strong = client.get_strongest_connections(memory_id, limit=10)

# Run maintenance cycle (decay + auto-prune)
client.run_maintenance_cycle()
```

### Tuneable Plasticity Configuration

All plasticity behavior is configurable via `PlasticityConfig`. All numeric values are 0-1 scale with 5 decimal precision.

```python
from memory_client import MemoryGraphClient, PlasticityConfig, Curve

# Create custom configuration
config = PlasticityConfig(
    # Master control (0=disabled, 1=normal)
    learning_rate=1.00000,

    # Context-specific amounts (each independent)
    strengthen_amount=0.10000,   # For explicit strengthen operations
    weaken_amount=0.10000,       # For explicit weaken operations
    hebbian_amount=0.05000,      # For co-access strengthening
    retrieval_amount=0.02000,    # For retrieval-induced changes
    decay_amount=0.05000,        # For time-based decay

    # Plasticity curve (applies to strengthen AND weaken symmetrically)
    curve=Curve.EXPONENTIAL,     # LINEAR, EXPONENTIAL, LOGARITHMIC
    curve_steepness=0.50000,     # 0.1=steep, 0.9=gentle

    # Decay settings
    decay_curve=Curve.EXPONENTIAL,
    decay_threshold=0.50000,     # Only decay connections below this
    decay_half_life=0.10000,     # 0.1 = 10 cycles to halve

    # Pruning
    prune_threshold=0.01000,     # Remove connections at or below this
    auto_prune=True,

    # Retrieval effects
    retrieval_strengthens=True,
    retrieval_weakens_competitors=False,

    # Hebbian learning
    hebbian_creates_connections=True,
    hebbian_initial_strength=0.30000,
)

# Use custom config
client = MemoryGraphClient(plasticity_config=config)

# Or use presets
client = MemoryGraphClient(plasticity_config=PlasticityConfig.aggressive_learning())
client = MemoryGraphClient(plasticity_config=PlasticityConfig.conservative_learning())
client = MemoryGraphClient(plasticity_config=PlasticityConfig.no_plasticity())
client = MemoryGraphClient(plasticity_config=PlasticityConfig.high_decay())

# Save/load config
client.save_plasticity_config("my_config.json")
client.load_plasticity_config("my_config.json")
```

See [Plasticity Configuration Guide](docs/plasticity-config.md) for full parameter reference.

## Why KùzuDB?

This project uses [KùzuDB](https://kuzudb.com/) as its graph database because:

1. **Zero Setup**: Install with `pip install kuzu` - no server, no Docker, no configuration
2. **Cross-Platform**: Native binaries for Windows, macOS, and Linux
3. **Embedded**: Runs in-process, data stored in a local directory
4. **Fast**: Written in C++ with excellent query performance
5. **Cypher Support**: Uses the familiar Cypher query language

## Documentation

- [Schema Details](docs/schema.md) - Full schema documentation
- [Design Decisions](docs/design-decisions.md) - Architectural rationale

## Requirements

- Python 3.8+
- kuzu >= 0.4.0

## License

MIT
