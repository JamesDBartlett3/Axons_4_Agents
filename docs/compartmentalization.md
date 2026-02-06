# Compartmentalization Guide

This document describes the compartmentalization feature for isolating memories and controlling data flow between them.

## Overview

Compartmentalization provides two independent controls:

1. **Connection Formation**: Whether new organic connections can form between memories across compartment boundaries
2. **Query Traversal (Permeability)**: Whether existing connections can be traversed during queries, and in which direction

These are separate axes - you can allow connections to form but restrict traversal, or vice versa.

## Concepts

### Compartments

A compartment is a named boundary that groups memories together. Each compartment has:

- **name**: Human-readable identifier
- **permeability**: Controls data flow direction (see below)
- **allow_external_connections**: Whether organic connections can form to memories outside this compartment

**Overlapping Compartments**: A memory can belong to multiple compartments simultaneously. When this happens, fail-safe logic applies - ANY compartment that blocks an operation will block it, regardless of what other compartments allow.

### Permeability

Permeability controls data flow direction through compartment boundaries. Think of it from the perspective of queries trying to retrieve data:

| Permeability | Allows Inward | Allows Outward | Use Case |
|--------------|---------------|----------------|----------|
| `OPEN` | Yes | Yes | Default - no restrictions |
| `CLOSED` | No | No | Complete isolation |
| `OSMOTIC_INWARD` | Yes | No | Can read external data, but doesn't leak |
| `OSMOTIC_OUTWARD` | No | Yes | Shares data out, but isn't influenced by external |

**Data flow direction**:
- **Inward**: Data flowing INTO the compartment (the compartment can retrieve external data)
- **Outward**: Data flowing OUT OF the compartment (external queries can retrieve data from inside)

### Multi-Layer Check (Fail-Safe)

When querying data across memories, multiple layers are checked:

1. **Source memory**: Must allow OUTWARD flow
2. **ALL source compartments**: Each must allow OUTWARD flow
3. **ALL destination compartments**: Each must allow INWARD flow
4. **Destination memory**: Must allow INWARD flow
5. **Connection**: Must allow this direction (if set)

**Fail-safe logic**: ANY layer that blocks will block the entire data flow. If a memory belongs to multiple compartments, ALL of them must allow the flow direction.

This provides fine-grained control at multiple levels:
- **Memory-level**: Individual memories can restrict their own visibility
- **Compartment-level**: Groups of memories share a common policy (overlapping allowed)
- **Connection-level**: Specific relationships can have custom rules

**Example**: If a memory is in both "Public" (OPEN) and "Restricted" (OSMOTIC_INWARD) compartments, it cannot leak data out because the Restricted compartment blocks outward flow.

## Quick Start

### Creating a Secure Compartment

```python
from memory_client import MemoryGraphClient, Compartment, Permeability

client = MemoryGraphClient()
client.initialize_schema()

# Create a compartment that can read external data but doesn't leak
secure = Compartment(
    name="Project Q",
    permeability=Permeability.OSMOTIC_INWARD,
    allow_external_connections=False  # No organic links to outside
)
compartment_id = client.create_compartment(secure)
```

### Working with Active Compartments

```python
# Set active compartment - all new memories go here
client.set_active_compartment(compartment_id)

# These memories are automatically in Project Q
memory1 = quick_store_memory(client, content="Secret data", summary="Secret")
memory2 = quick_store_memory(client, content="More secrets", summary="Secret 2")

# Clear active compartment
client.set_active_compartment(None)

# This memory is global (no compartment)
global_memory = quick_store_memory(client, content="Public info", summary="Public")
```

### Explicit Compartment Assignment

```python
# Create memory in specific compartment
memory_id = quick_store_memory(
    client,
    content="Project data",
    summary="Project",
    compartment_id=compartment_id
)

# Or assign after creation
client.add_memory_to_compartment(memory_id, compartment_id)

# Remove from specific compartment
client.remove_memory_from_compartment(memory_id, compartment_id)

# Remove from ALL compartments (make global)
client.remove_memory_from_compartment(memory_id)
```

### Overlapping Compartments

A memory can belong to multiple compartments simultaneously:

```python
# Add memory to multiple compartments
client.add_memory_to_compartment(memory_id, project_compartment_id)
client.add_memory_to_compartment(memory_id, security_compartment_id)

# Get all compartments for a memory
compartments = client.get_memory_compartments(memory_id)
for comp in compartments:
    print(f"  {comp['name']}: {comp['permeability']}")

# Remove from just one compartment
client.remove_memory_from_compartment(memory_id, project_compartment_id)
```

**Fail-safe behavior**: When a memory is in multiple compartments:
- **Connection formation**: Allowed if memories share ANY compartment, OR if ALL compartments allow external connections
- **Data flow**: Blocked if ANY compartment blocks the flow direction

```python
# Example: Memory in both OPEN and OSMOTIC_INWARD compartments
# Result: Cannot leak data out (OSMOTIC_INWARD blocks outward flow)
open_comp = client.create_compartment(Compartment(name="Open", permeability=Permeability.OPEN))
secure_comp = client.create_compartment(Compartment(name="Secure", permeability=Permeability.OSMOTIC_INWARD))

client.add_memory_to_compartment(mem_id, open_comp)
client.add_memory_to_compartment(mem_id, secure_comp)

# This memory can receive data (both allow inward)
# But cannot send data out (Secure blocks outward)
```

## Connection Formation Rules

