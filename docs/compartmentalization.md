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

| Permeability      | Allows Inward | Allows Outward | Use Case                                          |
| ----------------- | ------------- | -------------- | ------------------------------------------------- |
| `OPEN`            | Yes           | Yes            | Default - no restrictions                         |
| `CLOSED`          | No            | No             | Complete isolation                                |
| `OSMOTIC_INWARD`  | Yes           | No             | Can read external data, but doesn't leak          |
| `OSMOTIC_OUTWARD` | No            | Yes            | Shares data out, but isn't influenced by external |

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

- **Connection formation**: Allowed if memories are in **exactly the same set** of compartments, OR if ALL compartments of BOTH memories allow external connections
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

## Setting Permeability

Permeability can be set at three levels: memory, compartment, and connection. Each level uses the same `Permeability` enum.

### Setting Memory Permeability

```python
from memory_client import MemoryGraphClient, Memory, Permeability

client = MemoryGraphClient()
client.initialize_schema()

# Option 1: Set when creating the memory
secret_memory = Memory(
    content="API key: sk-abc123",
    summary="API credentials",
    permeability=Permeability.CLOSED  # No data in or out
)
mem_id = client.create_memory(secret_memory)

# Option 2: Update after creation (single memory)
client.set_memory_permeability(mem_id, Permeability.OSMOTIC_OUTWARD)

# Option 3: Update multiple memories at once
client.set_memory_permeability([mem1, mem2, mem3], Permeability.OSMOTIC_INWARD)

# Check current permeability
perm = client.get_memory_permeability(mem_id)  # Returns "osmotic_outward"
```

### Setting Compartment Permeability

```python
from memory_client import Compartment, Permeability

# Set when creating the compartment
secure_project = Compartment(
    name="Project X",
    permeability=Permeability.OSMOTIC_INWARD,
    allow_external_connections=False
)
comp_id = client.create_compartment(secure_project)

# Update existing compartment
client.update_compartment(comp_id, permeability=Permeability.CLOSED)
```

### Setting Connection Permeability

```python
# Set when creating the connection
client.link_memories(mem1, mem2, permeability=Permeability.OSMOTIC_INWARD)

# Update existing connection
client.set_connection_permeability(mem1, mem2, Permeability.OPEN)

# Check current permeability
perm = client.get_connection_permeability(mem1, mem2)
```

## How Permeability Works: Practical Examples

### Example 1: Protecting Sensitive Data (CLOSED)

```python
# Create a memory containing sensitive information
credentials = Memory(
    content="Database password: hunter2",
    summary="DB credentials",
    permeability=Permeability.CLOSED
)
cred_id = client.create_memory(credentials)

# Create a normal memory and link them
notes = Memory(content="Remember to rotate credentials", summary="Note")
note_id = client.create_memory(notes)
client.link_memories(cred_id, note_id)

# Query behavior:
# - Queries starting from notes CANNOT see credentials (blocked inward to cred)
# - Queries starting from credentials CANNOT see notes (blocked outward from cred)
assert not client.can_data_flow(cred_id, note_id)  # Blocked: cred won't send data out
assert not client.can_data_flow(note_id, cred_id)  # Blocked: cred won't accept data in
```

### Example 2: Read-Only Knowledge Base (OSMOTIC_OUTWARD)

```python
# Create a compartment for reference documentation
docs_comp = Compartment(
    name="Documentation",
    permeability=Permeability.OSMOTIC_OUTWARD,  # Share out, don't pull in
    allow_external_connections=True
)
docs_id = client.create_compartment(docs_comp)

# Add documentation memories
client.set_active_compartment(docs_id)
api_docs = quick_store_memory(client, content="API returns JSON", summary="API docs")
schema_docs = quick_store_memory(client, content="Users table has id, name", summary="Schema")
client.set_active_compartment(None)

# Create a working memory outside the compartment
work_mem = quick_store_memory(client, content="Working on API integration", summary="Work")
client.link_memories(work_mem, api_docs)

# Query behavior:
# - work_mem CAN see api_docs (docs share outward)
# - api_docs CANNOT see work_mem (docs don't pull inward)
assert client.can_data_flow(api_docs, work_mem)      # Allowed: docs share out
assert not client.can_data_flow(work_mem, api_docs)  # Blocked: docs won't pull in
```

### Example 3: Secure Project (OSMOTIC_INWARD)

```python
# Create a compartment for confidential project work
project_comp = Compartment(
    name="Project Alpha",
    permeability=Permeability.OSMOTIC_INWARD,  # Pull in, don't leak out
    allow_external_connections=False
)
project_id = client.create_compartment(project_comp)

# Add project memories
client.set_active_compartment(project_id)
design = quick_store_memory(client, content="Secret architecture design", summary="Design")
client.set_active_compartment(None)

# Create external reference memory
public_ref = quick_store_memory(client, content="Industry best practices", summary="Reference")

# Query behavior:
# - design CAN see public_ref (project can pull in external knowledge)
# - public_ref CANNOT see design (project doesn't leak)
assert client.can_data_flow(public_ref, design)      # Allowed: project pulls in
assert not client.can_data_flow(design, public_ref)  # Blocked: project won't leak
```

