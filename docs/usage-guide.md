# Usage Guide

This guide explains how to use the Memory Graph System in your applications.

## Basic Usage

### Connecting to the Database

```python
from memory_client import MemoryGraphClient

# Create a client (connects to localhost:7687 by default)
client = MemoryGraphClient()

# Or specify a different URI
client = MemoryGraphClient(uri="bolt://localhost:7687")

# Always close when done
client.close()

# Or use context manager (recommended)
with MemoryGraphClient() as client:
    # Do stuff
    pass
```

### Storing a Memory (Quick Method)

The easiest way to store a memory with all its associations:

```python
from memory_client import MemoryGraphClient, quick_store_memory

with MemoryGraphClient() as client:
    memory_id = quick_store_memory(
        client,
        content="The full content of the memory goes here. This can be as long as needed.",
        summary="A brief one-line summary",
        concepts=["concept1", "concept2"],      # Abstract ideas
        keywords=["specific", "terms"],          # Exact match terms
        topics=["Main Topic", "Secondary Topic"], # Broad categories
        entities=[                               # People, tools, etc.
            ("PersonName", "person"),
            ("ToolName", "technology"),
        ],
        confidence=0.9  # How certain (0-1)
    )
    print(f"Stored memory: {memory_id}")
```

### Storing a Memory (Detailed Method)

For more control, create objects explicitly:

```python
from memory_client import (
    MemoryGraphClient, Memory, Concept, Keyword, Topic, Entity,
    EntityType
)

with MemoryGraphClient() as client:
    # Create the memory
    memory = Memory(
        content="Full content here",
        summary="Brief summary",
        confidence=0.95
    )
    memory_id = client.create_memory(memory)

    # Create and link a concept
    concept = Concept(name="authentication", description="User identity verification")
    concept_id = client.create_concept(concept)
    client.link_memory_to_concept(memory_id, concept_id, relevance=0.9)

    # Create and link a keyword
    keyword = Keyword(term="OAuth2")
    keyword_id = client.create_keyword(keyword)
    client.link_memory_to_keyword(memory_id, keyword_id)

    # Create and link an entity
    entity = Entity(
        name="Auth0",
        type=EntityType.TECHNOLOGY,
        description="Authentication platform"
    )
    entity_id = client.create_entity(entity)
    client.link_memory_to_entity(memory_id, entity_id, role="tool used")
```

## Querying Memories

### Search by Text

```python
with MemoryGraphClient() as client:
    # Search content and summaries
    memories = client.search_memories("authentication", limit=10)
    for m in memories:
        print(f"- {m['summary']}")
```

### Find Related Memories

```python
with MemoryGraphClient() as client:
    # Get memories within 2 relationship hops
    related = client.get_related_memories(memory_id, hops=2, limit=20)
    for m in related:
        print(f"- {m['summary']}")
```

### Query by Concept, Keyword, or Topic

```python
with MemoryGraphClient() as client:
    # By concept
    auth_memories = client.get_memories_by_concept("authentication")

    # By keyword
    oauth_memories = client.get_memories_by_keyword("OAuth2")

    # By topic
    security_memories = client.get_memories_by_topic("Security")

    # By entity
    person_memories = client.get_memories_by_entity("James")
```

### Get a Specific Memory

```python
with MemoryGraphClient() as client:
    # This also updates lastAccessed and accessCount
    memory = client.get_memory(memory_id)
    if memory:
        print(memory['content'])
```

## Working with Goals and Questions

### Create a Goal

```python
from memory_client import Goal, GoalStatus

with MemoryGraphClient() as client:
    goal = Goal(
        description="Implement user authentication system",
        status=GoalStatus.ACTIVE,
        priority=1  # 1 = highest priority
    )
    goal_id = client.create_goal(goal)

    # Link a memory that supports this goal
    client.link_memory_to_goal(memory_id, goal_id, strength=0.8)
```

### Create a Question

```python
from memory_client import Question, QuestionStatus

with MemoryGraphClient() as client:
    question = Question(
        text="What authentication method should we use?",
        status=QuestionStatus.OPEN
    )
    question_id = client.create_question(question)

    # Link a memory that partially answers it
    client.link_memory_to_question(memory_id, question_id, completeness=0.5)
```

### Query Goals and Questions

```python
with MemoryGraphClient() as client:
    # Get all active goals
    active_goals = client.get_active_goals()

    # Get all open/partial questions
    open_questions = client.get_open_questions()
```

## Working with Decisions

### Record a Decision

```python
from memory_client import Decision

with MemoryGraphClient() as client:
    decision = Decision(
        description="Use JWT tokens for authentication",
        rationale="Stateless, scalable, industry standard",
        reversible=True
    )
    decision_id = client.create_decision(decision)

    # Link the memory that informed this decision
    client.link_memory_to_decision(memory_id, decision_id)
```

### Trace Decision Chains

```python
with MemoryGraphClient() as client:
    # See decisions that led to or from this one
    chain = client.get_decision_chain(decision_id)
```

## Working with Contexts

### Create a Context

```python
from memory_client import Context, ContextType, ContextStatus

with MemoryGraphClient() as client:
    # Create a project context
    project = Context(
        name="Authentication Redesign",
        type=ContextType.PROJECT,
        status=ContextStatus.ACTIVE,
        description="Modernizing the auth system"
    )
    project_id = client.create_context(project)

    # Create a task within the project
    task = Context(
        name="Evaluate auth providers",
        type=ContextType.TASK,
        status=ContextStatus.ACTIVE
    )
    task_id = client.create_context(task)

    # Link task to project
    client.link_contexts(project_id, task_id)

    # Link memory to context
    client.link_memory_to_context(memory_id, task_id)
```

## Working with Preferences

### Record a Preference

