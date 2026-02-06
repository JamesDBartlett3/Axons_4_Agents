# Database Schema

This document describes all node types, their properties, and the relationships between them.

## Node Types

### Memory

The core node type - represents a single memory.

| Property | Type | Description |
|----------|------|-------------|
| `id` | UUID | Unique identifier (primary key) |
| `content` | String | Full memory content |
| `summary` | String | Brief summary for quick scanning |
| `created` | DateTime | When the memory was created |
| `lastAccessed` | DateTime | When the memory was last retrieved |
| `accessCount` | Integer | How many times it's been accessed |
| `confidence` | Float (0-1) | How certain the information is |

### Concept

Abstract ideas that memories relate to.

| Property | Type | Description |
|----------|------|-------------|
| `id` | UUID | Unique identifier (primary key) |
| `name` | String | The concept name (e.g., "authentication") |
| `description` | String | Optional description |
| `created` | DateTime | When first created |

### Keyword

Specific terms for exact matching.

| Property | Type | Description |
|----------|------|-------------|
| `id` | UUID | Unique identifier (primary key) |
| `term` | String | The keyword (e.g., "OAuth2") |
| `created` | DateTime | When first created |

### Topic

Broader subject areas.

| Property | Type | Description |
|----------|------|-------------|
| `id` | UUID | Unique identifier (primary key) |
| `name` | String | The topic name (e.g., "Software Architecture") |
| `description` | String | Optional description |
| `created` | DateTime | When first created |

### Entity

People, organizations, projects, tools, technologies, places.

| Property | Type | Description |
|----------|------|-------------|
| `id` | UUID | Unique identifier (primary key) |
| `name` | String | Entity name |
| `type` | Enum | One of: person, organization, project, tool, technology, place |
| `description` | String | Optional description |
| `aliases` | String[] | Alternative names |
| `created` | DateTime | When first created |

### Source

Where information came from.

| Property | Type | Description |
|----------|------|-------------|
| `id` | UUID | Unique identifier (primary key) |
| `type` | Enum | One of: conversation, file, url, document, observation |
| `reference` | String | The actual reference (file path, URL, etc.) |
| `title` | String | Human-readable title |
| `reliability` | Float (0-1) | How reliable the source is |
| `created` | DateTime | When first created |

### Decision

Choices made with their rationale.

| Property | Type | Description |
|----------|------|-------------|
| `id` | UUID | Unique identifier (primary key) |
| `description` | String | What was decided |
| `rationale` | String | Why it was decided |
| `date` | DateTime | When the decision was made |
| `outcome` | String | What happened as a result |
| `reversible` | Boolean | Whether the decision can be undone |

### Goal

User objectives.

| Property | Type | Description |
|----------|------|-------------|
| `id` | UUID | Unique identifier (primary key) |
| `description` | String | The goal |
| `status` | Enum | One of: active, achieved, abandoned |
| `priority` | Integer | Priority (1 = highest) |
| `targetDate` | DateTime | Optional target completion date |
| `created` | DateTime | When first created |

### Question

Unresolved items.

| Property | Type | Description |
|----------|------|-------------|
| `id` | UUID | Unique identifier (primary key) |
| `text` | String | The question |
| `status` | Enum | One of: open, partial, answered |
| `answeredDate` | DateTime | When fully answered (if applicable) |
| `created` | DateTime | When first created |

### Context

Projects, tasks, conversations, sessions, domains.

| Property | Type | Description |
|----------|------|-------------|
| `id` | UUID | Unique identifier (primary key) |
| `name` | String | Context name |
| `type` | Enum | One of: project, task, conversation, session, domain |
| `description` | String | Optional description |
| `status` | Enum | One of: active, completed, archived |
| `created` | DateTime | When first created |

### Preference

User likes/dislikes and working styles.

| Property | Type | Description |
|----------|------|-------------|
| `id` | UUID | Unique identifier (primary key) |
| `category` | String | Category (e.g., "coding style", "communication") |
| `preference` | String | The preference itself |
| `strength` | Float (-1 to 1) | -1 = strong dislike, 0 = neutral, 1 = strong like |
| `observations` | Integer | How many times this has been observed |
| `created` | DateTime | When first created |

### TemporalMarker

Time periods and sequences.

| Property | Type | Description |
|----------|------|-------------|
| `id` | UUID | Unique identifier (primary key) |
| `type` | Enum | One of: point, period, sequence |
| `description` | String | Description of the time marker |
| `startDate` | DateTime | Start of period (if applicable) |
| `endDate` | DateTime | End of period (if applicable) |
| `created` | DateTime | When first created |

### Contradiction

When information conflicts.

| Property | Type | Description |
|----------|------|-------------|
| `id` | UUID | Unique identifier (primary key) |
| `description` | String | What the contradiction is |
| `resolution` | String | How it was resolved (if applicable) |
| `status` | Enum | One of: unresolved, resolved, accepted |
| `created` | DateTime | When first created |

---

## Relationships

### Memory Relationships

```
(Memory)-[:RELATES_TO {strength: Float, relType: String}]->(Memory)
```
Links two related memories. `strength` indicates how strongly related (0-1). `relType` describes the relationship kind.

```
(Memory)-[:HAS_CONCEPT {relevance: Float}]->(Concept)
```
Memory relates to a concept. `relevance` indicates how central this concept is to the memory.

```
(Memory)-[:HAS_KEYWORD]->(Keyword)
```
Memory contains this keyword.

```
(Memory)-[:BELONGS_TO {isPrimary: Boolean}]->(Topic)
```
Memory belongs to a topic. `isPrimary` indicates if this is the main topic.

