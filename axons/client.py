"""MemoryGraphClient — core graph database client for Axons memory system."""

import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

import real_ladybug

from .enums import (
    EntityType, Permeability,
)
from .models import (
    Memory, Concept, Keyword, Topic, Entity, Source,
    Decision, Goal, Question, Context, Preference,
    TemporalMarker, Contradiction, Compartment,
    _validate_range,
)
from .plasticity import PlasticityConfig
from .permeability import PermeabilityMixin


class MemoryGraphClient(PermeabilityMixin):
    """Client for interacting with the LadybugDB memory database."""

    def __init__(self, db_path: str = None, plasticity_config: PlasticityConfig = None):
        """
        Initialize connection to LadybugDB.

        Args:
            db_path: Path to the database directory. If None, uses default location
                     in user's home directory (~/.axons_memory_db)
            plasticity_config: Configuration for brain-like plasticity behavior.
                              If None, uses PlasticityConfig.default()
        """
        if db_path is None:
            db_path = os.path.join(Path.home(), ".axons_memory_db")

        self.db_path = db_path
        self.db = real_ladybug.Database(db_path)
        self.conn = real_ladybug.Connection(self.db)
        self._schema_initialized = False
        self._closed = False
        self.plasticity = plasticity_config or PlasticityConfig.default()
        self._access_cycle = 0  # Track access cycles for decay calculations
        self._active_compartment_id: Optional[str] = None  # Active compartment for new memories

    def _check_closed(self):
        """Raise RuntimeError if client has been closed."""
        if self._closed:
            raise RuntimeError("Client is closed")

    def close(self):
        """Close the database connection."""
        self._closed = True
        # LadybugDB connections are automatically managed, but we can clear references
        self.conn = None
        self.db = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def begin_transaction(self):
        """Begin a database transaction."""
        self._check_closed()
        self.conn.execute("BEGIN TRANSACTION")

    def commit(self):
        """Commit the current transaction."""
        self._check_closed()
        self.conn.execute("COMMIT")

    def rollback(self):
        """Roll back the current transaction."""
        self._check_closed()
        self.conn.execute("ROLLBACK")

    def _run_query(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict]:
        """Execute a Cypher query and return results."""
        self._check_closed()
        if parameters:
            result = self.conn.execute(query, parameters)
        else:
            result = self.conn.execute(query)

        rows = []
        while result.has_next():
            row = result.get_next()
            col_names = result.get_column_names()
            row_dict = {}
            for i, name in enumerate(col_names):
                row_dict[name] = row[i]
            rows.append(row_dict)
        return rows

    def _run_write(self, query: str, parameters: Dict[str, Any] = None) -> None:
        """Execute a data write query. All errors are propagated."""
        self._check_closed()
        if parameters:
            self.conn.execute(query, parameters)
        else:
            self.conn.execute(query)

    def _run_schema_write(self, query: str) -> None:
        """Execute a schema write query."""
        self._check_closed()
        self.conn.execute(query)

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
                confidence DOUBLE,
                permeability STRING
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
            )""",
            """CREATE NODE TABLE IF NOT EXISTS Compartment (
                id STRING PRIMARY KEY,
                name STRING,
                permeability STRING,
                allowExternalConnections BOOLEAN,
                description STRING,
                created STRING
            )"""
        ]

        # Create relationship tables with properties for brain-like plasticity
        # Edge weights enable Hebbian learning, decay, and relevance-based retrieval
        rel_tables = [
            # Memory associations with strength/relevance weights
            "CREATE REL TABLE IF NOT EXISTS HAS_CONCEPT (FROM Memory TO Concept, relevance DOUBLE)",
            "CREATE REL TABLE IF NOT EXISTS HAS_KEYWORD (FROM Memory TO Keyword)",
            "CREATE REL TABLE IF NOT EXISTS BELONGS_TO (FROM Memory TO Topic, isPrimary BOOLEAN)",
            "CREATE REL TABLE IF NOT EXISTS MENTIONS (FROM Memory TO Entity, role STRING)",
            "CREATE REL TABLE IF NOT EXISTS FROM_SOURCE (FROM Memory TO Source, excerpt STRING)",
            "CREATE REL TABLE IF NOT EXISTS IN_CONTEXT (FROM Memory TO Context)",
            "CREATE REL TABLE IF NOT EXISTS INFORMED (FROM Memory TO Decision)",
            "CREATE REL TABLE IF NOT EXISTS PARTIALLY_ANSWERS (FROM Memory TO Question, completeness DOUBLE)",
            "CREATE REL TABLE IF NOT EXISTS SUPPORTS (FROM Memory TO Goal, strength DOUBLE)",
            "CREATE REL TABLE IF NOT EXISTS REVEALS (FROM Memory TO Preference)",
            "CREATE REL TABLE IF NOT EXISTS OCCURRED_DURING (FROM Memory TO TemporalMarker)",
            # Memory-to-memory with synaptic-like strength and permeability for data flow control
            "CREATE REL TABLE IF NOT EXISTS RELATES_TO (FROM Memory TO Memory, strength DOUBLE, relType STRING, permeability STRING)",
            # Compartmentalization - memory isolation and data flow control
            "CREATE REL TABLE IF NOT EXISTS IN_COMPARTMENT (FROM Memory TO Compartment)",
            # Concept relationships
            "CREATE REL TABLE IF NOT EXISTS CONCEPT_RELATED_TO (FROM Concept TO Concept, relType STRING)",
            # Goal/Decision/Context hierarchies
            "CREATE REL TABLE IF NOT EXISTS DEPENDS_ON (FROM Goal TO Goal)",
            "CREATE REL TABLE IF NOT EXISTS LED_TO (FROM Decision TO Decision)",
            "CREATE REL TABLE IF NOT EXISTS PART_OF (FROM Context TO Context)",
            # Contradiction tracking
            "CREATE REL TABLE IF NOT EXISTS CONFLICTS_WITH (FROM Contradiction TO Memory)",
            "CREATE REL TABLE IF NOT EXISTS SUPERSEDES (FROM Contradiction TO Memory)"
        ]

        # Execute all schema statements
        for stmt in node_tables + rel_tables:
            self._run_schema_write(stmt)

        # Set up full-text search index on Memory content and summary
        self._fts_available = False
        try:
            self._run_schema_write("INSTALL fts")
            self._run_schema_write("LOAD EXTENSION fts")
            self._run_schema_write(
                'CALL CREATE_FTS_INDEX("Memory", "memory_fts", ["content", "summary"])'
            )
            self._fts_available = True
        except Exception:
            pass  # FTS is optional — search_memories falls back to CONTAINS

        self._schema_initialized = True

    # ========================================================================
    # CREATE OPERATIONS
    # ========================================================================

    def create_memory(self, memory: Memory, compartment_id: str = None) -> str:
        """Create a new memory node.

        Args:
            memory: The Memory object to create
            compartment_id: Optional compartment ID. If None, uses active compartment.
                           Pass empty string "" to create without compartment.
        """
        query = """
        CREATE (m:Memory {
            id: $id,
            content: $content,
            summary: $summary,
            created: $created,
            lastAccessed: $last_accessed,
            accessCount: $access_count,
            confidence: $confidence,
            permeability: $permeability
        })
        """
        self._run_write(query, {
            "id": memory.id,
            "content": memory.content,
            "summary": memory.summary,
            "created": memory.created.isoformat(),
            "last_accessed": memory.last_accessed.isoformat(),
            "access_count": memory.access_count,
            "confidence": memory.confidence,
            "permeability": memory.permeability.value
        })

        # Add to compartment if specified or active
        effective_compartment = compartment_id if compartment_id is not None else self._active_compartment_id
        if effective_compartment:  # Not None and not empty string
            self.add_memory_to_compartment(memory.id, effective_compartment)

        return memory.id

    def create_concept(self, concept: Concept) -> str:
        """Create a new concept node or return existing."""
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
    # COMPARTMENT OPERATIONS
    # ========================================================================

    def create_compartment(self, compartment: Compartment) -> str:
        """Create a new compartment for memory isolation."""
        check_query = "MATCH (c:Compartment) WHERE c.name = $name RETURN c.id AS id"
        result = self._run_query(check_query, {"name": compartment.name})
        if result:
            return result[0]["id"]

        query = """
        CREATE (c:Compartment {
            id: $id,
            name: $name,
            permeability: $permeability,
            allowExternalConnections: $allow_external,
            description: $description,
            created: $created
        })
        """
        self._run_write(query, {
            "id": compartment.id,
            "name": compartment.name,
            "permeability": compartment.permeability.value,
            "allow_external": compartment.allow_external_connections,
            "description": compartment.description,
            "created": compartment.created.isoformat()
        })
        return compartment.id

    def get_compartment(self, compartment_id: str) -> Optional[Dict]:
        """Get a compartment by ID."""
        query = """
        MATCH (c:Compartment {id: $id})
        RETURN c.id AS id, c.name AS name, c.permeability AS permeability,
               c.allowExternalConnections AS allowExternalConnections,
               c.description AS description, c.created AS created
        """
        result = self._run_query(query, {"id": compartment_id})
        return result[0] if result else None

    def get_compartment_by_name(self, name: str) -> Optional[Dict]:
        """Get a compartment by name."""
        query = """
        MATCH (c:Compartment {name: $name})
        RETURN c.id AS id, c.name AS name, c.permeability AS permeability,
               c.allowExternalConnections AS allowExternalConnections,
               c.description AS description, c.created AS created
        """
        result = self._run_query(query, {"name": name})
        return result[0] if result else None

    def update_compartment(self, compartment_id: str, permeability: Permeability = None,
                          allow_external_connections: bool = None, description: str = None):
        """Update compartment properties."""
        updates = []
        params = {"id": compartment_id}

        if permeability is not None:
            updates.append("c.permeability = $permeability")
            params["permeability"] = permeability.value
        if allow_external_connections is not None:
            updates.append("c.allowExternalConnections = $allow_external")
            params["allow_external"] = allow_external_connections
        if description is not None:
            updates.append("c.description = $description")
            params["description"] = description

        if updates:
            query = f"MATCH (c:Compartment {{id: $id}}) SET {', '.join(updates)}"
            self._run_write(query, params)

    def delete_compartment(self, compartment_id: str, reassign_memories: bool = True):
        """Delete a compartment.

        Args:
            compartment_id: ID of compartment to delete
            reassign_memories: If True, memories are moved to no compartment.
                              If False, deletion fails if compartment has memories.
        """
        if not reassign_memories:
            check_query = """
            MATCH (m:Memory)-[:IN_COMPARTMENT]->(c:Compartment {id: $id})
            RETURN COUNT(m) AS count
            """
            result = self._run_query(check_query, {"id": compartment_id})
            if result and result[0]["count"] > 0:
                raise ValueError(f"Compartment has {result[0]['count']} memories. "
                               "Set reassign_memories=True to remove them from compartment.")

        # Delete relationships first
        self._run_write(
            "MATCH (m:Memory)-[r:IN_COMPARTMENT]->(c:Compartment {id: $id}) DELETE r",
            {"id": compartment_id}
        )
        # Delete compartment
        self._run_write("MATCH (c:Compartment {id: $id}) DELETE c", {"id": compartment_id})

    def set_active_compartment(self, compartment_id: Optional[str]):
        """Set the active compartment for new memories.

        Args:
            compartment_id: Compartment ID, or None to create memories without compartment
        """
        self._active_compartment_id = compartment_id

    def get_active_compartment(self) -> Optional[str]:
        """Get the currently active compartment ID."""
        return self._active_compartment_id

    def add_memory_to_compartment(self, memory_ids, compartment_id: str):
        """Add one or more memories to a compartment.

        A memory can be in multiple compartments (overlapping compartments).
        Adding to a compartment the memory is already in is a no-op (MERGE).

        Args:
            memory_ids: Single memory ID (str) or list of memory IDs
            compartment_id: The compartment to add to
        """
        if isinstance(memory_ids, str):
            memory_ids = [memory_ids]

        query = """
        UNWIND $mids AS mid
        MATCH (m:Memory {id: mid}), (c:Compartment {id: $cid})
        MERGE (m)-[:IN_COMPARTMENT]->(c)
        """
        self._run_write(query, {"mids": memory_ids, "cid": compartment_id})

    def remove_memory_from_compartment(self, memory_ids, compartment_id: str = None):
        """Remove one or more memories from compartment(s).

        Args:
            memory_ids: Single memory ID (str) or list of memory IDs
            compartment_id: Specific compartment to remove from. If None, removes from ALL compartments.
        """
        if isinstance(memory_ids, str):
            memory_ids = [memory_ids]

        for memory_id in memory_ids:
            if compartment_id:
                self._run_write(
                    "MATCH (m:Memory {id: $mid})-[r:IN_COMPARTMENT]->(c:Compartment {id: $cid}) DELETE r",
                    {"mid": memory_id, "cid": compartment_id}
                )
            else:
                self._run_write(
                    "MATCH (m:Memory {id: $mid})-[r:IN_COMPARTMENT]->() DELETE r",
                    {"mid": memory_id}
                )

    def get_memory_compartments(self, memory_id: str) -> List[Dict]:
        """Get all compartments a memory belongs to.

        Returns:
            List of compartment dicts, empty if memory is global (no compartments).
        """
        query = """
        MATCH (m:Memory {id: $mid})-[:IN_COMPARTMENT]->(c:Compartment)
        RETURN c.id AS id, c.name AS name, c.permeability AS permeability,
               c.allowExternalConnections AS allowExternalConnections
        """
        return self._run_query(query, {"mid": memory_id})

    def get_memories_in_compartment(self, compartment_id: str, limit: int = 100) -> List[Dict]:
        """Get all memories in a compartment."""
        query = """
        MATCH (m:Memory)-[:IN_COMPARTMENT]->(c:Compartment {id: $cid})
        RETURN m.id AS id, m.summary AS summary, m.content AS content,
               m.created AS created, m.confidence AS confidence
        LIMIT $limit
        """
        return self._run_query(query, {"cid": compartment_id, "limit": limit})

    # ========================================================================
    # RELATIONSHIP OPERATIONS
    # ========================================================================

    def link_memory_to_concept(self, memory_id: str, concept_id: str, relevance: float = 1.0):
        """Link a memory to a concept with relevance weight (0-1)."""
        _validate_range(relevance, 0.0, 1.0, "relevance")
        query = """
        MATCH (m:Memory), (c:Concept)
        WHERE m.id = $memory_id AND c.id = $concept_id
        MERGE (m)-[r:HAS_CONCEPT]->(c)
        ON CREATE SET r.relevance = $relevance
        """
        self._run_write(query, {"memory_id": memory_id, "concept_id": concept_id, "relevance": relevance})

    def link_memory_to_keyword(self, memory_id: str, keyword_id: str):
        """Link a memory to a keyword."""
        query = """
        MATCH (m:Memory), (k:Keyword)
        WHERE m.id = $memory_id AND k.id = $keyword_id
        MERGE (m)-[:HAS_KEYWORD]->(k)
        """
        self._run_write(query, {"memory_id": memory_id, "keyword_id": keyword_id})

    def link_memory_to_topic(self, memory_id: str, topic_id: str, primary: bool = False):
        """Link a memory to a topic, optionally marking it as the primary topic."""
        query = """
        MATCH (m:Memory), (t:Topic)
        WHERE m.id = $memory_id AND t.id = $topic_id
        MERGE (m)-[r:BELONGS_TO]->(t)
        ON CREATE SET r.isPrimary = $is_primary
        """
        self._run_write(query, {"memory_id": memory_id, "topic_id": topic_id, "is_primary": primary})

    def link_memory_to_entity(self, memory_id: str, entity_id: str, role: str = ""):
        """Link a memory to an entity with an optional role description."""
        query = """
        MATCH (m:Memory), (e:Entity)
        WHERE m.id = $memory_id AND e.id = $entity_id
        MERGE (m)-[r:MENTIONS]->(e)
        ON CREATE SET r.role = $role
        """
        self._run_write(query, {"memory_id": memory_id, "entity_id": entity_id, "role": role})

    def link_memory_to_source(self, memory_id: str, source_id: str, excerpt: str = ""):
        """Link a memory to its source with an optional excerpt."""
        query = """
        MATCH (m:Memory), (s:Source)
        WHERE m.id = $memory_id AND s.id = $source_id
        MERGE (m)-[r:FROM_SOURCE]->(s)
        ON CREATE SET r.excerpt = $excerpt
        """
        self._run_write(query, {"memory_id": memory_id, "source_id": source_id, "excerpt": excerpt})

    def link_memory_to_context(self, memory_id: str, context_id: str):
        """Link a memory to a context."""
        query = """
        MATCH (m:Memory), (c:Context)
        WHERE m.id = $memory_id AND c.id = $context_id
        MERGE (m)-[:IN_CONTEXT]->(c)
        """
        self._run_write(query, {"memory_id": memory_id, "context_id": context_id})

    def link_memory_to_decision(self, memory_id: str, decision_id: str):
        """Link a memory that informed a decision."""
        query = """
        MATCH (m:Memory), (d:Decision)
        WHERE m.id = $memory_id AND d.id = $decision_id
        MERGE (m)-[:INFORMED]->(d)
        """
        self._run_write(query, {"memory_id": memory_id, "decision_id": decision_id})

    def link_memory_to_question(self, memory_id: str, question_id: str, completeness: float = 0.5):
        """Link a memory that partially answers a question."""
        _validate_range(completeness, 0.0, 1.0, "completeness")
        query = """
        MATCH (m:Memory), (q:Question)
        WHERE m.id = $memory_id AND q.id = $question_id
        MERGE (m)-[r:PARTIALLY_ANSWERS]->(q)
        ON CREATE SET r.completeness = $completeness
        """
        self._run_write(query, {"memory_id": memory_id, "question_id": question_id, "completeness": completeness})

    def link_memory_to_goal(self, memory_id: str, goal_id: str, strength: float = 0.5):
        """Link a memory that supports a goal."""
        _validate_range(strength, 0.0, 1.0, "strength")
        query = """
        MATCH (m:Memory), (g:Goal)
        WHERE m.id = $memory_id AND g.id = $goal_id
        MERGE (m)-[r:SUPPORTS]->(g)
        ON CREATE SET r.strength = $strength
        """
        self._run_write(query, {"memory_id": memory_id, "goal_id": goal_id, "strength": strength})

    def link_memory_to_preference(self, memory_id: str, preference_id: str):
        """Link a memory that reveals a preference."""
        query = """
        MATCH (m:Memory), (p:Preference)
        WHERE m.id = $memory_id AND p.id = $preference_id
        MERGE (m)-[:REVEALS]->(p)
        """
        self._run_write(query, {"memory_id": memory_id, "preference_id": preference_id})

    def link_memory_to_temporal(self, memory_id: str, temporal_id: str):
        """Link a memory to a temporal marker."""
        query = """
        MATCH (m:Memory), (t:TemporalMarker)
        WHERE m.id = $memory_id AND t.id = $temporal_id
        MERGE (m)-[:OCCURRED_DURING]->(t)
        """
        self._run_write(query, {"memory_id": memory_id, "temporal_id": temporal_id})

    def link_memories(self, memory_id_1: str, memory_id_2: str, strength: float = 0.5,
                      rel_type: str = "", permeability: Permeability = None,
                      check_compartments: bool = False) -> bool:
        """Link two related memories with a synaptic-like strength.

        Args:
            memory_id_1: First memory ID (connection owner)
            memory_id_2: Second memory ID
            strength: Connection weight (0-1), can be modified by plasticity operations
            rel_type: Optional relationship type label
            permeability: Optional permeability override for this connection.
                         If None, uses OPEN (inherits from compartments).
            check_compartments: If True, checks if connection is allowed by
                               compartment rules and returns False if blocked.

        Returns:
            True if connection was created, False if blocked by compartment rules.
        """
        _validate_range(strength, 0.0, 1.0, "strength")
        if check_compartments and not self.can_form_connection(memory_id_1, memory_id_2):
            return False

        perm_value = permeability.value if permeability else Permeability.OPEN.value
        query = """
        MATCH (m1:Memory), (m2:Memory)
        WHERE m1.id = $id1 AND m2.id = $id2
        MERGE (m1)-[r:RELATES_TO]->(m2)
        ON CREATE SET r.strength = $strength, r.relType = $relType, r.permeability = $perm
        """
        self._run_write(query, {
            "id1": memory_id_1, "id2": memory_id_2,
            "strength": strength, "relType": rel_type, "perm": perm_value
        })
        return True

    def link_concepts(self, concept_id_1: str, concept_id_2: str, rel_type: str = ""):
        """Link two related concepts."""
        query = """
        MATCH (c1:Concept), (c2:Concept)
        WHERE c1.id = $id1 AND c2.id = $id2
        MERGE (c1)-[r:CONCEPT_RELATED_TO]->(c2)
        ON CREATE SET r.relType = $relType
        """
        self._run_write(query, {"id1": concept_id_1, "id2": concept_id_2, "relType": rel_type})

    def link_goals(self, goal_id_1: str, goal_id_2: str):
        """Link a goal that depends on another."""
        query = """
        MATCH (g1:Goal), (g2:Goal)
        WHERE g1.id = $id1 AND g2.id = $id2
        MERGE (g1)-[:DEPENDS_ON]->(g2)
        """
        self._run_write(query, {"id1": goal_id_1, "id2": goal_id_2})

    def link_decisions(self, decision_id_1: str, decision_id_2: str):
        """Link a decision that led to another."""
        query = """
        MATCH (d1:Decision), (d2:Decision)
        WHERE d1.id = $id1 AND d2.id = $id2
        MERGE (d1)-[:LED_TO]->(d2)
        """
        self._run_write(query, {"id1": decision_id_1, "id2": decision_id_2})

    def link_contexts(self, parent_id: str, child_id: str):
        """Link a context as part of another (hierarchy)."""
        query = """
        MATCH (p:Context), (c:Context)
        WHERE p.id = $parent_id AND c.id = $child_id
        MERGE (c)-[:PART_OF]->(p)
        """
        self._run_write(query, {"parent_id": parent_id, "child_id": child_id})

    def mark_contradiction(self, contradiction_id: str, memory_id_1: str, memory_id_2: str):
        """Mark two memories as contradicting each other."""
        query1 = """
        MATCH (c:Contradiction), (m1:Memory)
        WHERE c.id = $cid AND m1.id = $mid1
        MERGE (c)-[:CONFLICTS_WITH]->(m1)
        """
        query2 = """
        MATCH (c:Contradiction), (m2:Memory)
        WHERE c.id = $cid AND m2.id = $mid2
        MERGE (c)-[:CONFLICTS_WITH]->(m2)
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
        MERGE (c)-[:SUPERSEDES]->(m)
        """
        self._run_write(query2, {"cid": contradiction_id, "mid": superseding_memory_id})

    # ========================================================================
    # PLASTICITY OPERATIONS (Brain-like learning)
    # ========================================================================

    def strengthen_memory_link(self, memory_id_1: str, memory_id_2: str, amount: float = None):
        """Strengthen the connection between two memories (Hebbian learning)."""
        current = self.get_memory_link_strength(memory_id_1, memory_id_2) or 0.0

        if amount is None:
            effective_amount = self.plasticity.effective_amount('strengthen', current)
        else:
            effective_amount = amount * self.plasticity.learning_rate

        if effective_amount <= 0:
            return

        max_strength = self.plasticity.max_strength
        query = """
        MATCH (m1:Memory)-[r:RELATES_TO]->(m2:Memory)
        WHERE m1.id = $id1 AND m2.id = $id2
        SET r.strength = CASE
            WHEN r.strength + $amount > $max THEN $max
            ELSE r.strength + $amount
        END
        """
        self._run_write(query, {
            "id1": memory_id_1, "id2": memory_id_2,
            "amount": effective_amount, "max": max_strength
        })

    def weaken_memory_link(self, memory_id_1: str, memory_id_2: str, amount: float = None):
        """Weaken the connection between two memories."""
        current = self.get_memory_link_strength(memory_id_1, memory_id_2) or 1.0

        if amount is None:
            effective_amount = self.plasticity.effective_amount('weaken', current)
        else:
            effective_amount = amount * self.plasticity.learning_rate

        if effective_amount <= 0:
            return

        min_strength = self.plasticity.min_strength
        query = """
        MATCH (m1:Memory)-[r:RELATES_TO]->(m2:Memory)
        WHERE m1.id = $id1 AND m2.id = $id2
        SET r.strength = CASE
            WHEN r.strength - $amount < $min THEN $min
            ELSE r.strength - $amount
        END
        """
        self._run_write(query, {
            "id1": memory_id_1, "id2": memory_id_2,
            "amount": effective_amount, "min": min_strength
        })

    def strengthen_concept_relevance(self, memory_id: str, concept_id: str, amount: float = None):
        """Increase the relevance of a concept to a memory."""
        if amount is None:
            amount = self.plasticity.effective_amount('strengthen', 0.5)

        if amount <= 0:
            return

        query = """
        MATCH (m:Memory)-[r:HAS_CONCEPT]->(c:Concept)
        WHERE m.id = $memory_id AND c.id = $concept_id
        SET r.relevance = CASE
            WHEN r.relevance + $amount > 1.0 THEN 1.0
            ELSE r.relevance + $amount
        END
        """
        self._run_write(query, {"memory_id": memory_id, "concept_id": concept_id, "amount": amount})

    def weaken_concept_relevance(self, memory_id: str, concept_id: str, amount: float = None):
        """Decrease the relevance of a concept to a memory."""
        if amount is None:
            amount = self.plasticity.effective_amount('weaken', 0.5)

        if amount <= 0:
            return

        query = """
        MATCH (m:Memory)-[r:HAS_CONCEPT]->(c:Concept)
        WHERE m.id = $memory_id AND c.id = $concept_id
        SET r.relevance = CASE
            WHEN r.relevance - $amount < 0.0 THEN 0.0
            ELSE r.relevance - $amount
        END
        """
        self._run_write(query, {"memory_id": memory_id, "concept_id": concept_id, "amount": amount})

    def get_memory_link_strength(self, memory_id_1: str, memory_id_2: str) -> Optional[float]:
        """Get the current connection strength between two memories."""
        query = """
        MATCH (m1:Memory)-[r:RELATES_TO]->(m2:Memory)
        WHERE m1.id = $id1 AND m2.id = $id2
        RETURN r.strength AS strength
        """
        result = self._run_query(query, {"id1": memory_id_1, "id2": memory_id_2})
        return result[0]["strength"] if result else None

    def apply_hebbian_learning(self, memory_ids: List[str], amount: float = None,
                               respect_compartments: bool = True):
        """Strengthen connections between all memories accessed together."""
        for i, id1 in enumerate(memory_ids):
            for id2 in memory_ids[i+1:]:
                # Check both directions for existing connections
                strength_fwd = self.get_memory_link_strength(id1, id2)
                strength_rev = self.get_memory_link_strength(id2, id1)
                has_connection = strength_fwd is not None or strength_rev is not None

                if not has_connection and self.plasticity.hebbian_creates_connections:
                    if respect_compartments and not self.can_form_connection(id1, id2):
                        continue
                    # Create new bidirectional connections (MERGE prevents duplicates)
                    initial = self.plasticity.get_initial_strength(explicit=False)
                    self.link_memories(id1, id2, initial, "hebbian")
                    self.link_memories(id2, id1, initial, "hebbian")
                elif has_connection:
                    effective = amount if amount else self.plasticity.effective_amount(
                        'hebbian', strength_fwd or strength_rev)
                    # Strengthen whichever directions exist
                    if strength_fwd is not None:
                        self.strengthen_memory_link(id1, id2, effective)
                    if strength_rev is not None:
                        self.strengthen_memory_link(id2, id1, effective)

    def decay_weak_connections(self, threshold: float = None, decay_amount: float = None):
        """Weaken connections that are below threshold."""
        if threshold is None:
            threshold = self.plasticity.decay_threshold
        if decay_amount is None:
            decay_amount = self.plasticity.effective_amount('decay', 0.5)

        if decay_amount <= 0:
            return

        min_strength = self.plasticity.min_strength

        if self.plasticity.decay_all:
            query = """
            MATCH (m1:Memory)-[r:RELATES_TO]->(m2:Memory)
            SET r.strength = CASE
                WHEN r.strength - $decay_amount < $min THEN $min
                ELSE r.strength - $decay_amount
            END
            """
            self._run_write(query, {"decay_amount": decay_amount, "min": min_strength})
        else:
            query = """
            MATCH (m1:Memory)-[r:RELATES_TO]->(m2:Memory)
            WHERE r.strength < $threshold
            SET r.strength = CASE
                WHEN r.strength - $decay_amount < $min THEN $min
                ELSE r.strength - $decay_amount
            END
            """
            self._run_write(query, {
                "threshold": threshold, "decay_amount": decay_amount, "min": min_strength
            })

        if self.plasticity.auto_prune:
            self.prune_dead_connections()

    def prune_dead_connections(self, min_strength: float = None):
        """Remove connections that have decayed to near-zero."""
        if min_strength is None:
            min_strength = self.plasticity.prune_threshold

        query = """
        MATCH (m1:Memory)-[r:RELATES_TO]->(m2:Memory)
        WHERE r.strength <= $min_strength
        DELETE r
        """
        self._run_write(query, {"min_strength": min_strength})

    def get_strongest_connections(self, memory_id: str, limit: int = 10,
                                  respect_permeability: bool = True) -> List[Dict]:
        """Get the strongest connections from a memory."""
        fetch_limit = limit * 3 if respect_permeability else limit
        query = """
        MATCH (m:Memory)-[r:RELATES_TO]->(related:Memory)
        WHERE m.id = $memory_id
        RETURN related.id AS id, related.summary AS summary, r.strength AS strength,
               r.permeability AS permeability
        ORDER BY r.strength DESC
        LIMIT $limit
        """
        results = self._run_query(query, {"memory_id": memory_id, "limit": fetch_limit})

        if respect_permeability:
            results = self._filter_by_permeability(memory_id, results)

        return results[:limit]

    def get_weakest_connections(self, memory_id: str, limit: int = 10,
                                respect_permeability: bool = True) -> List[Dict]:
        """Get the weakest connections from a memory (candidates for pruning)."""
        fetch_limit = limit * 3 if respect_permeability else limit
        query = """
        MATCH (m:Memory)-[r:RELATES_TO]->(related:Memory)
        WHERE m.id = $memory_id
        RETURN related.id AS id, related.summary AS summary, r.strength AS strength,
               r.permeability AS permeability
        ORDER BY r.strength ASC
        LIMIT $limit
        """
        results = self._run_query(query, {"memory_id": memory_id, "limit": fetch_limit})

        if respect_permeability:
            results = self._filter_by_permeability(memory_id, results)

        return results[:limit]

    def get_all_connection_strengths(self) -> List[Dict]:
        """Get all memory-to-memory connections with their strengths."""
        query = """
        MATCH (m1:Memory)-[r:RELATES_TO]->(m2:Memory)
        RETURN m1.id AS from_id, m2.id AS to_id, r.strength AS strength
        ORDER BY r.strength DESC
        """
        return self._run_query(query, {})

    def get_connection_statistics(self) -> Dict[str, Any]:
        """Get statistics about all connections in the graph."""
        connections = self.get_all_connection_strengths()
        if not connections:
            return {
                "count": 0, "min": None, "max": None, "avg": None,
                "buckets": {}, "below_threshold": 0
            }

        strengths = [c["strength"] for c in connections]
        threshold = self.plasticity.decay_threshold

        buckets = {f"{i/10:.1f}-{(i+1)/10:.1f}": 0 for i in range(10)}
        for s in strengths:
            bucket_idx = min(int(s * 10), 9)
            bucket_key = f"{bucket_idx/10:.1f}-{(bucket_idx+1)/10:.1f}"
            buckets[bucket_key] += 1

        return {
            "count": len(strengths),
            "min": min(strengths),
            "max": max(strengths),
            "avg": sum(strengths) / len(strengths),
            "buckets": buckets,
            "below_threshold": sum(1 for s in strengths if s < threshold),
            "pruning_candidates": sum(1 for s in strengths if s <= self.plasticity.prune_threshold),
        }

    # === RETRIEVAL-INDUCED MODIFICATION ===

    def _apply_retrieval_effects(self, memory_id: str, via_concept_id: str = None):
        """Apply retrieval-induced modifications when a memory is accessed."""
        if not self.plasticity.retrieval_strengthens:
            return

        amount = self.plasticity.effective_amount('retrieval', 0.5)
        if amount > 0:
            query = """
            MATCH (other:Memory)-[r:RELATES_TO]->(m:Memory {id: $id})
            SET r.strength = CASE
                WHEN r.strength + $amount > $max THEN $max
                ELSE r.strength + $amount
            END
            """
            self._run_write(query, {
                "id": memory_id, "amount": amount, "max": self.plasticity.max_strength
            })

        if via_concept_id:
            self.strengthen_concept_relevance(memory_id, via_concept_id)

        if self.plasticity.retrieval_weakens_competitors:
            self._weaken_competitors(memory_id)

    def _weaken_competitors(self, accessed_memory_id: str):
        """Weaken memories that are related to but weren't accessed."""
        amount = self.plasticity.weaken_amount * self.plasticity.learning_rate * self.plasticity.competitor_distance
        if amount <= 0:
            return

        query = """
        MATCH (accessed:Memory {id: $id})-[:RELATES_TO]-(competitor:Memory)
        MATCH (competitor)-[r:RELATES_TO]-(other:Memory)
        WHERE other.id <> $id
        SET r.strength = CASE
            WHEN r.strength - $amount < $min THEN $min
            ELSE r.strength - $amount
        END
        """
        self._run_write(query, {
            "id": accessed_memory_id,
            "amount": amount,
            "min": self.plasticity.min_strength
        })

    # === MAINTENANCE OPERATIONS ===

    def run_maintenance_cycle(self):
        """Run a full maintenance cycle: decay, prune, update statistics."""
        self._access_cycle += 1
        self.decay_weak_connections()

    def run_aggressive_maintenance(self, cycles: int = 5):
        """Run multiple maintenance cycles to aggressively prune weak connections."""
        for _ in range(cycles):
            self.run_maintenance_cycle()

    def strengthen_goal_connections(self, goal_id: str, amount: float = None):
        """Strengthen all memory connections to a goal."""
        if amount is None:
            amount = self.plasticity.effective_amount('strengthen', 0.5)

        if amount <= 0:
            return

        query = """
        MATCH (m:Memory)-[r:SUPPORTS]->(g:Goal {id: $goal_id})
        SET r.strength = CASE
            WHEN r.strength + $amount > 1.0 THEN 1.0
            ELSE r.strength + $amount
        END
        """
        self._run_write(query, {"goal_id": goal_id, "amount": amount})

    def strengthen_question_connections(self, question_id: str, amount: float = None):
        """Strengthen all memory connections to a question."""
        if amount is None:
            amount = self.plasticity.effective_amount('strengthen', 0.5)

        if amount <= 0:
            return

        query = """
        MATCH (m:Memory)-[r:PARTIALLY_ANSWERS]->(q:Question {id: $question_id})
        SET r.completeness = CASE
            WHEN r.completeness + $amount > 1.0 THEN 1.0
            ELSE r.completeness + $amount
        END
        """
        self._run_write(query, {"question_id": question_id, "amount": amount})

    # === CONFIGURATION MANAGEMENT ===

    def get_plasticity_config(self) -> PlasticityConfig:
        """Get the current plasticity configuration."""
        return self.plasticity

    def set_plasticity_config(self, config: PlasticityConfig):
        """Update the plasticity configuration."""
        self.plasticity = config

    def save_plasticity_config(self, filepath: str):
        """Save plasticity config to a JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.plasticity.to_dict(), f, indent=2)

    def load_plasticity_config(self, filepath: str):
        """Load plasticity config from a JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        self.plasticity = PlasticityConfig.from_dict(data)

    # ========================================================================
    # QUERY OPERATIONS
    # ========================================================================

    def get_memory(self, memory_id: str, apply_retrieval_effects: bool = True) -> Optional[Dict]:
        """Get a memory by ID and update access tracking."""
        update_query = """
        MATCH (m:Memory {id: $id})
        SET m.lastAccessed = $now, m.accessCount = m.accessCount + 1
        """
        self._run_write(update_query, {"id": memory_id, "now": datetime.now().isoformat()})

        query = """
        MATCH (m:Memory {id: $id})
        RETURN m.id AS id, m.content AS content, m.summary AS summary,
               m.created AS created, m.lastAccessed AS lastAccessed,
               m.accessCount AS accessCount, m.confidence AS confidence
        """
        result = self._run_query(query, {"id": memory_id})

        if result and apply_retrieval_effects:
            self._apply_retrieval_effects(memory_id)

        return result[0] if result else None

    def search_memories(self, search_term: str, limit: int = 10) -> List[Dict]:
        """Search memories by content or summary.

        Uses full-text search index (BM25 scoring) when available,
        falls back to CONTAINS scan otherwise.
        """
        if self._fts_available:
            query = """
            CALL QUERY_FTS_INDEX("Memory", "memory_fts", $term)
            WITH node, score
            RETURN node.id AS id, node.content AS content, node.summary AS summary,
                   node.created AS created, node.lastAccessed AS lastAccessed,
                   node.accessCount AS accessCount, node.confidence AS confidence
            ORDER BY score DESC
            LIMIT $limit
            """
            return self._run_query(query, {"term": search_term, "limit": limit})

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

    def get_related_memories(self, memory_id: str, limit: int = 20,
                             respect_permeability: bool = True) -> List[Dict]:
        """Get memories related to a given memory through shared concepts/keywords/topics.

        Finds memories that share at least one concept or keyword with the given memory
        (single-hop traversal through association nodes).
        """
        query = """
        MATCH (m:Memory {id: $id})-[:HAS_CONCEPT]->(c:Concept)<-[:HAS_CONCEPT]-(related:Memory)
        WHERE related.id <> $id
        RETURN DISTINCT related.id AS id, related.content AS content, related.summary AS summary,
               related.created AS created, related.lastAccessed AS lastAccessed,
               related.accessCount AS accessCount, related.confidence AS confidence
        LIMIT $limit
        """
        fetch_limit = limit * 3 if respect_permeability else limit
        results = self._run_query(query, {"id": memory_id, "limit": fetch_limit})

        if len(results) < fetch_limit:
            query2 = """
            MATCH (m:Memory {id: $id})-[:HAS_KEYWORD]->(k:Keyword)<-[:HAS_KEYWORD]-(related:Memory)
            WHERE related.id <> $id
            RETURN DISTINCT related.id AS id, related.content AS content, related.summary AS summary,
                   related.created AS created, related.lastAccessed AS lastAccessed,
                   related.accessCount AS accessCount, related.confidence AS confidence
            LIMIT $remaining
            """
            remaining = fetch_limit - len(results)
            keyword_results = self._run_query(query2, {"id": memory_id, "remaining": remaining})
            seen_ids = {r["id"] for r in results}
            for r in keyword_results:
                if r["id"] not in seen_ids:
                    results.append(r)
                    seen_ids.add(r["id"])

        if respect_permeability:
            results = self._filter_by_permeability(memory_id, results)

        return results[:limit]

    def get_memories_by_concept(self, concept_name: str, limit: int = 20,
                                 apply_retrieval_effects: bool = True) -> List[Dict]:
        """Get all memories associated with a concept."""
        concept_query = """
        MATCH (c:Concept {name: $name})
        RETURN c.id AS id
        """
        concept_result = self._run_query(concept_query, {"name": concept_name})
        concept_id = concept_result[0]["id"] if concept_result else None

        query = """
        MATCH (m:Memory)-[:HAS_CONCEPT]->(c:Concept {name: $name})
        RETURN m.id AS id, m.content AS content, m.summary AS summary,
               m.created AS created, m.lastAccessed AS lastAccessed,
               m.accessCount AS accessCount, m.confidence AS confidence
        ORDER BY m.lastAccessed DESC
        LIMIT $limit
        """
        results = self._run_query(query, {"name": concept_name, "limit": limit})

        if apply_retrieval_effects and concept_id and self.plasticity.retrieval_strengthens:
            for mem in results:
                self._apply_retrieval_effects(mem["id"], via_concept_id=concept_id)

        return results

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
        query1 = """
        MATCH (d1:Decision)-[:LED_TO]->(d2:Decision {id: $id})
        RETURN d1.id AS id, d1.description AS description, d1.rationale AS rationale,
               d1.date AS date, d1.outcome AS outcome, 'predecessor' AS relation
        """
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
            "Contradiction": "MATCH (n:Contradiction) RETURN n.id AS id, n.description AS description, n.status AS status, n.created AS created",
            "Compartment": "MATCH (n:Compartment) RETURN n.id AS id, n.name AS name, n.permeability AS permeability, n.allowExternalConnections AS allowExternalConnections, n.description AS description, n.created AS created"
        }

        for node_type, query in node_queries.items():
            summary[node_type] = self._run_query(query)

        return summary

    def get_node_counts(self) -> Dict[str, int]:
        """Get counts of each node type in a single batched query."""
        node_types = [
            "Memory", "Concept", "Keyword", "Topic", "Entity", "Source",
            "Decision", "Goal", "Question", "Context", "Preference",
            "TemporalMarker", "Contradiction", "Compartment"
        ]
        parts = [
            f"MATCH (n:{nt}) RETURN '{nt}' AS type, count(n) AS cnt"
            for nt in node_types
        ]
        query = " UNION ALL ".join(parts)
        results = self._run_query(query)
        counts = {row["type"]: row["cnt"] for row in results}
        return {nt: counts.get(nt, 0) for nt in node_types}

    def export_directory_markdown(self) -> str:
        """Export the node directory as markdown."""
        summary = self.get_all_nodes_summary()
        # Derive counts from summary data instead of running a separate query
        counts = {k: len(v) for k, v in summary.items()}

        lines = ["# Memory Graph Directory\n"]
        lines.append(f"Last updated: {datetime.now().isoformat()}\n")

        lines.append("## Node Counts\n")
        for node_type, count in sorted(counts.items()):
            lines.append(f"- **{node_type}**: {count}")
        lines.append("")

        for node_type in ["Compartment", "Concept", "Topic", "Keyword", "Entity", "Goal", "Question", "Context", "Preference"]:
            if node_type in summary and summary[node_type]:
                plural = "ies" if node_type.endswith("y") else "s"
                label = node_type[:-1] + plural if node_type.endswith("y") else node_type + "s"
                lines.append(f"\n## {label}\n")
                for item in summary[node_type]:
                    node_id = str(item.get('id', 'N/A'))[:8]
                    if node_type == "Compartment":
                        perm = item.get('permeability', 'open')
                        ext = "yes" if item.get('allowExternalConnections', True) else "no"
                        lines.append(f"- `{node_id}` **{item.get('name', 'N/A')}** ({perm}, ext:{ext})")
                    elif node_type in ("Concept", "Topic"):
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
            "TemporalMarker", "Contradiction", "Compartment"
        ]
        for node_type in node_types:
            self._run_write(f"MATCH (n:{node_type}) DETACH DELETE n")


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
    confidence: float = 1.0,
    compartment_id: str = None  # Optional compartment (None uses active compartment)
) -> str:
    """Quickly store a memory with its associations.

    Wrapped in a transaction so partial failures roll back cleanly.
    """
    memory = Memory(content=content, summary=summary, confidence=confidence)

    client.begin_transaction()
    try:
        memory_id = client.create_memory(memory, compartment_id=compartment_id)

        if concepts:
            for concept_name in concepts:
                concept = Concept(name=concept_name)
                concept_id = client.create_concept(concept)
                client.link_memory_to_concept(memory_id, concept_id)

        if keywords:
            for term in keywords:
                keyword = Keyword(term=term)
                keyword_id = client.create_keyword(keyword)
                client.link_memory_to_keyword(memory_id, keyword_id)

        if topics:
            for i, topic_name in enumerate(topics):
                topic = Topic(name=topic_name)
                topic_id = client.create_topic(topic)
                client.link_memory_to_topic(memory_id, topic_id, primary=(i == 0))

        if entities:
            for name, etype in entities:
                entity = Entity(name=name, type=EntityType(etype))
                entity_id = client.create_entity(entity)
                client.link_memory_to_entity(memory_id, entity_id)

        client.commit()
        return memory_id
    except Exception:
        client.rollback()
        raise
