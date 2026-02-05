# Database Schema

This document describes all node types, their properties, and the relationships between them.

## Node Types

### Memory

The core node type - represents a single memory.

| Property | Type | Description |
|----------|------|-------------|
| `id` | UUID | Unique identifier |
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
| `id` | UUID | Unique identifier |
| `name` | String | The concept name (e.g., "authentication") |
| `description` | String | Optional description |
| `created` | DateTime | When first created |

### Keyword

Specific terms for exact matching.

| Property | Type | Description |
|----------|------|-------------|
| `id` | UUID | Unique identifier |
| `term` | String | The keyword (e.g., "OAuth2") |
| `created` | DateTime | When first created |

### Topic

Broader subject areas.

| Property | Type | Description |
|----------|------|-------------|
| `id` | UUID | Unique identifier |
| `name` | String | The topic name (e.g., "Software Architecture") |
| `description` | String | Optional description |
| `created` | DateTime | When first created |

### Entity

People, organizations, projects, tools, technologies, places.

| Property | Type | Description |
|----------|------|-------------|
| `id` | UUID | Unique identifier |
| `name` | String | Entity name |
| `type` | Enum | One of: person, organization, project, tool, technology, place |
| `description` | String | Optional description |
| `aliases` | String[] | Alternative names |
| `created` | DateTime | When first created |

### Source

Where information came from.

| Property | Type | Description |
|----------|------|-------------|
| `id` | UUID | Unique identifier |
| `type` | Enum | One of: conversation, file, url, document, observation |
| `reference` | String | The actual reference (file path, URL, etc.) |
| `title` | String | Human-readable title |
| `reliability` | Float (0-1) | How reliable the source is |
| `created` | DateTime | When first created |

### Decision

Choices made with their rationale.

| Property | Type | Description |
|----------|------|-------------|
| `id` | UUID | Unique identifier |
| `description` | String | What was decided |
| `rationale` | String | Why it was decided |
| `date` | DateTime | When the decision was made |
| `outcome` | String | What happened as a result |
| `reversible` | Boolean | Whether the decision can be undone |

### Goal

User objectives.

| Property | Type | Description |
|----------|------|-------------|
| `id` | UUID | Unique identifier |
| `description` | String | The goal |
| `status` | Enum | One of: active, achieved, abandoned |
| `priority` | Integer | Priority (1 = highest) |
| `targetDate` | DateTime | Optional target completion date |
| `created` | DateTime | When first created |

### Question

Unresolved items.

| Property | Type | Description |
|----------|------|-------------|
| `id` | UUID | Unique identifier |
| `text` | String | The question |
| `status` | Enum | One of: open, partial, answered |
| `answeredDate` | DateTime | When fully answered (if applicable) |
| `created` | DateTime | When first created |

### Context

Projects, tasks, conversations, sessions, domains.

| Property | Type | Description |
|----------|------|-------------|
| `id` | UUID | Unique identifier |
| `name` | String | Context name |
| `type` | Enum | One of: project, task, conversation, session, domain |
| `description` | String | Optional description |
| `status` | Enum | One of: active, completed, archived |
| `created` | DateTime | When first created |

### Preference

User likes/dislikes and working styles.

| Property | Type | Description |
|----------|------|-------------|
| `id` | UUID | Unique identifier |
| `category` | String | Category (e.g., "coding style", "communication") |
| `preference` | String | The preference itself |
| `strength` | Float (-1 to 1) | -1 = strong dislike, 0 = neutral, 1 = strong like |
| `observations` | Integer | How many times this has been observed |
| `created` | DateTime | When first created |

### TemporalMarker

Time periods and sequences.

| Property | Type | Description |
|----------|------|-------------|
| `id` | UUID | Unique identifier |
| `type` | Enum | One of: point, period, sequence |
| `description` | String | Description of the time marker |
| `startDate` | DateTime | Start of period (if applicable) |
| `endDate` | DateTime | End of period (if applicable) |
| `created` | DateTime | When first created |

### Contradiction

When information conflicts.

| Property | Type | Description |
|----------|------|-------------|
| `id` | UUID | Unique identifier |
| `description` | String | What the contradiction is |
| `resolution` | String | How it was resolved (if applicable) |
| `status` | Enum | One of: unresolved, resolved, accepted |
| `created` | DateTime | When first created |

---

## Relationships

### Memory Relationships

```
(Memory)-[:RELATES_TO {strength: Float, type: String}]->(Memory)
```
Links two related memories. `strength` indicates how strongly related (0-1). `type` describes the relationship kind.

```
(Memory)-[:HAS_CONCEPT {relevance: Float}]->(Concept)
```
Memory relates to a concept. `relevance` indicates how central this concept is to the memory.

```
(Memory)-[:HAS_KEYWORD]->(Keyword)
```
Memory contains this keyword.

