"""
Memory Graph Client
A Python client for interacting with the Memgraph-based memory system.
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

# Using neo4j driver (Memgraph is Bolt-compatible)
from neo4j import GraphDatabase


# ============================================================================
# ENUMS
# ============================================================================

class EntityType(Enum):
    PERSON = "person"
    ORGANIZATION = "organization"
    PROJECT = "project"
    TOOL = "tool"
    TECHNOLOGY = "technology"
    PLACE = "place"


class SourceType(Enum):
    CONVERSATION = "conversation"
    FILE = "file"
    URL = "url"
    DOCUMENT = "document"
    OBSERVATION = "observation"


class GoalStatus(Enum):
    ACTIVE = "active"
    ACHIEVED = "achieved"
    ABANDONED = "abandoned"


class QuestionStatus(Enum):
    OPEN = "open"
    PARTIAL = "partial"
    ANSWERED = "answered"


class ContextType(Enum):
    PROJECT = "project"
    TASK = "task"
    CONVERSATION = "conversation"
    SESSION = "session"
    DOMAIN = "domain"


class ContextStatus(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class TemporalType(Enum):
    POINT = "point"
    PERIOD = "period"
    SEQUENCE = "sequence"


class ContradictionStatus(Enum):
    UNRESOLVED = "unresolved"
    RESOLVED = "resolved"
    ACCEPTED = "accepted"


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class Memory:
    content: str
    summary: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    confidence: float = 1.0


@dataclass
class Concept:
    name: str
    description: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created: datetime = field(default_factory=datetime.now)


@dataclass
class Keyword:
    term: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created: datetime = field(default_factory=datetime.now)


@dataclass
class Topic:
    name: str
    description: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created: datetime = field(default_factory=datetime.now)


@dataclass
class Entity:
    name: str
    type: EntityType
    description: str = ""
    aliases: List[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created: datetime = field(default_factory=datetime.now)


@dataclass
class Source:
    type: SourceType
    reference: str
    title: str = ""
    reliability: float = 1.0
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created: datetime = field(default_factory=datetime.now)


@dataclass
class Decision:
    description: str
    rationale: str
    date: datetime = field(default_factory=datetime.now)
    outcome: str = ""
    reversible: bool = True
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class Goal:
    description: str
    status: GoalStatus = GoalStatus.ACTIVE
    priority: int = 5
    target_date: Optional[datetime] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created: datetime = field(default_factory=datetime.now)


@dataclass
class Question:
    text: str
    status: QuestionStatus = QuestionStatus.OPEN
    answered_date: Optional[datetime] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created: datetime = field(default_factory=datetime.now)


@dataclass
class Context:
    name: str
    type: ContextType
    description: str = ""
    status: ContextStatus = ContextStatus.ACTIVE
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created: datetime = field(default_factory=datetime.now)


@dataclass
class Preference:
    category: str
    preference: str
    strength: float = 0.5  # -1 (dislike) to 1 (strong like)
    observations: int = 1
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created: datetime = field(default_factory=datetime.now)


@dataclass
class TemporalMarker:
    type: TemporalType
    description: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created: datetime = field(default_factory=datetime.now)


@dataclass
class Contradiction:
    description: str
    resolution: str = ""
    status: ContradictionStatus = ContradictionStatus.UNRESOLVED
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created: datetime = field(default_factory=datetime.now)


# ============================================================================
# MEMORY GRAPH CLIENT
# ============================================================================

class MemoryGraphClient:
    """Client for interacting with the Memgraph memory database."""

    def __init__(self, uri: str = "bolt://localhost:7687", user: str = "", password: str = ""):
        """Initialize connection to Memgraph."""
        self.driver = GraphDatabase.driver(uri, auth=(user, password) if user else None)

    def close(self):
        """Close the database connection."""
        self.driver.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _run_query(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict]:
        """Execute a Cypher query and return results."""
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

    def _run_write(self, query: str, parameters: Dict[str, Any] = None) -> None:
        """Execute a write query."""
        with self.driver.session() as session:
            session.run(query, parameters or {})

    # ========================================================================
    # SCHEMA INITIALIZATION
    # ========================================================================

    def initialize_schema(self, schema_file: str = None):
        """Initialize the database schema with indexes."""
        if schema_file:
            with open(schema_file, 'r') as f:
                schema = f.read()
            # Execute each statement separately
            for statement in schema.split(';'):
                statement = statement.strip()
                if statement and not statement.startswith('//'):
                    try:
                        self._run_write(statement)
                    except Exception as e:
                        print(f"Warning: {e}")
        else:
            # Inline minimal schema
            indexes = [
                "CREATE INDEX ON :Memory(id)",
                "CREATE INDEX ON :Memory(created)",
                "CREATE INDEX ON :Concept(id)",
                "CREATE INDEX ON :Concept(name)",
                "CREATE INDEX ON :Keyword(id)",
                "CREATE INDEX ON :Keyword(term)",
                "CREATE INDEX ON :Topic(id)",
                "CREATE INDEX ON :Topic(name)",
                "CREATE INDEX ON :Entity(id)",
                "CREATE INDEX ON :Entity(name)",
                "CREATE INDEX ON :Source(id)",
                "CREATE INDEX ON :Decision(id)",
                "CREATE INDEX ON :Goal(id)",
                "CREATE INDEX ON :Question(id)",
                "CREATE INDEX ON :Context(id)",
                "CREATE INDEX ON :Preference(id)",
                "CREATE INDEX ON :TemporalMarker(id)",
                "CREATE INDEX ON :Contradiction(id)",
            ]
            for idx in indexes:
                try:
                    self._run_write(idx)
                except Exception:
                    pass  # Index may already exist

    # ========================================================================
    # CREATE OPERATIONS
    # ========================================================================

    def create_memory(self, memory: Memory) -> str:
        """Create a new memory node."""
        query = """
        CREATE (m:Memory {
            id: $id,
            content: $content,
            summary: $summary,
            created: $created,
            lastAccessed: $last_accessed,
            accessCount: $access_count,
            confidence: $confidence
        })
        RETURN m.id as id
        """
        self._run_write(query, {
            "id": memory.id,
            "content": memory.content,
            "summary": memory.summary,
            "created": memory.created.isoformat(),
            "last_accessed": memory.last_accessed.isoformat(),
            "access_count": memory.access_count,
            "confidence": memory.confidence
        })
        return memory.id

    def create_concept(self, concept: Concept) -> str:
        """Create a new concept node or return existing."""
        query = """
        MERGE (c:Concept {name: $name})
        ON CREATE SET c.id = $id, c.description = $description, c.created = $created
        RETURN c.id as id
        """
        result = self._run_query(query, {
            "id": concept.id,
            "name": concept.name,
            "description": concept.description,
            "created": concept.created.isoformat()
        })
        return result[0]["id"] if result else concept.id

    def create_keyword(self, keyword: Keyword) -> str:
        """Create a new keyword node or return existing."""
        query = """
        MERGE (k:Keyword {term: $term})
        ON CREATE SET k.id = $id, k.created = $created
        RETURN k.id as id
        """
        result = self._run_query(query, {
            "id": keyword.id,
            "term": keyword.term,
            "created": keyword.created.isoformat()
        })
        return result[0]["id"] if result else keyword.id

    def create_topic(self, topic: Topic) -> str:
        """Create a new topic node or return existing."""
        query = """
        MERGE (t:Topic {name: $name})
        ON CREATE SET t.id = $id, t.description = $description, t.created = $created
        RETURN t.id as id
        """
        result = self._run_query(query, {
            "id": topic.id,
            "name": topic.name,
            "description": topic.description,
            "created": topic.created.isoformat()
        })
        return result[0]["id"] if result else topic.id

    def create_entity(self, entity: Entity) -> str:
        """Create a new entity node or return existing."""
        query = """
        MERGE (e:Entity {name: $name, type: $type})
        ON CREATE SET e.id = $id, e.description = $description,
                      e.aliases = $aliases, e.created = $created
        RETURN e.id as id
        """
        result = self._run_query(query, {
            "id": entity.id,
            "name": entity.name,
            "type": entity.type.value,
            "description": entity.description,
            "aliases": entity.aliases,
            "created": entity.created.isoformat()
        })
        return result[0]["id"] if result else entity.id

    def create_source(self, source: Source) -> str:
        """Create a new source node or return existing."""
        query = """
        MERGE (s:Source {reference: $reference, type: $type})
        ON CREATE SET s.id = $id, s.title = $title,
                      s.reliability = $reliability, s.created = $created
        RETURN s.id as id
        """
        result = self._run_query(query, {
            "id": source.id,
            "type": source.type.value,
            "reference": source.reference,
            "title": source.title,
            "reliability": source.reliability,
            "created": source.created.isoformat()
        })
        return result[0]["id"] if result else source.id

    def create_decision(self, decision: Decision) -> str:
        """Create a new decision node."""
        query = """
        CREATE (d:Decision {
            id: $id,
            description: $description,
            rationale: $rationale,
            date: $date,
            outcome: $outcome,
            reversible: $reversible
        })
        RETURN d.id as id
        """
        self._run_write(query, {
            "id": decision.id,
            "description": decision.description,
            "rationale": decision.rationale,
            "date": decision.date.isoformat(),
            "outcome": decision.outcome,
            "reversible": decision.reversible
        })
        return decision.id

    def create_goal(self, goal: Goal) -> str:
        """Create a new goal node."""
        query = """
        CREATE (g:Goal {
            id: $id,
            description: $description,
            status: $status,
            priority: $priority,
            targetDate: $target_date,
            created: $created
        })
        RETURN g.id as id
        """
        self._run_write(query, {
            "id": goal.id,
            "description": goal.description,
            "status": goal.status.value,
            "priority": goal.priority,
            "target_date": goal.target_date.isoformat() if goal.target_date else None,
            "created": goal.created.isoformat()
        })
        return goal.id

    def create_question(self, question: Question) -> str:
        """Create a new question node."""
        query = """
        CREATE (q:Question {
            id: $id,
            text: $text,
            status: $status,
            answeredDate: $answered_date,
            created: $created
        })
        RETURN q.id as id
        """
        self._run_write(query, {
            "id": question.id,
            "text": question.text,
            "status": question.status.value,
            "answered_date": question.answered_date.isoformat() if question.answered_date else None,
            "created": question.created.isoformat()
        })
        return question.id

    def create_context(self, context: Context) -> str:
        """Create a new context node or return existing."""
        query = """
        MERGE (c:Context {name: $name, type: $type})
        ON CREATE SET c.id = $id, c.description = $description,
                      c.status = $status, c.created = $created
        RETURN c.id as id
        """
        result = self._run_query(query, {
            "id": context.id,
            "name": context.name,
            "type": context.type.value,
            "description": context.description,
            "status": context.status.value,
            "created": context.created.isoformat()
        })
        return result[0]["id"] if result else context.id

    def create_preference(self, preference: Preference) -> str:
        """Create or update a preference node."""
        query = """
        MERGE (p:Preference {category: $category, preference: $preference})
        ON CREATE SET p.id = $id, p.strength = $strength,
                      p.observations = $observations, p.created = $created
        ON MATCH SET p.observations = p.observations + 1,
                     p.strength = (p.strength * p.observations + $strength) / (p.observations + 1)
        RETURN p.id as id
        """
        result = self._run_query(query, {
            "id": preference.id,
            "category": preference.category,
            "preference": preference.preference,
            "strength": preference.strength,
            "observations": preference.observations,
            "created": preference.created.isoformat()
        })
        return result[0]["id"] if result else preference.id

    def create_temporal_marker(self, marker: TemporalMarker) -> str:
        """Create a new temporal marker node."""
        query = """
        CREATE (t:TemporalMarker {
            id: $id,
            type: $type,
            description: $description,
            startDate: $start_date,
            endDate: $end_date,
            created: $created
        })
        RETURN t.id as id
        """
        self._run_write(query, {
            "id": marker.id,
            "type": marker.type.value,
            "description": marker.description,
            "start_date": marker.start_date.isoformat() if marker.start_date else None,
            "end_date": marker.end_date.isoformat() if marker.end_date else None,
            "created": marker.created.isoformat()
        })
        return marker.id

    def create_contradiction(self, contradiction: Contradiction) -> str:
        """Create a new contradiction node."""
        query = """
        CREATE (c:Contradiction {
            id: $id,
            description: $description,
            resolution: $resolution,
            status: $status,
            created: $created
        })
        RETURN c.id as id
        """
        self._run_write(query, {
            "id": contradiction.id,
            "description": contradiction.description,
            "resolution": contradiction.resolution,
            "status": contradiction.status.value,
            "created": contradiction.created.isoformat()
        })
        return contradiction.id

    # ========================================================================
    # RELATIONSHIP OPERATIONS
    # ========================================================================

    def link_memory_to_concept(self, memory_id: str, concept_id: str, relevance: float = 1.0):
        """Link a memory to a concept."""
        query = """
        MATCH (m:Memory {id: $memory_id}), (c:Concept {id: $concept_id})
        MERGE (m)-[r:HAS_CONCEPT]->(c)
        SET r.relevance = $relevance
        """
        self._run_write(query, {"memory_id": memory_id, "concept_id": concept_id, "relevance": relevance})

    def link_memory_to_keyword(self, memory_id: str, keyword_id: str):
        """Link a memory to a keyword."""
        query = """
        MATCH (m:Memory {id: $memory_id}), (k:Keyword {id: $keyword_id})
        MERGE (m)-[:HAS_KEYWORD]->(k)
        """
        self._run_write(query, {"memory_id": memory_id, "keyword_id": keyword_id})

    def link_memory_to_topic(self, memory_id: str, topic_id: str, primary: bool = False):
        """Link a memory to a topic."""
        query = """
        MATCH (m:Memory {id: $memory_id}), (t:Topic {id: $topic_id})
        MERGE (m)-[r:BELONGS_TO]->(t)
        SET r.primary = $primary
        """
        self._run_write(query, {"memory_id": memory_id, "topic_id": topic_id, "primary": primary})

    def link_memory_to_entity(self, memory_id: str, entity_id: str, role: str = ""):
        """Link a memory to an entity."""
        query = """
        MATCH (m:Memory {id: $memory_id}), (e:Entity {id: $entity_id})
        MERGE (m)-[r:MENTIONS]->(e)
        SET r.role = $role
        """
        self._run_write(query, {"memory_id": memory_id, "entity_id": entity_id, "role": role})

    def link_memory_to_source(self, memory_id: str, source_id: str, excerpt: str = ""):
        """Link a memory to its source."""
        query = """
        MATCH (m:Memory {id: $memory_id}), (s:Source {id: $source_id})
        MERGE (m)-[r:FROM_SOURCE]->(s)
        SET r.excerpt = $excerpt
        """
        self._run_write(query, {"memory_id": memory_id, "source_id": source_id, "excerpt": excerpt})

    def link_memory_to_context(self, memory_id: str, context_id: str):
        """Link a memory to a context."""
        query = """
        MATCH (m:Memory {id: $memory_id}), (c:Context {id: $context_id})
        MERGE (m)-[:IN_CONTEXT]->(c)
        """
        self._run_write(query, {"memory_id": memory_id, "context_id": context_id})

    def link_memory_to_decision(self, memory_id: str, decision_id: str):
        """Link a memory that informed a decision."""
        query = """
        MATCH (m:Memory {id: $memory_id}), (d:Decision {id: $decision_id})
        MERGE (m)-[:INFORMED]->(d)
        """
        self._run_write(query, {"memory_id": memory_id, "decision_id": decision_id})

    def link_memory_to_question(self, memory_id: str, question_id: str, completeness: float = 0.5):
        """Link a memory that partially answers a question."""
        query = """
        MATCH (m:Memory {id: $memory_id}), (q:Question {id: $question_id})
        MERGE (m)-[r:PARTIALLY_ANSWERS]->(q)
        SET r.completeness = $completeness
        """
        self._run_write(query, {"memory_id": memory_id, "question_id": question_id, "completeness": completeness})

    def link_memory_to_goal(self, memory_id: str, goal_id: str, strength: float = 0.5):
        """Link a memory that supports a goal."""
        query = """
        MATCH (m:Memory {id: $memory_id}), (g:Goal {id: $goal_id})
        MERGE (m)-[r:SUPPORTS]->(g)
        SET r.strength = $strength
        """
        self._run_write(query, {"memory_id": memory_id, "goal_id": goal_id, "strength": strength})

    def link_memory_to_preference(self, memory_id: str, preference_id: str):
        """Link a memory that reveals a preference."""
        query = """
        MATCH (m:Memory {id: $memory_id}), (p:Preference {id: $preference_id})
        MERGE (m)-[:REVEALS]->(p)
        """
        self._run_write(query, {"memory_id": memory_id, "preference_id": preference_id})

    def link_memory_to_temporal(self, memory_id: str, temporal_id: str):
        """Link a memory to a temporal marker."""
        query = """
        MATCH (m:Memory {id: $memory_id}), (t:TemporalMarker {id: $temporal_id})
        MERGE (m)-[:OCCURRED_DURING]->(t)
        """
        self._run_write(query, {"memory_id": memory_id, "temporal_id": temporal_id})

    def link_memories(self, memory_id_1: str, memory_id_2: str, strength: float = 0.5, rel_type: str = ""):
        """Link two related memories."""
        query = """
        MATCH (m1:Memory {id: $id1}), (m2:Memory {id: $id2})
        MERGE (m1)-[r:RELATES_TO]->(m2)
        SET r.strength = $strength, r.type = $type
        """
        self._run_write(query, {"id1": memory_id_1, "id2": memory_id_2, "strength": strength, "type": rel_type})

    def link_concepts(self, concept_id_1: str, concept_id_2: str, rel_type: str = ""):
        """Link two related concepts."""
        query = """
        MATCH (c1:Concept {id: $id1}), (c2:Concept {id: $id2})
        MERGE (c1)-[r:RELATED_TO]->(c2)
        SET r.type = $type
        """
        self._run_write(query, {"id1": concept_id_1, "id2": concept_id_2, "type": rel_type})

    def link_goals(self, goal_id_1: str, goal_id_2: str):
        """Link a goal that depends on another."""
        query = """
        MATCH (g1:Goal {id: $id1}), (g2:Goal {id: $id2})
        MERGE (g1)-[:DEPENDS_ON]->(g2)
        """
        self._run_write(query, {"id1": goal_id_1, "id2": goal_id_2})

    def link_decisions(self, decision_id_1: str, decision_id_2: str):
        """Link a decision that led to another."""
        query = """
        MATCH (d1:Decision {id: $id1}), (d2:Decision {id: $id2})
        MERGE (d1)-[:LED_TO]->(d2)
        """
        self._run_write(query, {"id1": decision_id_1, "id2": decision_id_2})

    def link_contexts(self, parent_id: str, child_id: str):
        """Link a context as part of another (hierarchy)."""
        query = """
        MATCH (p:Context {id: $parent_id}), (c:Context {id: $child_id})
        MERGE (c)-[:PART_OF]->(p)
        """
        self._run_write(query, {"parent_id": parent_id, "child_id": child_id})

    def mark_contradiction(self, contradiction_id: str, memory_id_1: str, memory_id_2: str):
        """Mark two memories as contradicting each other."""
        query = """
        MATCH (c:Contradiction {id: $cid}), (m1:Memory {id: $mid1}), (m2:Memory {id: $mid2})
        MERGE (c)-[:CONFLICTS_WITH]->(m1)
        MERGE (c)-[:CONFLICTS_WITH]->(m2)
        """
        self._run_write(query, {"cid": contradiction_id, "mid1": memory_id_1, "mid2": memory_id_2})

    def resolve_contradiction(self, contradiction_id: str, superseding_memory_id: str, resolution: str):
        """Resolve a contradiction by marking which memory supersedes."""
        query = """
        MATCH (c:Contradiction {id: $cid}), (m:Memory {id: $mid})
        SET c.status = 'resolved', c.resolution = $resolution
        MERGE (c)-[:SUPERSEDES]->(m)
        """
        self._run_write(query, {"cid": contradiction_id, "mid": superseding_memory_id, "resolution": resolution})

    # ========================================================================
    # QUERY OPERATIONS
    # ========================================================================

    def get_memory(self, memory_id: str) -> Optional[Dict]:
        """Get a memory by ID and update access tracking."""
        query = """
        MATCH (m:Memory {id: $id})
        SET m.lastAccessed = $now, m.accessCount = m.accessCount + 1
        RETURN m
        """
        result = self._run_query(query, {"id": memory_id, "now": datetime.now().isoformat()})
        return result[0]["m"] if result else None

    def search_memories(self, search_term: str, limit: int = 10) -> List[Dict]:
        """Search memories by content or summary."""
        query = """
        MATCH (m:Memory)
        WHERE m.content CONTAINS $term OR m.summary CONTAINS $term
        RETURN m
        ORDER BY m.lastAccessed DESC
        LIMIT $limit
        """
        return [r["m"] for r in self._run_query(query, {"term": search_term, "limit": limit})]

    def get_related_memories(self, memory_id: str, hops: int = 2, limit: int = 20) -> List[Dict]:
        """Get memories related to a given memory within N hops."""
        query = f"""
        MATCH (m:Memory {{id: $id}})-[:RELATES_TO|HAS_CONCEPT|HAS_KEYWORD|BELONGS_TO*1..{hops}]-(related:Memory)
        WHERE related.id <> $id
        RETURN DISTINCT related
        ORDER BY related.lastAccessed DESC
        LIMIT $limit
        """
        return [r["related"] for r in self._run_query(query, {"id": memory_id, "limit": limit})]

    def get_memories_by_concept(self, concept_name: str, limit: int = 20) -> List[Dict]:
        """Get all memories associated with a concept."""
        query = """
        MATCH (m:Memory)-[:HAS_CONCEPT]->(c:Concept {name: $name})
        RETURN m
        ORDER BY m.lastAccessed DESC
        LIMIT $limit
        """
        return [r["m"] for r in self._run_query(query, {"name": concept_name, "limit": limit})]

    def get_memories_by_keyword(self, keyword: str, limit: int = 20) -> List[Dict]:
        """Get all memories associated with a keyword."""
        query = """
        MATCH (m:Memory)-[:HAS_KEYWORD]->(k:Keyword {term: $term})
        RETURN m
        ORDER BY m.lastAccessed DESC
        LIMIT $limit
        """
        return [r["m"] for r in self._run_query(query, {"term": keyword, "limit": limit})]

    def get_memories_by_topic(self, topic_name: str, limit: int = 20) -> List[Dict]:
        """Get all memories belonging to a topic."""
        query = """
        MATCH (m:Memory)-[:BELONGS_TO]->(t:Topic {name: $name})
        RETURN m
        ORDER BY m.lastAccessed DESC
        LIMIT $limit
        """
        return [r["m"] for r in self._run_query(query, {"name": topic_name, "limit": limit})]

    def get_memories_by_entity(self, entity_name: str, limit: int = 20) -> List[Dict]:
        """Get all memories mentioning an entity."""
        query = """
        MATCH (m:Memory)-[:MENTIONS]->(e:Entity {name: $name})
        RETURN m
        ORDER BY m.lastAccessed DESC
        LIMIT $limit
        """
        return [r["m"] for r in self._run_query(query, {"name": entity_name, "limit": limit})]

    def get_open_questions(self) -> List[Dict]:
        """Get all open questions."""
        query = """
        MATCH (q:Question)
        WHERE q.status = 'open' OR q.status = 'partial'
        RETURN q
        ORDER BY q.created DESC
        """
        return [r["q"] for r in self._run_query(query)]

    def get_active_goals(self) -> List[Dict]:
        """Get all active goals."""
        query = """
        MATCH (g:Goal {status: 'active'})
        RETURN g
        ORDER BY g.priority ASC, g.created ASC
        """
        return [r["g"] for r in self._run_query(query)]

    def get_unresolved_contradictions(self) -> List[Dict]:
        """Get all unresolved contradictions with their conflicting memories."""
        query = """
        MATCH (c:Contradiction {status: 'unresolved'})-[:CONFLICTS_WITH]->(m:Memory)
        RETURN c, collect(m) as memories
        """
        return self._run_query(query)

    def get_preferences_by_category(self, category: str) -> List[Dict]:
        """Get all preferences in a category."""
        query = """
        MATCH (p:Preference {category: $category})
        RETURN p
        ORDER BY p.strength DESC
        """
        return [r["p"] for r in self._run_query(query, {"category": category})]

    def get_decision_chain(self, decision_id: str) -> List[Dict]:
        """Trace the chain of decisions leading to/from a decision."""
        query = """
        MATCH path = (d:Decision {id: $id})-[:LED_TO*0..5]-(other:Decision)
        RETURN path
        """
        return self._run_query(query, {"id": decision_id})

    # ========================================================================
    # DIRECTORY OPERATIONS (for markdown index)
    # ========================================================================

    def get_all_nodes_summary(self) -> Dict[str, List[Dict]]:
        """Get a summary of all nodes for the directory index."""
        summary = {}

        # Get all nodes of each type
        node_types = [
            "Memory", "Concept", "Keyword", "Topic", "Entity", "Source",
            "Decision", "Goal", "Question", "Context", "Preference",
            "TemporalMarker", "Contradiction"
        ]

        for node_type in node_types:
            query = f"MATCH (n:{node_type}) RETURN n"
            try:
                result = self._run_query(query)
                summary[node_type] = [r["n"] for r in result]
            except Exception:
                summary[node_type] = []

        return summary

    def get_node_counts(self) -> Dict[str, int]:
        """Get counts of each node type."""
        query = """
        MATCH (n)
        RETURN labels(n)[0] as label, count(n) as count
        """
        result = self._run_query(query)
        return {r["label"]: r["count"] for r in result}

    def export_directory_markdown(self) -> str:
        """Export the node directory as markdown."""
        counts = self.get_node_counts()
        summary = self.get_all_nodes_summary()

        lines = ["# Memory Graph Directory\n"]
        lines.append(f"Last updated: {datetime.now().isoformat()}\n")

        # Summary counts
        lines.append("## Node Counts\n")
        for node_type, count in sorted(counts.items()):
            lines.append(f"- **{node_type}**: {count}")
        lines.append("")

        # Node listings
        for node_type in ["Concept", "Topic", "Keyword", "Entity", "Goal", "Question", "Context", "Preference"]:
            if node_type in summary and summary[node_type]:
                plural = "ies" if node_type.endswith("y") else "s"
                label = node_type[:-1] + plural if node_type.endswith("y") else node_type + "s"
                lines.append(f"\n## {label}\n")
                for item in summary[node_type]:
                    node_id = str(item.get('id', 'N/A'))[:8]
                    if node_type == "Concept":
                        lines.append(f"- `{node_id}` **{item.get('name', 'N/A')}**")
                    elif node_type == "Topic":
                        lines.append(f"- `{node_id}` **{item.get('name', 'N/A')}**")
                    elif node_type == "Keyword":
                        lines.append(f"- `{node_id}` {item.get('term', 'N/A')}")
                    elif node_type == "Entity":
                        lines.append(f"- `{node_id}` **{item.get('name', 'N/A')}** ({item.get('type', 'N/A')})")
                    elif node_type == "Goal":
                        desc = str(item.get('description', 'N/A'))[:50]
                        lines.append(f"- `{node_id}` [{item.get('status', 'N/A')}] {desc}")
                    elif node_type == "Question":
                        text = str(item.get('text', 'N/A'))[:50]
                        lines.append(f"- `{node_id}` [{item.get('status', 'N/A')}] {text}")
                    elif node_type == "Context":
                        lines.append(f"- `{node_id}` **{item.get('name', 'N/A')}** ({item.get('type', 'N/A')}) [{item.get('status', 'N/A')}]")
                    elif node_type == "Preference":
                        strength = item.get('strength', 0) or 0
                        indicator = "+" if strength > 0 else "-" if strength < 0 else "~"
                        lines.append(f"- `{node_id}` [{item.get('category', 'N/A')}] {indicator} {item.get('preference', 'N/A')}")

        return "\n".join(lines)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_client(uri: str = "bolt://localhost:7687") -> MemoryGraphClient:
    """Create a new memory graph client."""
    return MemoryGraphClient(uri=uri)


def quick_store_memory(
    client: MemoryGraphClient,
    content: str,
    summary: str,
    concepts: List[str] = None,
    keywords: List[str] = None,
    topics: List[str] = None,
    entities: List[tuple] = None,  # List of (name, type) tuples
    confidence: float = 1.0
) -> str:
    """Quickly store a memory with its associations."""
    # Create the memory
    memory = Memory(content=content, summary=summary, confidence=confidence)
    memory_id = client.create_memory(memory)

    # Link concepts
    if concepts:
        for concept_name in concepts:
            concept = Concept(name=concept_name)
            concept_id = client.create_concept(concept)
            client.link_memory_to_concept(memory_id, concept_id)

    # Link keywords
    if keywords:
        for term in keywords:
            keyword = Keyword(term=term)
            keyword_id = client.create_keyword(keyword)
            client.link_memory_to_keyword(memory_id, keyword_id)

    # Link topics
    if topics:
        for i, topic_name in enumerate(topics):
            topic = Topic(name=topic_name)
            topic_id = client.create_topic(topic)
            client.link_memory_to_topic(memory_id, topic_id, primary=(i == 0))

    # Link entities
    if entities:
        for name, etype in entities:
            entity = Entity(name=name, type=EntityType(etype))
            entity_id = client.create_entity(entity)
            client.link_memory_to_entity(memory_id, entity_id)

    return memory_id
