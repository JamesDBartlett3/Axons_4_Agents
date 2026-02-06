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


class DecayCurve(Enum):
    """Mathematical function for connection decay over time."""
    LINEAR = "linear"           # Constant decay rate
    EXPONENTIAL = "exponential" # Fast initial decay, slowing over time
    LOGARITHMIC = "logarithmic" # Slow initial decay, accelerating over time
    SIGMOID = "sigmoid"         # S-curve: slow start, fast middle, slow end


class StrengtheningCurve(Enum):
    """Mathematical function for connection strengthening."""
    LINEAR = "linear"           # Constant strengthening rate
    DIMINISHING = "diminishing" # Easier to strengthen weak connections
    ACCELERATING = "accelerating" # Easier to strengthen strong connections


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
# PLASTICITY CONFIGURATION
# ============================================================================

@dataclass
class PlasticityConfig:
    """
    Configuration for brain-like plasticity behavior.

    All parameters are tuneable to experiment with different memory dynamics.
    Use PlasticityConfig.default() for sensible defaults, or customize as needed.

    Example:
        config = PlasticityConfig(
            learning_rate=0.15,
            decay_curve=DecayCurve.EXPONENTIAL,
            retrieval_strengthens=True
        )
        client = MemoryGraphClient(plasticity_config=config)
    """

    # === LEARNING RATES ===
    # Global multiplier for all plasticity operations (0.0 = no learning, 1.0 = normal, >1.0 = accelerated)
    learning_rate: float = 1.0

    # === STRENGTHENING PARAMETERS ===
    # Base amount to strengthen connections (before learning_rate multiplier)
    base_strengthening_amount: float = 0.1
    # Maximum connection strength (ceiling)
    max_strength: float = 1.0
    # Minimum connection strength (floor, but still exists)
    min_strength: float = 0.0
    # Curve for strengthening (affects whether weak or strong connections strengthen faster)
    strengthening_curve: StrengtheningCurve = StrengtheningCurve.LINEAR
    # For DIMINISHING curve: how much harder it is to strengthen already-strong connections
    # Higher = more diminishing returns (e.g., 2.0 means half as effective at strength 0.5)
    diminishing_factor: float = 2.0

    # === WEAKENING PARAMETERS ===
    # Base amount to weaken connections (before learning_rate multiplier)
    base_weakening_amount: float = 0.1
    # Whether weakening uses the same curve as strengthening (inverted)
    symmetric_curves: bool = True

    # === HEBBIAN LEARNING ===
    # Amount to strengthen when memories are co-accessed
    hebbian_learning_amount: float = 0.05
    # Whether to create new connections if none exist when co-accessed
    hebbian_creates_connections: bool = True
    # Initial strength for Hebbian-created connections
    hebbian_initial_strength: float = 0.3

    # === DECAY PARAMETERS ===
    # Curve type for time-based decay
    decay_curve: DecayCurve = DecayCurve.EXPONENTIAL
    # Base decay rate per decay cycle
    base_decay_rate: float = 0.05
    # Connections below this threshold decay (those above are stable)
    decay_threshold: float = 0.5
    # Half-life in decay cycles (for exponential decay): cycles until strength halves
    # Set to 0 to disable half-life-based decay
    decay_half_life: int = 10
    # Whether decay affects all connections or only weak ones
    decay_affects_all: bool = False

    # === PRUNING PARAMETERS ===
    # Connections at or below this strength are candidates for pruning
    pruning_threshold: float = 0.01
    # Whether to auto-prune during decay operations
    auto_prune: bool = True
    # Grace period: minimum age (in access cycles) before a connection can be pruned
    pruning_grace_period: int = 0

    # === RETRIEVAL-INDUCED MODIFICATION ===
    # Whether querying/accessing memories affects connections (like human recall)
    retrieval_strengthens: bool = True
    # Amount to strengthen accessed connections
    retrieval_strengthening_amount: float = 0.02
    # Whether retrieval weakens competing (non-accessed but related) memories
    retrieval_weakens_competitors: bool = False
    # Amount to weaken competing memories
    competitor_weakening_amount: float = 0.01
    # Hops away to consider as "competitors"
    competitor_hops: int = 1

    # === CONCEPT RELEVANCE ===
    # Base amount to adjust concept relevance
    concept_relevance_adjustment: float = 0.1
    # Whether accessing a memory via concept search boosts that concept's relevance
    access_boosts_concept_relevance: bool = True

    # === GOAL/QUESTION SUPPORT ===
    # Amount to strengthen memory-goal connections when goal is progressed
    goal_progress_strengthening: float = 0.1
    # Amount to strengthen memory-question connections when question is answered
    question_answer_strengthening: float = 0.15

    # === TIME-BASED PARAMETERS ===
    # Whether to use real wall-clock time for decay (vs access-count based)
    use_real_time_decay: bool = False
    # If using real time, decay rate per hour
    hourly_decay_rate: float = 0.001

    # === CONNECTION TYPE WEIGHTS ===
    # Multipliers for different relationship types (allows tuning per-type)
    relationship_weights: Dict[str, float] = field(default_factory=lambda: {
        "RELATES_TO": 1.0,
        "HAS_CONCEPT": 1.0,
        "HAS_KEYWORD": 1.0,
        "BELONGS_TO": 1.0,
        "MENTIONS": 1.0,
        "SUPPORTS": 1.0,
        "PARTIALLY_ANSWERS": 1.0,
    })

    @classmethod
    def default(cls) -> "PlasticityConfig":
        """Return default configuration with balanced settings."""
        return cls()

    @classmethod
    def aggressive_learning(cls) -> "PlasticityConfig":
        """Configuration for fast learning with quick adaptation."""
        return cls(
            learning_rate=1.5,
            base_strengthening_amount=0.15,
            hebbian_learning_amount=0.1,
            retrieval_strengthens=True,
            retrieval_strengthening_amount=0.05,
            decay_threshold=0.3,
        )

    @classmethod
    def conservative_learning(cls) -> "PlasticityConfig":
        """Configuration for slow, stable learning."""
        return cls(
            learning_rate=0.5,
            base_strengthening_amount=0.05,
            hebbian_learning_amount=0.02,
            retrieval_strengthens=True,
            retrieval_strengthening_amount=0.01,
            decay_threshold=0.7,
            pruning_threshold=0.005,
        )

    @classmethod
    def no_plasticity(cls) -> "PlasticityConfig":
        """Configuration that disables all automatic plasticity (manual only)."""
        return cls(
            learning_rate=0.0,
            retrieval_strengthens=False,
            retrieval_weakens_competitors=False,
            access_boosts_concept_relevance=False,
            auto_prune=False,
        )

    @classmethod
    def high_decay(cls) -> "PlasticityConfig":
        """Configuration with aggressive forgetting (for memory pressure scenarios)."""
        return cls(
            base_decay_rate=0.1,
            decay_threshold=0.7,
            decay_affects_all=True,
            pruning_threshold=0.05,
            decay_half_life=5,
        )

    def effective_strengthening(self, base_amount: float = None, current_strength: float = 0.0) -> float:
        """Calculate effective strengthening amount based on config and current strength."""
        amount = base_amount if base_amount is not None else self.base_strengthening_amount
        amount *= self.learning_rate

        # Apply curve
        if self.strengthening_curve == StrengtheningCurve.DIMINISHING:
            # Harder to strengthen already-strong connections
            # At strength 0, full effect. At strength 1, minimal effect.
            factor = 1.0 - (current_strength ** (1.0 / self.diminishing_factor))
            amount *= max(0.1, factor)  # Never reduce below 10%
        elif self.strengthening_curve == StrengtheningCurve.ACCELERATING:
            # Easier to strengthen already-strong connections
            factor = 0.5 + (current_strength * 0.5)
            amount *= factor

        return amount

    def effective_weakening(self, base_amount: float = None, current_strength: float = 1.0) -> float:
        """Calculate effective weakening amount based on config and current strength."""
        amount = base_amount if base_amount is not None else self.base_weakening_amount
        amount *= self.learning_rate

        if self.symmetric_curves:
            # Inverse of strengthening curve
            if self.strengthening_curve == StrengtheningCurve.DIMINISHING:
                # Harder to weaken already-weak connections
                factor = current_strength ** (1.0 / self.diminishing_factor)
                amount *= max(0.1, factor)
            elif self.strengthening_curve == StrengtheningCurve.ACCELERATING:
                # Easier to weaken already-weak connections
                factor = 1.0 - (current_strength * 0.5)
                amount *= factor

        return amount

    def effective_decay(self, current_strength: float, cycles_since_access: int = 1) -> float:
        """Calculate decay amount based on curve and time since last access."""
        if current_strength > self.decay_threshold and not self.decay_affects_all:
            return 0.0

        base = self.base_decay_rate * self.learning_rate

        if self.decay_curve == DecayCurve.LINEAR:
            return base * cycles_since_access
        elif self.decay_curve == DecayCurve.EXPONENTIAL:
            if self.decay_half_life > 0:
                # Exponential decay based on half-life
                return current_strength * (1 - (0.5 ** (cycles_since_access / self.decay_half_life)))
            else:
                return base * (1.5 ** cycles_since_access - 1)
        elif self.decay_curve == DecayCurve.LOGARITHMIC:
            import math
            return base * math.log1p(cycles_since_access)
        elif self.decay_curve == DecayCurve.SIGMOID:
            import math
            # S-curve centered around half the decay threshold
            midpoint = self.decay_threshold / 2
            steepness = 5.0
            sigmoid = 1 / (1 + math.exp(-steepness * (cycles_since_access - midpoint)))
            return base * sigmoid * 2

        return base

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for serialization."""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Enum):
                result[key] = value.value
            elif isinstance(value, dict):
                result[key] = value.copy()
            else:
                result[key] = value
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlasticityConfig":
        """Create config from dictionary."""
        # Convert enum strings back to enums
        if "decay_curve" in data and isinstance(data["decay_curve"], str):
            data["decay_curve"] = DecayCurve(data["decay_curve"])
        if "strengthening_curve" in data and isinstance(data["strengthening_curve"], str):
            data["strengthening_curve"] = StrengtheningCurve(data["strengthening_curve"])
        return cls(**data)


# ============================================================================
# MEMORY GRAPH CLIENT
# ============================================================================

class MemoryGraphClient:
    """Client for interacting with the KùzuDB memory database."""

    def __init__(self, db_path: str = None, plasticity_config: PlasticityConfig = None):
        """
        Initialize connection to KùzuDB.

        Args:
            db_path: Path to the database directory. If None, uses default location
                     in user's home directory (~/.axons_memory_db)
            plasticity_config: Configuration for brain-like plasticity behavior.
                              If None, uses PlasticityConfig.default()
        """
        if db_path is None:
            db_path = os.path.join(Path.home(), ".axons_memory_db")

        self.db_path = db_path
        self.db = kuzu.Database(db_path)
        self.conn = kuzu.Connection(self.db)
        self._schema_initialized = False
        self.plasticity = plasticity_config or PlasticityConfig.default()
        self._access_cycle = 0  # Track access cycles for decay calculations

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
            # Memory-to-memory with synaptic-like strength
            "CREATE REL TABLE IF NOT EXISTS RELATES_TO (FROM Memory TO Memory, strength DOUBLE, relType STRING)",
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
        """Link a memory to a concept with relevance weight (0-1).

        Higher relevance = stronger association (like synaptic strength).
        """
        query = """
        MATCH (m:Memory), (c:Concept)
        WHERE m.id = $memory_id AND c.id = $concept_id
        CREATE (m)-[:HAS_CONCEPT {relevance: $relevance}]->(c)
        """
        self._run_write(query, {"memory_id": memory_id, "concept_id": concept_id, "relevance": relevance})

    def link_memory_to_keyword(self, memory_id: str, keyword_id: str):
        """Link a memory to a keyword."""
        query = """
        MATCH (m:Memory), (k:Keyword)
        WHERE m.id = $memory_id AND k.id = $keyword_id
        CREATE (m)-[:HAS_KEYWORD]->(k)
        """
        self._run_write(query, {"memory_id": memory_id, "keyword_id": keyword_id})

    def link_memory_to_topic(self, memory_id: str, topic_id: str, primary: bool = False):
        """Link a memory to a topic, optionally marking it as the primary topic."""
        query = """
        MATCH (m:Memory), (t:Topic)
        WHERE m.id = $memory_id AND t.id = $topic_id
        CREATE (m)-[:BELONGS_TO {isPrimary: $is_primary}]->(t)
        """
        self._run_write(query, {"memory_id": memory_id, "topic_id": topic_id, "is_primary": primary})

    def link_memory_to_entity(self, memory_id: str, entity_id: str, role: str = ""):
        """Link a memory to an entity with an optional role description."""
        query = """
        MATCH (m:Memory), (e:Entity)
        WHERE m.id = $memory_id AND e.id = $entity_id
        CREATE (m)-[:MENTIONS {role: $role}]->(e)
        """
        self._run_write(query, {"memory_id": memory_id, "entity_id": entity_id, "role": role})

    def link_memory_to_source(self, memory_id: str, source_id: str, excerpt: str = ""):
        """Link a memory to its source with an optional excerpt."""
        query = """
        MATCH (m:Memory), (s:Source)
        WHERE m.id = $memory_id AND s.id = $source_id
        CREATE (m)-[:FROM_SOURCE {excerpt: $excerpt}]->(s)
        """
        self._run_write(query, {"memory_id": memory_id, "source_id": source_id, "excerpt": excerpt})

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
        """Link a memory that partially answers a question.

        Completeness (0-1) indicates how much the memory answers the question.
        """
        query = """
        MATCH (m:Memory), (q:Question)
        WHERE m.id = $memory_id AND q.id = $question_id
        CREATE (m)-[:PARTIALLY_ANSWERS {completeness: $completeness}]->(q)
        """
        self._run_write(query, {"memory_id": memory_id, "question_id": question_id, "completeness": completeness})

    def link_memory_to_goal(self, memory_id: str, goal_id: str, strength: float = 0.5):
        """Link a memory that supports a goal.

        Strength (0-1) indicates how strongly the memory supports the goal.
        """
        query = """
        MATCH (m:Memory), (g:Goal)
        WHERE m.id = $memory_id AND g.id = $goal_id
        CREATE (m)-[:SUPPORTS {strength: $strength}]->(g)
        """
        self._run_write(query, {"memory_id": memory_id, "goal_id": goal_id, "strength": strength})

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
        """Link two related memories with a synaptic-like strength.

        Strength (0-1) represents the connection weight - can be increased
        when memories are accessed together (Hebbian learning) or decreased
        over time (decay).
        """
        query = """
        MATCH (m1:Memory), (m2:Memory)
        WHERE m1.id = $id1 AND m2.id = $id2
        CREATE (m1)-[:RELATES_TO {strength: $strength, relType: $relType}]->(m2)
        """
        self._run_write(query, {"id1": memory_id_1, "id2": memory_id_2, "strength": strength, "relType": rel_type})

    def link_concepts(self, concept_id_1: str, concept_id_2: str, rel_type: str = ""):
        """Link two related concepts."""
        query = """
        MATCH (c1:Concept), (c2:Concept)
        WHERE c1.id = $id1 AND c2.id = $id2
        CREATE (c1)-[:CONCEPT_RELATED_TO {relType: $relType}]->(c2)
        """
        self._run_write(query, {"id1": concept_id_1, "id2": concept_id_2, "relType": rel_type})

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
    # PLASTICITY OPERATIONS (Brain-like learning)
    # All operations respect self.plasticity configuration
    # ========================================================================

    def strengthen_memory_link(self, memory_id_1: str, memory_id_2: str, amount: float = None):
        """Strengthen the connection between two memories (Hebbian learning).

        This emulates synaptic potentiation - "neurons that fire together wire together".
        Call this when two memories are accessed/recalled together.

        Args:
            memory_id_1: First memory ID
            memory_id_2: Second memory ID
            amount: Override for strengthening amount. If None, uses config.
        """
        # Get current strength to apply curve
        current = self.get_memory_link_strength(memory_id_1, memory_id_2) or 0.0
        effective_amount = self.plasticity.effective_strengthening(amount, current)

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
        """Weaken the connection between two memories.

        This emulates synaptic depression - connections weaken when not reinforced.

        Args:
            memory_id_1: First memory ID
            memory_id_2: Second memory ID
            amount: Override for weakening amount. If None, uses config.
        """
        # Get current strength to apply curve
        current = self.get_memory_link_strength(memory_id_1, memory_id_2) or 1.0
        effective_amount = self.plasticity.effective_weakening(amount, current)

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
        """Increase the relevance of a concept to a memory.

        Use when a concept proves particularly useful for retrieving this memory.
        """
        if amount is None:
            amount = self.plasticity.concept_relevance_adjustment * self.plasticity.learning_rate

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
            amount = self.plasticity.concept_relevance_adjustment * self.plasticity.learning_rate

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

    def apply_hebbian_learning(self, memory_ids: List[str], amount: float = None):
        """Strengthen connections between all memories accessed together.

        When multiple memories are retrieved in the same context, strengthen
        all pairwise connections. This implements "neurons that fire together
        wire together".

        If plasticity.hebbian_creates_connections is True, creates new connections
        between memories that aren't already linked.

        Args:
            memory_ids: List of memory IDs that were accessed together
            amount: Override for strengthening amount. If None, uses config.
        """
        if amount is None:
            amount = self.plasticity.hebbian_learning_amount

        # Strengthen all pairwise connections
        for i, id1 in enumerate(memory_ids):
            for id2 in memory_ids[i+1:]:
                # Check if connection exists
                strength = self.get_memory_link_strength(id1, id2)
                if strength is None and self.plasticity.hebbian_creates_connections:
                    # Create new connection with initial strength
                    self.link_memories(id1, id2, self.plasticity.hebbian_initial_strength, "hebbian")
                    self.link_memories(id2, id1, self.plasticity.hebbian_initial_strength, "hebbian")
                else:
                    self.strengthen_memory_link(id1, id2, amount)
                    self.strengthen_memory_link(id2, id1, amount)

    def decay_weak_connections(self, threshold: float = None, decay_amount: float = None):
        """Weaken connections that are below threshold.

        This emulates synaptic decay - connections that aren't reinforced
        eventually weaken. Controlled by decay_curve in config.

        Args:
            threshold: Override for decay threshold. If None, uses config.
            decay_amount: Override for decay amount. If None, uses config.
        """
        if threshold is None:
            threshold = self.plasticity.decay_threshold
        if decay_amount is None:
            decay_amount = self.plasticity.base_decay_rate * self.plasticity.learning_rate

        if decay_amount <= 0:
            return

        min_strength = self.plasticity.min_strength

        if self.plasticity.decay_affects_all:
            # Decay all connections
            query = """
            MATCH (m1:Memory)-[r:RELATES_TO]->(m2:Memory)
            SET r.strength = CASE
                WHEN r.strength - $decay_amount < $min THEN $min
                ELSE r.strength - $decay_amount
            END
            """
            self._run_write(query, {"decay_amount": decay_amount, "min": min_strength})
        else:
            # Only decay connections below threshold
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

        # Auto-prune if enabled
        if self.plasticity.auto_prune:
            self.prune_dead_connections()

    def prune_dead_connections(self, min_strength: float = None):
        """Remove connections that have decayed to near-zero.

        Args:
            min_strength: Override for pruning threshold. If None, uses config.
        """
        if min_strength is None:
            min_strength = self.plasticity.pruning_threshold

        query = """
        MATCH (m1:Memory)-[r:RELATES_TO]->(m2:Memory)
        WHERE r.strength <= $min_strength
        DELETE r
        """
        self._run_write(query, {"min_strength": min_strength})

    def get_strongest_connections(self, memory_id: str, limit: int = 10) -> List[Dict]:
        """Get the strongest connections from a memory (most relevant associations).

        Returns memories sorted by connection strength, highest first.
        """
        query = """
        MATCH (m:Memory)-[r:RELATES_TO]->(related:Memory)
        WHERE m.id = $memory_id
        RETURN related.id AS id, related.summary AS summary, r.strength AS strength
        ORDER BY r.strength DESC
        LIMIT $limit
        """
        return self._run_query(query, {"memory_id": memory_id, "limit": limit})

    def get_weakest_connections(self, memory_id: str, limit: int = 10) -> List[Dict]:
        """Get the weakest connections from a memory (candidates for pruning).

        Returns memories sorted by connection strength, lowest first.
        """
        query = """
        MATCH (m:Memory)-[r:RELATES_TO]->(related:Memory)
        WHERE m.id = $memory_id
        RETURN related.id AS id, related.summary AS summary, r.strength AS strength
        ORDER BY r.strength ASC
        LIMIT $limit
        """
        return self._run_query(query, {"memory_id": memory_id, "limit": limit})

    def get_all_connection_strengths(self) -> List[Dict]:
        """Get all memory-to-memory connections with their strengths.

        Useful for analyzing the overall connection distribution.
        """
        query = """
        MATCH (m1:Memory)-[r:RELATES_TO]->(m2:Memory)
        RETURN m1.id AS from_id, m2.id AS to_id, r.strength AS strength
        ORDER BY r.strength DESC
        """
        return self._run_query(query, {})

    def get_connection_statistics(self) -> Dict[str, Any]:
        """Get statistics about all connections in the graph.

        Returns dict with count, min, max, avg, and distribution buckets.
        """
        connections = self.get_all_connection_strengths()
        if not connections:
            return {
                "count": 0, "min": None, "max": None, "avg": None,
                "buckets": {}, "below_threshold": 0
            }

        strengths = [c["strength"] for c in connections]
        threshold = self.plasticity.decay_threshold

        # Create distribution buckets (0-0.1, 0.1-0.2, etc.)
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
            "pruning_candidates": sum(1 for s in strengths if s <= self.plasticity.pruning_threshold),
        }

    # === RETRIEVAL-INDUCED MODIFICATION ===

    def _apply_retrieval_effects(self, memory_id: str, via_concept_id: str = None):
        """Apply retrieval-induced modifications when a memory is accessed.

        This emulates how human memory recall actually modifies the memory:
        - Strengthens the accessed memory's connections
        - Optionally weakens competing (related but not accessed) memories
        - Boosts concept relevance if accessed via concept search

        Called automatically by get_memory() if retrieval_strengthens is enabled.
        """
        if not self.plasticity.retrieval_strengthens:
            return

        # Strengthen connections TO this memory (it was useful enough to retrieve)
        amount = self.plasticity.retrieval_strengthening_amount * self.plasticity.learning_rate
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

        # Boost concept relevance if accessed via concept
        if via_concept_id and self.plasticity.access_boosts_concept_relevance:
            self.strengthen_concept_relevance(memory_id, via_concept_id)

        # Weaken competitors if enabled
        if self.plasticity.retrieval_weakens_competitors:
            self._weaken_competitors(memory_id)

    def _weaken_competitors(self, accessed_memory_id: str):
        """Weaken memories that are related to but weren't accessed.

        This implements retrieval-induced forgetting - accessing one memory
        can make related memories harder to recall.
        """
        amount = self.plasticity.competitor_weakening_amount * self.plasticity.learning_rate
        if amount <= 0:
            return

        # Find memories connected to the accessed memory (competitors)
        # and weaken their OTHER connections (not the one to accessed memory)
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
        """Run a full maintenance cycle: decay, prune, update statistics.

        Call this periodically (e.g., at session end) to simulate time passing.
        Increments the internal access cycle counter.
        """
        self._access_cycle += 1
        self.decay_weak_connections()
        # Auto-prune is handled by decay_weak_connections if enabled

    def run_aggressive_maintenance(self, cycles: int = 5):
        """Run multiple maintenance cycles to aggressively prune weak connections.

        Useful for memory pressure situations or cleanup.

        Args:
            cycles: Number of decay cycles to run
        """
        for _ in range(cycles):
            self.run_maintenance_cycle()

    def strengthen_goal_connections(self, goal_id: str, amount: float = None):
        """Strengthen all memory connections to a goal (goal progress).

        Call when a goal is progressed or achieved.
        """
        if amount is None:
            amount = self.plasticity.goal_progress_strengthening * self.plasticity.learning_rate

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
        """Strengthen all memory connections to a question.

        Call when a question is answered or progressed.
        """
        if amount is None:
            amount = self.plasticity.question_answer_strengthening * self.plasticity.learning_rate

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
        import json
        with open(filepath, 'w') as f:
            json.dump(self.plasticity.to_dict(), f, indent=2)

    def load_plasticity_config(self, filepath: str):
        """Load plasticity config from a JSON file."""
        import json
        with open(filepath, 'r') as f:
            data = json.load(f)
        self.plasticity = PlasticityConfig.from_dict(data)

    # ========================================================================
    # QUERY OPERATIONS
    # ========================================================================

    def get_memory(self, memory_id: str, apply_retrieval_effects: bool = True) -> Optional[Dict]:
        """Get a memory by ID and update access tracking.

        Args:
            memory_id: The memory's unique identifier
            apply_retrieval_effects: If True (default), applies retrieval-induced
                                    modifications based on plasticity config.
                                    Set to False for read-only access.
        """
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

        if result and apply_retrieval_effects:
            # Apply retrieval-induced modifications (like human recall changing memory)
            self._apply_retrieval_effects(memory_id)

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

    def get_memories_by_concept(self, concept_name: str, limit: int = 20,
                                 apply_retrieval_effects: bool = True) -> List[Dict]:
        """Get all memories associated with a concept.

        Args:
            concept_name: Name of the concept to search for
            limit: Maximum number of results
            apply_retrieval_effects: If True, boosts concept relevance for returned memories
        """
        # First get the concept ID for retrieval effects
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

        # Apply retrieval effects - accessing via concept boosts that concept's relevance
        if apply_retrieval_effects and concept_id and self.plasticity.access_boosts_concept_relevance:
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