```
(Memory)-[:BELONGS_TO {primary: Boolean}]->(Topic)
```
Memory belongs to a topic. `primary` indicates if this is the main topic.

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

```
(Memory)-[:INVOLVED_IN]->(Contradiction)
```
Memory is involved in a contradiction.

### Inter-Node Relationships

```
(Concept)-[:RELATED_TO {type: String}]->(Concept)
```
Two concepts are related.

```
(Concept)-[:PART_OF]->(Topic)
```
Concept belongs to a broader topic.

```
(Keyword)-[:INDICATES]->(Concept)
```
Keyword suggests a concept.

```
(Entity)-[:RELATED_TO {relationship: String}]->(Entity)
```
Two entities are related. `relationship` describes how (e.g., "works for", "created by").

```
(Entity)-[:WORKS_ON]->(Context)
```
Person/organization is associated with a project/context.

```
(Entity)-[:CREATED]->(Source)
```
Entity authored a source.

```
(Decision)-[:LED_TO]->(Decision)
```
One decision led to another (causal chain).

```
(Decision)-[:SUPPORTS]->(Goal)
```
Decision supports a goal.

```
(Decision)-[:ADDRESSES]->(Question)
```
Decision resolves a question.

```
(Goal)-[:DEPENDS_ON]->(Goal)
```
Goal hierarchy/dependencies.

```
(Goal)-[:BLOCKED_BY]->(Question)
```
Goal can't be achieved until question is answered.

```
(Question)-[:RELATED_TO]->(Question)
```
Connected unknowns.

```
(Question)-[:ABOUT]->(Entity)
```
Question concerns an entity.

```
(Question)-[:ABOUT]->(Concept)
```
Question concerns a concept.

```
(Context)-[:PART_OF]->(Context)
```
Context hierarchy (task within project).

```
(Context)-[:PRECEDED_BY]->(Context)
```
Sequence of contexts.

```
(Contradiction)-[:SUPERSEDES]->(Memory)
```
In a resolved contradiction, new info supersedes old.

```
(Contradiction)-[:CONFLICTS_WITH]->(Memory)
```
The memories that conflict with each other.

```
(TemporalMarker)-[:BEFORE]->(TemporalMarker)
```
Time sequence.

```
(TemporalMarker)-[:CONTAINS]->(TemporalMarker)
```
Period contains a point or smaller period.

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

## Indexes

The following indexes are created for fast lookups:

```cypher
// Primary identifiers
CREATE INDEX ON :Memory(id);
CREATE INDEX ON :Concept(id);
CREATE INDEX ON :Keyword(id);
CREATE INDEX ON :Topic(id);
CREATE INDEX ON :Entity(id);
CREATE INDEX ON :Source(id);
CREATE INDEX ON :Decision(id);
CREATE INDEX ON :Goal(id);
CREATE INDEX ON :Question(id);
CREATE INDEX ON :Context(id);
CREATE INDEX ON :Preference(id);
CREATE INDEX ON :TemporalMarker(id);
CREATE INDEX ON :Contradiction(id);

// Common query fields
CREATE INDEX ON :Memory(created);
CREATE INDEX ON :Memory(lastAccessed);
CREATE INDEX ON :Concept(name);
CREATE INDEX ON :Keyword(term);
CREATE INDEX ON :Topic(name);
CREATE INDEX ON :Entity(name);
CREATE INDEX ON :Entity(type);
CREATE INDEX ON :Goal(status);
CREATE INDEX ON :Question(status);
CREATE INDEX ON :Context(name);
CREATE INDEX ON :Context(status);
CREATE INDEX ON :Preference(category);
CREATE INDEX ON :Contradiction(status);
```

---

## Example Queries

### Find memories related to a concept within 2 hops

```cypher
MATCH (m:Memory)-[:HAS_CONCEPT|RELATES_TO*1..2]-(related:Memory)
WHERE m.id = $memoryId
RETURN DISTINCT related
```

### Find memories that might answer an open question

```cypher
MATCH (q:Question {status: 'open'})<-[:PARTIALLY_ANSWERS]-(m:Memory)
RETURN q, collect(m) as relevantMemories
```

### Trace the reasoning behind a decision

```cypher
MATCH (m:Memory)-[:INFORMED]->(d:Decision)-[:LED_TO*0..3]->(outcome:Decision)
WHERE d.id = $decisionId
RETURN m, d, outcome
```

### Find all unresolved contradictions

```cypher
MATCH (c:Contradiction {status: 'unresolved'})-[:CONFLICTS_WITH]->(m:Memory)
RETURN c, collect(m) as conflictingMemories
```

### Get user preferences in a category

```cypher
MATCH (p:Preference {category: $category})
RETURN p
ORDER BY p.strength DESC
```

### Find all entities connected to a project

```cypher
MATCH (e:Entity)-[:WORKS_ON|MENTIONS*1..2]-(ctx:Context {name: $projectName})
RETURN DISTINCT e
```