### Example 4: Layered Security with Multiple Levels

```python
# Scenario: Memory in secure compartment with connection-level override

# Create secure compartment
secure = Compartment(name="Secure", permeability=Permeability.OSMOTIC_INWARD)
secure_id = client.create_compartment(secure)

# Create memories
internal = quick_store_memory(client, content="Internal data", summary="Internal",
                               compartment_id=secure_id)
external = quick_store_memory(client, content="External data", summary="External",
                               compartment_id="")

# Default: internal can see external, external cannot see internal
assert client.can_data_flow(external, internal)      # Allowed by compartment
assert not client.can_data_flow(internal, external)  # Blocked by compartment

# Create a special "approved export" connection with OPEN permeability
client.link_memories(internal, external, permeability=Permeability.OPEN)

# Connection permeability alone doesn't override compartment!
# The compartment still blocks because fail-safe requires ALL layers to allow
assert not client.can_data_flow(internal, external)  # Still blocked by compartment

# To allow export, you must change the compartment OR memory permeability
client.set_memory_permeability(internal, Permeability.OPEN)
assert client.can_data_flow(internal, external)  # Now allowed (memory overrides)
```

### Example 5: Fail-Safe with Overlapping Compartments

```python
# Memory in multiple compartments - most restrictive wins

open_comp = Compartment(name="Open", permeability=Permeability.OPEN)
open_id = client.create_compartment(open_comp)

restricted = Compartment(name="Restricted", permeability=Permeability.OSMOTIC_INWARD)
restricted_id = client.create_compartment(restricted)

# Create memory and add to both compartments
dual_mem = quick_store_memory(client, content="Dual membership", summary="Dual",
                               compartment_id="")
client.add_memory_to_compartment(dual_mem, open_id)
client.add_memory_to_compartment(dual_mem, restricted_id)

other_mem = quick_store_memory(client, content="Other data", summary="Other",
                                compartment_id="")

# Even though Open allows outward, Restricted blocks it
# Fail-safe: ANY compartment blocking = blocked
assert not client.can_data_flow(dual_mem, other_mem)  # Blocked by Restricted
assert client.can_data_flow(other_mem, dual_mem)      # Allowed (both allow inward)
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

## Permeability Quick Reference

| Permeability      | Data Flows In? | Data Flows Out? | Typical Use Case                              |
| ----------------- | -------------- | --------------- | --------------------------------------------- |
| `OPEN`            | Yes            | Yes             | Default, unrestricted access                  |
| `CLOSED`          | No             | No              | Credentials, secrets, sandbox environments    |
| `OSMOTIC_INWARD`  | Yes            | No              | Secure projects that need external references |
| `OSMOTIC_OUTWARD` | No             | Yes             | Read-only knowledge bases, documentation      |

**Remember**: "Inward" and "Outward" refer to data flow direction, not query direction. A query from memory A to memory B causes data to flow FROM B TO A.

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

| Method                                             | Description                                                   |
| -------------------------------------------------- | ------------------------------------------------------------- |
| `create_compartment(compartment)`                  | Create a new compartment                                      |
| `get_compartment(id)`                              | Get compartment by ID                                         |
| `get_compartment_by_name(name)`                    | Get compartment by name                                       |
| `update_compartment(id, ...)`                      | Update compartment properties                                 |
| `delete_compartment(id, reassign_memories)`        | Delete a compartment                                          |
| `set_active_compartment(id)`                       | Set active compartment for new memories                       |
| `get_active_compartment()`                         | Get current active compartment                                |
| `add_memory_to_compartment(mem_ids, comp_id)`      | Add memory(s) to compartment (accepts single ID or list)      |
| `remove_memory_from_compartment(mem_ids, comp_id)` | Remove memory(s) from compartment (accepts single ID or list) |
| `get_memory_compartments(mem_id)`                  | Get all compartments for a memory                             |
| `get_memories_in_compartment(comp_id)`             | List memories in compartment                                  |
| `can_form_connection(mem1, mem2)`                  | Check if connection can form                                  |
| `can_data_flow(from_mem, to_mem)`                  | Check if data can flow (five-layer check)                     |
| `set_memory_permeability(mem_ids, perm)`           | Set permeability for memory(s) (accepts single ID or list)    |
| `get_memory_permeability(mem_id)`                  | Get memory permeability                                       |
| `set_connection_permeability(m1, m2, perm)`        | Set connection permeability                                   |
| `get_connection_permeability(m1, m2)`              | Get connection permeability                                   |

## Best Practices

1. **Default to OPEN**: Only use restrictions when needed for security or organization.

2. **Use active compartment**: Set `client.set_active_compartment(id)` when working on a project to automatically assign new memories.

3. **OSMOTIC_INWARD for security**: When you need to reference external knowledge but can't risk data leaks.

4. **Check before linking**: Use `check_compartments=True` when creating connections programmatically to respect boundaries.

5. **Connection permeability for exceptions**: Use connection-level permeability for specific relationships that need different rules than the compartment default.

6. **Monitor with queries**: Use `respect_permeability=False` in admin/debug contexts to see the full graph, then switch to `True` for normal operations.