When `allow_external_connections=False`:
- Organic connections (Hebbian learning) won't create links across the boundary
- Explicit `link_memories()` with `check_compartments=True` will be blocked
- Explicit `link_memories()` with `check_compartments=False` still works (for administrative purposes)

```python
# This respects compartment rules
client.apply_hebbian_learning([mem1, mem2], respect_compartments=True)

# This checks rules and returns False if blocked
result = client.link_memories(mem1, mem2, check_compartments=True)

# This bypasses rules (admin override)
client.link_memories(mem1, mem2, check_compartments=False)
```

## Permeability Examples

### Secure Project (OSMOTIC_INWARD)

Can reference external knowledge but doesn't expose its data:

```python
secure_project = Compartment(
    name="Secret Project",
    permeability=Permeability.OSMOTIC_INWARD,
    allow_external_connections=False
)

# Queries from inside can reach external memories
# Queries from outside cannot see inside
```

### Knowledge Base (OSMOTIC_OUTWARD)

Publishes data but isn't influenced by external sources:

```python
knowledge_base = Compartment(
    name="Reference Data",
    permeability=Permeability.OSMOTIC_OUTWARD,
    allow_external_connections=False
)

# External queries can read this data
# This compartment won't incorporate external data
```

### Isolated Environment (CLOSED)

Complete isolation:

```python
sandbox = Compartment(
    name="Sandbox",
    permeability=Permeability.CLOSED,
    allow_external_connections=False
)

# No data flows in or out
# Memories inside can only connect to each other
```

## Memory-Level Permeability

Individual memories can have their own permeability, independent of any compartment:

```python
from memory_client import Memory, Permeability

# Create a memory with specific permeability
secret = Memory(
    content="Classified information",
    summary="Secret",
    permeability=Permeability.CLOSED  # Complete isolation
)
memory_id = client.create_memory(secret)

# Or update existing memory permeability
client.set_memory_permeability(memory_id, Permeability.OSMOTIC_OUTWARD)

# Check memory permeability
perm = client.get_memory_permeability(memory_id)
```

Memory permeability is checked even if the memory is not in a compartment, providing fine-grained control at the individual memory level.

## Connection-Level Permeability

Individual connections can have their own permeability:

```python
# Create connection with specific permeability
client.link_memories(mem1, mem2, permeability=Permeability.OSMOTIC_INWARD)

# Update existing connection
client.set_connection_permeability(mem1, mem2, Permeability.CLOSED)

# Check connection permeability
perm = client.get_connection_permeability(mem1, mem2)
```

Connection permeability provides fine-grained control when the compartment default isn't appropriate for a specific relationship.

## Query Filtering

Query methods respect permeability by default:

```python
# Filtered by permeability (default)
related = client.get_related_memories(memory_id, respect_permeability=True)

# Unfiltered (sees everything)
all_related = client.get_related_memories(memory_id, respect_permeability=False)

# Same for strongest connections
strong = client.get_strongest_connections(memory_id, respect_permeability=True)
```

## API Reference

### Compartment Dataclass

```python
@dataclass
class Compartment:
    name: str
    permeability: Permeability = Permeability.OPEN
    allow_external_connections: bool = True
    description: str = ""
```

### Permeability Enum

```python
class Permeability(Enum):
    OPEN = "open"                     # Bidirectional
    CLOSED = "closed"                 # No data flow
    OSMOTIC_INWARD = "osmotic_inward"   # Can pull in, doesn't leak out
    OSMOTIC_OUTWARD = "osmotic_outward" # Can share out, doesn't pull in
```

### Client Methods

| Method | Description |
|--------|-------------|
| `create_compartment(compartment)` | Create a new compartment |
| `get_compartment(id)` | Get compartment by ID |
| `get_compartment_by_name(name)` | Get compartment by name |
| `update_compartment(id, ...)` | Update compartment properties |
| `delete_compartment(id, reassign_memories)` | Delete a compartment |
| `set_active_compartment(id)` | Set active compartment for new memories |
| `get_active_compartment()` | Get current active compartment |
| `add_memory_to_compartment(mem_ids, comp_id)` | Add memory(s) to compartment (accepts single ID or list) |
| `remove_memory_from_compartment(mem_ids, comp_id)` | Remove memory(s) from compartment (accepts single ID or list) |
| `get_memory_compartments(mem_id)` | Get all compartments for a memory |
| `get_memories_in_compartment(comp_id)` | List memories in compartment |
| `can_form_connection(mem1, mem2)` | Check if connection can form |
| `can_data_flow(from_mem, to_mem)` | Check if data can flow (four-layer check) |
| `set_memory_permeability(mem_ids, perm)` | Set permeability for memory(s) (accepts single ID or list) |
| `get_memory_permeability(mem_id)` | Get memory permeability |
| `set_connection_permeability(m1, m2, perm)` | Set connection permeability |
| `get_connection_permeability(m1, m2)` | Get connection permeability |

## Best Practices

1. **Default to OPEN**: Only use restrictions when needed for security or organization.

2. **Use active compartment**: Set `client.set_active_compartment(id)` when working on a project to automatically assign new memories.

3. **OSMOTIC_INWARD for security**: When you need to reference external knowledge but can't risk data leaks.

4. **Check before linking**: Use `check_compartments=True` when creating connections programmatically to respect boundaries.

5. **Connection permeability for exceptions**: Use connection-level permeability for specific relationships that need different rules than the compartment default.

6. **Monitor with queries**: Use `respect_permeability=False` in admin/debug contexts to see the full graph, then switch to `True` for normal operations.