```
(Memory)-[:MENTIONS {role: String}]->(Entity)
```
Memory mentions an entity. `role` describes how (e.g., "subject", "author", "tool used").

```
(Memory)-[:FROM_SOURCE {excerpt: String}]->(Source)
```
Memory came from this source. `excerpt` contains the relevant quote if applicable.

```
(Memory)-[:IN_CONTEXT]->(Context)
```
Memory belongs to this context (project, task, etc.).

```
(Memory)-[:OCCURRED_DURING]->(TemporalMarker)
```
Memory relates to this time period.

```
(Memory)-[:INFORMED]->(Decision)
```
Memory informed this decision.

```
(Memory)-[:PARTIALLY_ANSWERS {completeness: Float}]->(Question)
```
Memory partially answers this question. `completeness` indicates how much (0-1).

```
(Memory)-[:SUPPORTS {strength: Float}]->(Goal)
```
Memory supports this goal.

```
(Memory)-[:REVEALS]->(Preference)
```
Memory reveals this user preference.

### Inter-Node Relationships

```
(Concept)-[:CONCEPT_RELATED_TO {relType: String}]->(Concept)
```
Two concepts are related.

```
(Decision)-[:LED_TO]->(Decision)
```
One decision led to another (causal chain).

```
(Goal)-[:DEPENDS_ON]->(Goal)
```
Goal hierarchy/dependencies.

```
(Context)-[:PART_OF]->(Context)
```
Context hierarchy (task within project).

```
(Contradiction)-[:CONFLICTS_WITH]->(Memory)
```
The memories that conflict with each other.

```
(Contradiction)-[:SUPERSEDES]->(Memory)
```
In a resolved contradiction, new info supersedes old.

---

## Visual Schema

```
                                    ┌─────────────┐
                                    │   Topic     │
                                    └──────▲──────┘
                                           │ BELONGS_TO
                                           │
┌─────────────┐    HAS_CONCEPT    ┌────────┴────────┐    HAS_KEYWORD    ┌─────────────┐
│   Concept   │◄──────────────────│     Memory      │──────────────────►│   Keyword   │
└─────────────┘                   └────────┬────────┘                   └─────────────┘
                                           │
              ┌────────────────────────────┼────────────────────────────┐
              │                            │                            │
              ▼                            ▼                            ▼
       ┌─────────────┐              ┌─────────────┐              ┌─────────────┐
       │   Entity    │              │   Source    │              │   Context   │
       └─────────────┘              └─────────────┘              └─────────────┘

              │                            │                            │
              │                            │                            │
              ▼                            ▼                            ▼
       ┌─────────────┐              ┌─────────────┐              ┌─────────────┐
       │  Decision   │              │    Goal     │              │  Question   │
       └─────────────┘              └─────────────┘              └─────────────┘

                                           │
                                           ▼
                              ┌─────────────────────────┐
                              │  Preference │ Temporal  │
                              │             │ Marker    │
                              └─────────────────────────┘

                                           │
                                           ▼
                                   ┌─────────────┐
                                   │Contradiction│
                                   └─────────────┘
```

---

## Example Queries

### Find memories related to a concept

```cypher
MATCH (m:Memory)-[:HAS_CONCEPT]->(c:Concept {name: $conceptName})
RETURN m
ORDER BY m.lastAccessed DESC
LIMIT 20
```

### Find memories that might answer an open question

```cypher
MATCH (q:Question {status: 'open'})<-[:PARTIALLY_ANSWERS]-(m:Memory)
RETURN q, m
```

### Find all unresolved contradictions

```cypher
MATCH (c:Contradiction {status: 'unresolved'})-[:CONFLICTS_WITH]->(m:Memory)
RETURN c, m
```

### Get user preferences in a category

```cypher
MATCH (p:Preference {category: $category})
RETURN p
ORDER BY p.strength DESC
```

### Find memories through shared concepts

```cypher
MATCH (m1:Memory {id: $memoryId})-[:HAS_CONCEPT]->(c:Concept)<-[:HAS_CONCEPT]-(m2:Memory)
WHERE m2.id <> $memoryId
RETURN DISTINCT m2
LIMIT 20
```

---

## Plasticity Operations

The system supports brain-like learning through weighted relationships.

### Strengthen Connection (Hebbian Learning)

```cypher
MATCH (m1:Memory)-[r:RELATES_TO]->(m2:Memory)
WHERE m1.id = $id1 AND m2.id = $id2
SET r.strength = CASE
    WHEN r.strength + $amount > 1.0 THEN 1.0
    ELSE r.strength + $amount
END
```

### Weaken Connection (Synaptic Depression)

```cypher
MATCH (m1:Memory)-[r:RELATES_TO]->(m2:Memory)
WHERE m1.id = $id1 AND m2.id = $id2
SET r.strength = CASE
    WHEN r.strength - $amount < 0.0 THEN 0.0
    ELSE r.strength - $amount
END
```

### Decay Weak Connections

```cypher
MATCH ()-[r:RELATES_TO]->()
WHERE r.strength < $threshold AND r.strength > 0
SET r.strength = CASE
    WHEN r.strength - $decay < 0.0 THEN 0.0
    ELSE r.strength - $decay
END
```

### Prune Dead Connections

```cypher
MATCH ()-[r:RELATES_TO]->()
WHERE r.strength < $minStrength
DELETE r
```

### Find Strong Associations

```cypher
MATCH (m:Memory {id: $memoryId})-[r:RELATES_TO]->(related:Memory)
WHERE r.strength >= $minStrength
RETURN related, r.strength AS strength
ORDER BY r.strength DESC
```
