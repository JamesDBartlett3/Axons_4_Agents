"""
Memory Graph Client
A Python client for interacting with the KùzuDB-based memory system.

Cross-platform compatible: Works natively on Windows, macOS, and Linux.
Only requires: pip install kuzu
"""

import uuid
import os
import shutil
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import kuzu


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
    """Client for interacting with the KùzuDB memory database."""

    def __init__(self, db_path: str = None):
        """
        Initialize connection to KùzuDB.

        Args:
            db_path: Path to the database directory. If None, uses default location
                     in user's home directory (~/.axons_memory_db)
        """
        if db_path is None:
            db_path = os.path.join(Path.home(), ".axons_memory_db")

        self.db_path = db_path
        self.db = kuzu.Database(db_path)
        self.conn = kuzu.Connection(self.db)
        self._schema_initialized = False

    def close(self):
        """Close the database connection."""
        # KùzuDB connections are automatically managed, but we can clear references
        self.conn = None
        self.db = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _run_query(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict]:
        """Execute a Cypher query and return results."""
        try:
            if parameters:
                result = self.conn.execute(query, parameters)
            else:
                result = self.conn.execute(query)

            rows = []
            while result.has_next():
                row = result.get_next()
                # Convert row to dict using column names
                col_names = result.get_column_names()
                row_dict = {}
                for i, name in enumerate(col_names):
                    row_dict[name] = row[i]
                rows.append(row_dict)
            return rows
        except Exception as e:
            # Return empty list for queries that don't return results
            if "does not return any result" in str(e).lower():
                return []
            raise

    def _run_write(self, query: str, parameters: Dict[str, Any] = None) -> None:
        """Execute a write query."""
        try:
            if parameters:
                self.conn.execute(query, parameters)
            else:
                self.conn.execute(query)
        except Exception as e:
            # Ignore "already exists" errors for idempotent operations
            if "already exists" not in str(e).lower():
                raise

    # ========================================================================
    # SCHEMA INITIALIZATION
    # ========================================================================

    def initialize_schema(self, schema_file: str = None):
        """Initialize the database schema with node and relationship tables."""
        if self._schema_initialized:
            return

        # Create node tables
        node_tables = [
            """CREATE NODE TABLE IF NOT EXISTS Memory (
                id STRING PRIMARY KEY,
                content STRING,
                summary STRING,
                created STRING,
                lastAccessed STRING,
                accessCount INT64,
                confidence DOUBLE
            )""",
            """CREATE NODE TABLE IF NOT EXISTS Concept (
                id STRING PRIMARY KEY,
                name STRING,
                description STRING,
                created STRING
            )""",
            """CREATE NODE TABLE IF NOT EXISTS Keyword (
                id STRING PRIMARY KEY,
                term STRING,
                created STRING
            )""",
            """CREATE NODE TABLE IF NOT EXISTS Topic (
                id STRING PRIMARY KEY,
                name STRING,
                description STRING,
                created STRING
            )""",
            """CREATE NODE TABLE IF NOT EXISTS Entity (
                id STRING PRIMARY KEY,
                name STRING,
                type STRING,
                description STRING,
                aliases STRING[],
                created STRING
            )""",
            """CREATE NODE TABLE IF NOT EXISTS Source (
                id STRING PRIMARY KEY,
                type STRING,
                reference STRING,
                title STRING,
                reliability DOUBLE,
                created STRING
            )""",
            """CREATE NODE TABLE IF NOT EXISTS Decision (
                id STRING PRIMARY KEY,
                description STRING,
                rationale STRING,
                date STRING,
                outcome STRING,
                reversible BOOLEAN
            )""",
            """CREATE NODE TABLE IF NOT EXISTS Goal (
                id STRING PRIMARY KEY,
                description STRING,
                status STRING,
                priority INT64,
                targetDate STRING,
                created STRING
            )""",
            """CREATE NODE TABLE IF NOT EXISTS Question (
                id STRING PRIMARY KEY,
                text STRING,
                status STRING,
                answeredDate STRING,
                created STRING
            )""",
            """CREATE NODE TABLE IF NOT EXISTS Context (
                id STRING PRIMARY KEY,
                name STRING,
                type STRING,
                description STRING,
                status STRING,
                created STRING
            )""",
            """CREATE NODE TABLE IF NOT EXISTS Preference (
                id STRING PRIMARY KEY,
                category STRING,
                preference STRING,
                strength DOUBLE,
                observations INT64,
                created STRING
            )""",
            """CREATE NODE TABLE IF NOT EXISTS TemporalMarker (
                id STRING PRIMARY KEY,
                type STRING,
                description STRING,
                startDate STRING,
                endDate STRING,
                created STRING
            )""",
            """CREATE NODE TABLE IF NOT EXISTS Contradiction (
                id STRING PRIMARY KEY,
                description STRING,
                resolution STRING,
                status STRING,
                created STRING
            )"""
        ]

        # Create relationship tables
        # Note: KùzuDB has limited support for relationship properties in Cypher syntax,
        # so we keep relationships simple for cross-platform compatibility
        rel_tables = [
            "CREATE REL TABLE IF NOT EXISTS HAS_CONCEPT (FROM Memory TO Concept)",
            "CREATE REL TABLE IF NOT EXISTS HAS_KEYWORD (FROM Memory TO Keyword)",
            "CREATE REL TABLE IF NOT EXISTS BELONGS_TO (FROM Memory TO Topic)",
            "CREATE REL TABLE IF NOT EXISTS MENTIONS (FROM Memory TO Entity)",
            "CREATE REL TABLE IF NOT EXISTS FROM_SOURCE (FROM Memory TO Source)",
            "CREATE REL TABLE IF NOT EXISTS IN_CONTEXT (FROM Memory TO Context)",
            "CREATE REL TABLE IF NOT EXISTS INFORMED (FROM Memory TO Decision)",
            "CREATE REL TABLE IF NOT EXISTS PARTIALLY_ANSWERS (FROM Memory TO Question)",
            "CREATE REL TABLE IF NOT EXISTS SUPPORTS (FROM Memory TO Goal)",
            "CREATE REL TABLE IF NOT EXISTS REVEALS (FROM Memory TO Preference)",
            "CREATE REL TABLE IF NOT EXISTS OCCURRED_DURING (FROM Memory TO TemporalMarker)",
            "CREATE REL TABLE IF NOT EXISTS RELATES_TO (FROM Memory TO Memory)",
            "CREATE REL TABLE IF NOT EXISTS CONCEPT_RELATED_TO (FROM Concept TO Concept)",
            "CREATE REL TABLE IF NOT EXISTS DEPENDS_ON (FROM Goal TO Goal)",
            "CREATE REL TABLE IF NOT EXISTS LED_TO (FROM Decision TO Decision)",
            "CREATE REL TABLE IF NOT EXISTS PART_OF (FROM Context TO Context)",
            "CREATE REL TABLE IF NOT EXISTS CONFLICTS_WITH (FROM Contradiction TO Memory)",
            "CREATE REL TABLE IF NOT EXISTS SUPERSEDES (FROM Contradiction TO Memory)"
        ]

        # Execute all schema statements
        for stmt in node_tables + rel_tables:
            try:
                self._run_write(stmt)
            except Exception as e:
                # Ignore errors for tables that already exist
                if "already exists" not in str(e).lower():
                    print(f"Warning: {e}")

        self._schema_initialized = True

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
        # Check if concept with same name exists
        check_query = "MATCH (c:Concept) WHERE c.name = $name RETURN c.id AS id"
        result = self._run_query(check_query, {"name": concept.name})
        if result:
            return result[0]["id"]

        query = """
        CREATE (c:Concept {
            id: $id,
            name: $name,
            description: $description,
            created: $created
        })
        """
        self._run_write(query, {
            "id": concept.id,
            "name": concept.name,
            "description": concept.description,
            "created": concept.created.isoformat()
        })
        return concept.id

    def create_keyword(self, keyword: Keyword) -> str:
        """Create a new keyword node or return existing."""
        # Check if keyword with same term exists
        check_query = "MATCH (k:Keyword) WHERE k.term = $term RETURN k.id AS id"
        result = self._run_query(check_query, {"term": keyword.term})
        if result:
            return result[0]["id"]

        query = """
        CREATE (k:Keyword {
            id: $id,
            term: $term,
            created: $created
        })
        """
        self._run_write(query, {
            "id": keyword.id,
            "term": keyword.term,
            "created": keyword.created.isoformat()
        })
        return keyword.id

    def create_topic(self, topic: Topic) -> str:
        """Create a new topic node or return existing."""
        # Check if topic with same name exists
        check_query = "MATCH (t:Topic) WHERE t.name = $name RETURN t.id AS id"
        result = self._run_query(check_query, {"name": topic.name})
        if result:
            return result[0]["id"]

        query = """
        CREATE (t:Topic {
            id: $id,
            name: $name,
            description: $description,
            created: $created
        })
        """
        self._run_write(query, {
            "id": topic.id,
            "name": topic.name,
            "description": topic.description,
            "created": topic.created.isoformat()
        })
        return topic.id

    def create_entity(self, entity: Entity) -> str:
        """Create a new entity node or return existing."""
        # Check if entity with same name and type exists
        check_query = "MATCH (e:Entity) WHERE e.name = $name AND e.type = $type RETURN e.id AS id"
        result = self._run_query(check_query, {"name": entity.name, "type": entity.type.value})
        if result:
            return result[0]["id"]

        query = """
        CREATE (e:Entity {
            id: $id,
            name: $name,
            type: $type,
            description: $description,
            aliases: $aliases,
            created: $created
        })
        """
        self._run_write(query, {
            "id": entity.id,
            "name": entity.name,
            "type": entity.type.value,
            "description": entity.description,
            "aliases": entity.aliases,
            "created": entity.created.isoformat()
        })
        return entity.id

    def create_source(self, source: Source) -> str:
        """Create a new source node or return existing."""
        # Check if source with same reference and type exists
        check_query = "MATCH (s:Source) WHERE s.reference = $reference AND s.type = $type RETURN s.id AS id"
        result = self._run_query(check_query, {"reference": source.reference, "type": source.type.value})
        if result:
            return result[0]["id"]

        query = """
        CREATE (s:Source {
            id: $id,
            type: $type,
            reference: $reference,
            title: $title,
            reliability: $reliability,
            created: $created
        })
        """
        self._run_write(query, {
            "id": source.id,
            "type": source.type.value,
            "reference": source.reference,
            "title": source.title,
            "reliability": source.reliability,
            "created": source.created.isoformat()
        })
        return source.id

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
        """
        self._run_write(query, {
            "id": goal.id,
            "description": goal.description,
            "status": goal.status.value,
            "priority": goal.priority,
            "target_date": goal.target_date.isoformat() if goal.target_date else "",
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
        """
        self._run_write(query, {
            "id": question.id,
            "text": question.text,
            "status": question.status.value,
            "answered_date": question.answered_date.isoformat() if question.answered_date else "",
            "created": question.created.isoformat()
        })
        return question.id

    def create_context(self, context: Context) -> str:
        """Create a new context node or return existing."""
        # Check if context with same name and type exists
        check_query = "MATCH (c:Context) WHERE c.name = $name AND c.type = $type RETURN c.id AS id"
        result = self._run_query(check_query, {"name": context.name, "type": context.type.value})
        if result:
            return result[0]["id"]

        query = """
        CREATE (c:Context {
            id: $id,
            name: $name,
            type: $type,
            description: $description,
            status: $status,
            created: $created
        })
        """
        self._run_write(query, {
            "id": context.id,
            "name": context.name,
            "type": context.type.value,
            "description": context.description,
            "status": context.status.value,
            "created": context.created.isoformat()
        })
        return context.id

    def create_preference(self, preference: Preference) -> str:
        """Create or update a preference node."""
        # Check if preference with same category and preference exists
        check_query = """
        MATCH (p:Preference)
        WHERE p.category = $category AND p.preference = $preference
        RETURN p.id AS id, p.strength AS strength, p.observations AS observations
        """
        result = self._run_query(check_query, {
            "category": preference.category,
            "preference": preference.preference
        })

        if result:
            # Update existing preference
            existing = result[0]
            new_observations = existing["observations"] + 1
            new_strength = (existing["strength"] * existing["observations"] + preference.strength) / new_observations
            update_query = """
            MATCH (p:Preference {id: $id})
            SET p.observations = $observations, p.strength = $strength
            """
            self._run_write(update_query, {
                "id": existing["id"],
                "observations": new_observations,
                "strength": new_strength
            })
            return existing["id"]

        query = """
        CREATE (p:Preference {
            id: $id,
            category: $category,
            preference: $preference,
            strength: $strength,
            observations: $observations,
            created: $created
        })
        """
        self._run_write(query, {
            "id": preference.id,
            "category": preference.category,
            "preference": preference.preference,
            "strength": preference.strength,
            "observations": preference.observations,
            "created": preference.created.isoformat()
        })
        return preference.id

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
        """
        self._run_write(query, {
            "id": marker.id,
            "type": marker.type.value,
            "description": marker.description,
            "start_date": marker.start_date.isoformat() if marker.start_date else "",
            "end_date": marker.end_date.isoformat() if marker.end_date else "",
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
        MATCH (m:Memory), (c:Concept)
        WHERE m.id = $memory_id AND c.id = $concept_id
        CREATE (m)-[:HAS_CONCEPT]->(c)
        """
        self._run_write(query, {"memory_id": memory_id, "concept_id": concept_id})

    def link_memory_to_keyword(self, memory_id: str, keyword_id: str):
        """Link a memory to a keyword."""
        query = """
        MATCH (m:Memory), (k:Keyword)
        WHERE m.id = $memory_id AND k.id = $keyword_id
        CREATE (m)-[:HAS_KEYWORD]->(k)
        """
        self._run_write(query, {"memory_id": memory_id, "keyword_id": keyword_id})

    def link_memory_to_topic(self, memory_id: str, topic_id: str, primary: bool = False):
        """Link a memory to a topic."""
        query = """
        MATCH (m:Memory), (t:Topic)
        WHERE m.id = $memory_id AND t.id = $topic_id
        CREATE (m)-[:BELONGS_TO]->(t)
        """
        self._run_write(query, {"memory_id": memory_id, "topic_id": topic_id})

    def link_memory_to_entity(self, memory_id: str, entity_id: str, role: str = ""):
        """Link a memory to an entity."""
        query = """
        MATCH (m:Memory), (e:Entity)
        WHERE m.id = $memory_id AND e.id = $entity_id
        CREATE (m)-[:MENTIONS]->(e)
        """
        self._run_write(query, {"memory_id": memory_id, "entity_id": entity_id})

    def link_memory_to_source(self, memory_id: str, source_id: str, excerpt: str = ""):
        """Link a memory to its source."""
        query = """
        MATCH (m:Memory), (s:Source)
        WHERE m.id = $memory_id AND s.id = $source_id
        CREATE (m)-[:FROM_SOURCE]->(s)
        """
        self._run_write(query, {"memory_id": memory_id, "source_id": source_id})

    def link_memory_to_context(self, memory_id: str, context_id: str):
        """Link a memory to a context."""
        query = """
        MATCH (m:Memory), (c:Context)
        WHERE m.id = $memory_id AND c.id = $context_id
        CREATE (m)-[:IN_CONTEXT]->(c)
        """
        self._run_write(query, {"memory_id": memory_id, "context_id": context_id})

    def link_memory_to_decision(self, memory_id: str, decision_id: str):
        """Link a memory that informed a decision."""
        query = """
        MATCH (m:Memory), (d:Decision)
        WHERE m.id = $memory_id AND d.id = $decision_id
        CREATE (m)-[:INFORMED]->(d)
        """
        self._run_write(query, {"memory_id": memory_id, "decision_id": decision_id})

    def link_memory_to_question(self, memory_id: str, question_id: str, completeness: float = 0.5):
        """Link a memory that partially answers a question."""
        query = """
        MATCH (m:Memory), (q:Question)
        WHERE m.id = $memory_id AND q.id = $question_id
        CREATE (m)-[:PARTIALLY_ANSWERS]->(q)
        """
        self._run_write(query, {"memory_id": memory_id, "question_id": question_id})

    def link_memory_to_goal(self, memory_id: str, goal_id: str, strength: float = 0.5):
        """Link a memory that supports a goal."""
        query = """
        MATCH (m:Memory), (g:Goal)
        WHERE m.id = $memory_id AND g.id = $goal_id
        CREATE (m)-[:SUPPORTS]->(g)
        """
        self._run_write(query, {"memory_id": memory_id, "goal_id": goal_id})

    def link_memory_to_preference(self, memory_id: str, preference_id: str):
        """Link a memory that reveals a preference."""
        query = """
        MATCH (m:Memory), (p:Preference)
        WHERE m.id = $memory_id AND p.id = $preference_id
        CREATE (m)-[:REVEALS]->(p)
        """
        self._run_write(query, {"memory_id": memory_id, "preference_id": preference_id})

    def link_memory_to_temporal(self, memory_id: str, temporal_id: str):
        """Link a memory to a temporal marker."""
        query = """
        MATCH (m:Memory), (t:TemporalMarker)
        WHERE m.id = $memory_id AND t.id = $temporal_id
        CREATE (m)-[:OCCURRED_DURING]->(t)
        """
        self._run_write(query, {"memory_id": memory_id, "temporal_id": temporal_id})

    def link_memories(self, memory_id_1: str, memory_id_2: str, strength: float = 0.5, rel_type: str = ""):
        """Link two related memories."""
        query = """
        MATCH (m1:Memory), (m2:Memory)
        WHERE m1.id = $id1 AND m2.id = $id2
        CREATE (m1)-[:RELATES_TO]->(m2)
        """
        self._run_write(query, {"id1": memory_id_1, "id2": memory_id_2})

    def link_concepts(self, concept_id_1: str, concept_id_2: str, rel_type: str = ""):
        """Link two related concepts."""
        query = """
        MATCH (c1:Concept), (c2:Concept)
        WHERE c1.id = $id1 AND c2.id = $id2
        CREATE (c1)-[:CONCEPT_RELATED_TO]->(c2)
        """
        self._run_write(query, {"id1": concept_id_1, "id2": concept_id_2})

    def link_goals(self, goal_id_1: str, goal_id_2: str):
        """Link a goal that depends on another."""
        query = """
        MATCH (g1:Goal), (g2:Goal)
        WHERE g1.id = $id1 AND g2.id = $id2
        CREATE (g1)-[:DEPENDS_ON]->(g2)
        """
        self._run_write(query, {"id1": goal_id_1, "id2": goal_id_2})

    def link_decisions(self, decision_id_1: str, decision_id_2: str):
        """Link a decision that led to another."""
        query = """
        MATCH (d1:Decision), (d2:Decision)
        WHERE d1.id = $id1 AND d2.id = $id2
        CREATE (d1)-[:LED_TO]->(d2)
        """
        self._run_write(query, {"id1": decision_id_1, "id2": decision_id_2})

    def link_contexts(self, parent_id: str, child_id: str):
        """Link a context as part of another (hierarchy)."""
        query = """
        MATCH (p:Context), (c:Context)
        WHERE p.id = $parent_id AND c.id = $child_id
        CREATE (c)-[:PART_OF]->(p)
        """
        self._run_write(query, {"parent_id": parent_id, "child_id": child_id})

    def mark_contradiction(self, contradiction_id: str, memory_id_1: str, memory_id_2: str):
        """Mark two memories as contradicting each other."""
        query1 = """
        MATCH (c:Contradiction), (m1:Memory)
        WHERE c.id = $cid AND m1.id = $mid1
        CREATE (c)-[:CONFLICTS_WITH]->(m1)
        """
        query2 = """
        MATCH (c:Contradiction), (m2:Memory)
        WHERE c.id = $cid AND m2.id = $mid2
        CREATE (c)-[:CONFLICTS_WITH]->(m2)
        """
        self._run_write(query1, {"cid": contradiction_id, "mid1": memory_id_1})
        self._run_write(query2, {"cid": contradiction_id, "mid2": memory_id_2})

    def resolve_contradiction(self, contradiction_id: str, superseding_memory_id: str, resolution: str):
        """Resolve a contradiction by marking which memory supersedes."""
        query = """
        MATCH (c:Contradiction)
        WHERE c.id = $cid
        SET c.status = 'resolved', c.resolution = $resolution
        """
        self._run_write(query, {"cid": contradiction_id, "resolution": resolution})

        query2 = """
        MATCH (c:Contradiction), (m:Memory)
        WHERE c.id = $cid AND m.id = $mid
        CREATE (c)-[:SUPERSEDES]->(m)
        """
        self._run_write(query2, {"cid": contradiction_id, "mid": superseding_memory_id})

    # ========================================================================
    # QUERY OPERATIONS
    # ========================================================================

    def get_memory(self, memory_id: str) -> Optional[Dict]:
        """Get a memory by ID and update access tracking."""
        # First update access tracking
        update_query = """
        MATCH (m:Memory {id: $id})
        SET m.lastAccessed = $now, m.accessCount = m.accessCount + 1
        """
        self._run_write(update_query, {"id": memory_id, "now": datetime.now().isoformat()})

        # Then retrieve the memory
        query = """
        MATCH (m:Memory {id: $id})
        RETURN m.id AS id, m.content AS content, m.summary AS summary,
               m.created AS created, m.lastAccessed AS lastAccessed,
               m.accessCount AS accessCount, m.confidence AS confidence
        """
        result = self._run_query(query, {"id": memory_id})
        return result[0] if result else None

    def search_memories(self, search_term: str, limit: int = 10) -> List[Dict]:
        """Search memories by content or summary."""
        query = """
        MATCH (m:Memory)
        WHERE m.content CONTAINS $term OR m.summary CONTAINS $term
        RETURN m.id AS id, m.content AS content, m.summary AS summary,
               m.created AS created, m.lastAccessed AS lastAccessed,
               m.accessCount AS accessCount, m.confidence AS confidence
        ORDER BY m.lastAccessed DESC
        LIMIT $limit
        """
        return self._run_query(query, {"term": search_term, "limit": limit})

    def get_related_memories(self, memory_id: str, hops: int = 2, limit: int = 20) -> List[Dict]:
        """Get memories related to a given memory through shared concepts/keywords/topics."""
        # KùzuDB doesn't support variable-length paths the same way, so we use a simpler approach
        # Find memories that share concepts, keywords, or topics with the given memory
        query = """
        MATCH (m:Memory {id: $id})-[:HAS_CONCEPT]->(c:Concept)<-[:HAS_CONCEPT]-(related:Memory)
        WHERE related.id <> $id
        RETURN DISTINCT related.id AS id, related.content AS content, related.summary AS summary,
               related.created AS created, related.lastAccessed AS lastAccessed,
               related.accessCount AS accessCount, related.confidence AS confidence
        LIMIT $limit
        """
        results = self._run_query(query, {"id": memory_id, "limit": limit})

        # Also check keyword relationships
        if len(results) < limit:
            query2 = """
            MATCH (m:Memory {id: $id})-[:HAS_KEYWORD]->(k:Keyword)<-[:HAS_KEYWORD]-(related:Memory)
            WHERE related.id <> $id
            RETURN DISTINCT related.id AS id, related.content AS content, related.summary AS summary,
                   related.created AS created, related.lastAccessed AS lastAccessed,
                   related.accessCount AS accessCount, related.confidence AS confidence
            LIMIT $remaining
            """
            remaining = limit - len(results)
            keyword_results = self._run_query(query2, {"id": memory_id, "remaining": remaining})
            # Merge results avoiding duplicates
            seen_ids = {r["id"] for r in results}
            for r in keyword_results:
                if r["id"] not in seen_ids:
                    results.append(r)
                    seen_ids.add(r["id"])

        return results[:limit]

    def get_memories_by_concept(self, concept_name: str, limit: int = 20) -> List[Dict]:
        """Get all memories associated with a concept."""
        query = """
        MATCH (m:Memory)-[:HAS_CONCEPT]->(c:Concept {name: $name})
        RETURN m.id AS id, m.content AS content, m.summary AS summary,
               m.created AS created, m.lastAccessed AS lastAccessed,
               m.accessCount AS accessCount, m.confidence AS confidence
        ORDER BY m.lastAccessed DESC
        LIMIT $limit
        """
        return self._run_query(query, {"name": concept_name, "limit": limit})

    def get_memories_by_keyword(self, keyword: str, limit: int = 20) -> List[Dict]:
        """Get all memories associated with a keyword."""
        query = """
        MATCH (m:Memory)-[:HAS_KEYWORD]->(k:Keyword {term: $term})
        RETURN m.id AS id, m.content AS content, m.summary AS summary,
               m.created AS created, m.lastAccessed AS lastAccessed,
               m.accessCount AS accessCount, m.confidence AS confidence
        ORDER BY m.lastAccessed DESC
        LIMIT $limit
        """
        return self._run_query(query, {"term": keyword, "limit": limit})

    def get_memories_by_topic(self, topic_name: str, limit: int = 20) -> List[Dict]:
        """Get all memories belonging to a topic."""
        query = """
        MATCH (m:Memory)-[:BELONGS_TO]->(t:Topic {name: $name})
        RETURN m.id AS id, m.content AS content, m.summary AS summary,
               m.created AS created, m.lastAccessed AS lastAccessed,
               m.accessCount AS accessCount, m.confidence AS confidence
        ORDER BY m.lastAccessed DESC
        LIMIT $limit
        """
        return self._run_query(query, {"name": topic_name, "limit": limit})

    def get_memories_by_entity(self, entity_name: str, limit: int = 20) -> List[Dict]:
        """Get all memories mentioning an entity."""
        query = """
        MATCH (m:Memory)-[:MENTIONS]->(e:Entity {name: $name})
        RETURN m.id AS id, m.content AS content, m.summary AS summary,
               m.created AS created, m.lastAccessed AS lastAccessed,
               m.accessCount AS accessCount, m.confidence AS confidence
        ORDER BY m.lastAccessed DESC
        LIMIT $limit
        """
        return self._run_query(query, {"name": entity_name, "limit": limit})

    def get_open_questions(self) -> List[Dict]:
        """Get all open questions."""
        query = """
        MATCH (q:Question)
        WHERE q.status = 'open' OR q.status = 'partial'
        RETURN q.id AS id, q.text AS text, q.status AS status,
               q.answeredDate AS answeredDate, q.created AS created
        ORDER BY q.created DESC
        """
        return self._run_query(query)

    def get_active_goals(self) -> List[Dict]:
        """Get all active goals."""
        query = """
        MATCH (g:Goal {status: 'active'})
        RETURN g.id AS id, g.description AS description, g.status AS status,
               g.priority AS priority, g.targetDate AS targetDate, g.created AS created
        ORDER BY g.priority ASC, g.created ASC
        """
        return self._run_query(query)

    def get_unresolved_contradictions(self) -> List[Dict]:
        """Get all unresolved contradictions with their conflicting memories."""
        query = """
        MATCH (c:Contradiction {status: 'unresolved'})-[:CONFLICTS_WITH]->(m:Memory)
        RETURN c.id AS contradiction_id, c.description AS description,
               m.id AS memory_id, m.summary AS memory_summary
        """
        results = self._run_query(query)

        # Group by contradiction
        contradictions = {}
        for r in results:
            cid = r["contradiction_id"]
            if cid not in contradictions:
                contradictions[cid] = {
                    "id": cid,
                    "description": r["description"],
                    "memories": []
                }
            contradictions[cid]["memories"].append({
                "id": r["memory_id"],
                "summary": r["memory_summary"]
            })

        return list(contradictions.values())

    def get_preferences_by_category(self, category: str) -> List[Dict]:
        """Get all preferences in a category."""
        query = """
        MATCH (p:Preference {category: $category})
        RETURN p.id AS id, p.category AS category, p.preference AS preference,
               p.strength AS strength, p.observations AS observations, p.created AS created
        ORDER BY p.strength DESC
        """
        return self._run_query(query, {"category": category})

    def get_decision_chain(self, decision_id: str) -> List[Dict]:
        """Get decisions related to a given decision."""
        # Get decisions that led to this one
        query1 = """
        MATCH (d1:Decision)-[:LED_TO]->(d2:Decision {id: $id})
        RETURN d1.id AS id, d1.description AS description, d1.rationale AS rationale,
               d1.date AS date, d1.outcome AS outcome, 'predecessor' AS relation
        """
        # Get decisions this one led to
        query2 = """
        MATCH (d1:Decision {id: $id})-[:LED_TO]->(d2:Decision)
        RETURN d2.id AS id, d2.description AS description, d2.rationale AS rationale,
               d2.date AS date, d2.outcome AS outcome, 'successor' AS relation
        """
        results = self._run_query(query1, {"id": decision_id})
        results.extend(self._run_query(query2, {"id": decision_id}))
        return results

    # ========================================================================
    # DIRECTORY OPERATIONS (for markdown index)
    # ========================================================================

    def get_all_nodes_summary(self) -> Dict[str, List[Dict]]:
        """Get a summary of all nodes for the directory index."""
        summary = {}

        # Define queries for each node type
        node_queries = {
            "Memory": "MATCH (n:Memory) RETURN n.id AS id, n.summary AS summary, n.content AS content, n.created AS created",
            "Concept": "MATCH (n:Concept) RETURN n.id AS id, n.name AS name, n.description AS description, n.created AS created",
            "Keyword": "MATCH (n:Keyword) RETURN n.id AS id, n.term AS term, n.created AS created",
            "Topic": "MATCH (n:Topic) RETURN n.id AS id, n.name AS name, n.description AS description, n.created AS created",
            "Entity": "MATCH (n:Entity) RETURN n.id AS id, n.name AS name, n.type AS type, n.description AS description, n.created AS created",
            "Source": "MATCH (n:Source) RETURN n.id AS id, n.type AS type, n.reference AS reference, n.title AS title, n.created AS created",
            "Decision": "MATCH (n:Decision) RETURN n.id AS id, n.description AS description, n.rationale AS rationale, n.date AS date",
            "Goal": "MATCH (n:Goal) RETURN n.id AS id, n.description AS description, n.status AS status, n.priority AS priority, n.created AS created",
            "Question": "MATCH (n:Question) RETURN n.id AS id, n.text AS text, n.status AS status, n.created AS created",
            "Context": "MATCH (n:Context) RETURN n.id AS id, n.name AS name, n.type AS type, n.status AS status, n.created AS created",
            "Preference": "MATCH (n:Preference) RETURN n.id AS id, n.category AS category, n.preference AS preference, n.strength AS strength, n.created AS created",
            "TemporalMarker": "MATCH (n:TemporalMarker) RETURN n.id AS id, n.type AS type, n.description AS description, n.created AS created",
            "Contradiction": "MATCH (n:Contradiction) RETURN n.id AS id, n.description AS description, n.status AS status, n.created AS created"
        }

        for node_type, query in node_queries.items():
            try:
                result = self._run_query(query)
                summary[node_type] = result
            except Exception:
                summary[node_type] = []

        return summary

    def get_node_counts(self) -> Dict[str, int]:
        """Get counts of each node type."""
        counts = {}
        node_types = [
            "Memory", "Concept", "Keyword", "Topic", "Entity", "Source",
            "Decision", "Goal", "Question", "Context", "Preference",
            "TemporalMarker", "Contradiction"
        ]

        for node_type in node_types:
            try:
                query = f"MATCH (n:{node_type}) RETURN count(n) AS cnt"
                result = self._run_query(query)
                counts[node_type] = result[0]["cnt"] if result else 0
            except Exception:
                counts[node_type] = 0

        return counts

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

    def delete_all_data(self):
        """Delete all data from the database (useful for testing)."""
        node_types = [
            "Memory", "Concept", "Keyword", "Topic", "Entity", "Source",
            "Decision", "Goal", "Question", "Context", "Preference",
            "TemporalMarker", "Contradiction"
        ]
        for node_type in node_types:
            try:
                self._run_write(f"MATCH (n:{node_type}) DETACH DELETE n")
            except Exception:
                pass


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_client(db_path: str = None) -> MemoryGraphClient:
    """Create a new memory graph client."""
    return MemoryGraphClient(db_path=db_path)


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