```python
from memory_client import Preference

with MemoryGraphClient() as client:
    pref = Preference(
        category="coding style",
        preference="Prefer explicit imports over wildcards",
        strength=0.8  # -1 (dislike) to 1 (strong preference)
    )
    pref_id = client.create_preference(pref)

    # Link the memory that revealed this
    client.link_memory_to_preference(memory_id, pref_id)
```

### Query Preferences

```python
with MemoryGraphClient() as client:
    coding_prefs = client.get_preferences_by_category("coding style")
    for p in coding_prefs:
        sign = "+" if p['strength'] > 0 else "-"
        print(f"{sign} {p['preference']}")
```

## Handling Contradictions

### Record a Contradiction

```python
from memory_client import Contradiction, ContradictionStatus

with MemoryGraphClient() as client:
    # Create the contradiction
    contradiction = Contradiction(
        description="Memory A says use sessions, Memory B says use JWT",
        status=ContradictionStatus.UNRESOLVED
    )
    contradiction_id = client.create_contradiction(contradiction)

    # Mark which memories conflict
    client.mark_contradiction(contradiction_id, memory_a_id, memory_b_id)
```

### Resolve a Contradiction

```python
with MemoryGraphClient() as client:
    # Resolve by marking which memory supersedes
    client.resolve_contradiction(
        contradiction_id,
        superseding_memory_id=memory_b_id,
        resolution="JWT is the newer, correct approach"
    )
```

### Find Unresolved Contradictions

```python
with MemoryGraphClient() as client:
    unresolved = client.get_unresolved_contradictions()
    for item in unresolved:
        print(f"Contradiction: {item['c']['description']}")
        print(f"Conflicting memories: {len(item['memories'])}")
```

## Directory Management

### Export Directory to Markdown

```python
with MemoryGraphClient() as client:
    markdown = client.export_directory_markdown()

    # Save to file
    with open("directory.md", "w") as f:
        f.write(markdown)
```

### Get Node Counts

```python
with MemoryGraphClient() as client:
    counts = client.get_node_counts()
    for node_type, count in counts.items():
        print(f"{node_type}: {count}")
```

## Raw Cypher Queries

For advanced use cases, execute Cypher directly:

```python
with MemoryGraphClient() as client:
    # Read query
    results = client._run_query("""
        MATCH (m:Memory)-[:HAS_CONCEPT]->(c:Concept {name: $concept})
        RETURN m.summary as summary, m.created as created
        ORDER BY m.created DESC
        LIMIT 10
    """, {"concept": "authentication"})

    # Write query
    client._run_write("""
        MATCH (m:Memory {id: $id})
        SET m.confidence = $new_confidence
    """, {"id": memory_id, "new_confidence": 0.5})
```

## Best Practices

### 1. Use MERGE-based methods for reusable nodes

Concepts, keywords, topics, entities, and contexts use MERGE, so calling `create_concept("auth")` twice returns the same node.

### 2. Link memories immediately after creation

```python
memory_id = client.create_memory(memory)
client.link_memory_to_concept(memory_id, concept_id)  # Do this right away
```

### 3. Update the directory after bulk operations

```python
# After adding many memories
markdown = client.export_directory_markdown()
with open("directory.md", "w") as f:
    f.write(markdown)
```

### 4. Use context managers

```python
# Good - connection is always closed
with MemoryGraphClient() as client:
    # Do stuff

# Bad - might leak connections
client = MemoryGraphClient()
# Do stuff
# Forgot to close!
```

### 5. Set appropriate confidence levels

- 1.0: Confirmed fact
- 0.8-0.9: Very likely correct
- 0.5-0.7: Probable but uncertain
- Below 0.5: Speculation or inference

## Complete Example

```python
from memory_client import (
    MemoryGraphClient, Memory, Concept, Keyword, Topic,
    Entity, EntityType, Decision, Goal, GoalStatus,
    Context, ContextType, ContextStatus, Preference,
    quick_store_memory
)

with MemoryGraphClient() as client:
    # Initialize schema (only needed once)
    client.initialize_schema()

    # Create a project context
    project = Context(
        name="Memory System Development",
        type=ContextType.PROJECT,
        status=ContextStatus.ACTIVE
    )
    project_id = client.create_context(project)

    # Create a goal
    goal = Goal(
        description="Build a working memory graph system",
        status=GoalStatus.ACTIVE,
        priority=1
    )
    goal_id = client.create_goal(goal)

    # Store a memory
    memory_id = quick_store_memory(
        client,
        content="We decided to use Memgraph because of its speed and Cypher support.",
        summary="Database selection: Memgraph",
        concepts=["graph database", "architecture"],
        keywords=["memgraph", "cypher"],
        topics=["Technology Decisions"],
        entities=[("Memgraph", "technology")]
    )

    # Link to context and goal
    client.link_memory_to_context(memory_id, project_id)
    client.link_memory_to_goal(memory_id, goal_id, strength=0.7)

    # Record a decision
    decision = Decision(
        description="Use Memgraph for the memory database",
        rationale="Fast C++ implementation, Cypher-compatible, low memory usage"
    )
    decision_id = client.create_decision(decision)
    client.link_memory_to_decision(memory_id, decision_id)

    # Record a preference discovered
    pref = Preference(
        category="infrastructure",
        preference="Prefer lightweight, fast databases over feature-rich heavy ones",
        strength=0.8
    )
    pref_id = client.create_preference(pref)
    client.link_memory_to_preference(memory_id, pref_id)

    # Export the directory
    with open("directory.md", "w") as f:
        f.write(client.export_directory_markdown())

    # Query it back
    print("Related memories:")
    for m in client.get_memories_by_concept("graph database"):
        print(f"  - {m['summary']}")
```
