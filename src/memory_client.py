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


class Curve(Enum):
    """
    Mathematical curve for plasticity operations.

    Used for both:
    - Plasticity curve: how current strength affects rate of change
    - Decay curve: how time affects decay rate

    Options:
    - LINEAR: Constant rate, no modification based on input
    - EXPONENTIAL: Starts fast, slows down (or half-life based for decay)
    - LOGARITHMIC: Starts slow, speeds up
    """
    LINEAR = "linear"           # Constant rate
    EXPONENTIAL = "exponential" # Fast start, slowing (half-life for decay)
    LOGARITHMIC = "logarithmic" # Slow start, accelerating


class Permeability(Enum):
    """
    Controls data flow direction through compartment boundaries.

    Used for both compartments (default policy) and individual connections (override).
    Data flow direction is from the perspective of the compartment/connection owner.

    Options:
    - OPEN: Bidirectional data flow (no restrictions)
    - CLOSED: No data flow in either direction (complete isolation)
    - OSMOTIC_INWARD: Data can flow IN (can retrieve external data, but external
                      queries cannot retrieve data from inside)
    - OSMOTIC_OUTWARD: Data can flow OUT (external queries can retrieve data,
                       but cannot retrieve external data from inside)
    """
    OPEN = "open"                     # Bidirectional (default)
    CLOSED = "closed"                 # No data flow
    OSMOTIC_INWARD = "osmotic_inward"   # Can pull data in, cannot leak out
    OSMOTIC_OUTWARD = "osmotic_outward" # Can share out, cannot pull in

    def allows_inward(self) -> bool:
        """Check if this permeability allows inward data flow."""
        return self in (Permeability.OPEN, Permeability.OSMOTIC_INWARD)

    def allows_outward(self) -> bool:
        """Check if this permeability allows outward data flow."""
        return self in (Permeability.OPEN, Permeability.OSMOTIC_OUTWARD)


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
    permeability: Permeability = Permeability.OPEN


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


@dataclass
class Compartment:
    """
    A compartment for isolating memories and controlling data flow.

    Compartmentalization allows:
    1. Preventing organic connections from forming across boundaries
    2. Controlling query traversal direction (osmotic data flow)

    Example:
        # Create a secure project compartment
        compartment = Compartment(
            name="Project Q",
            permeability=Permeability.OSMOTIC_INWARD,  # Can read external, but doesn't leak
            allow_external_connections=False  # No organic links to outside
        )
    """
    name: str
    permeability: Permeability = Permeability.OPEN
    allow_external_connections: bool = True  # Whether organic connections can form externally
    description: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created: datetime = field(default_factory=datetime.now)


# ============================================================================
# PLASTICITY CONFIGURATION
# ============================================================================

@dataclass
class PlasticityConfig:
    """
    Configuration for brain-like plasticity behavior.

    Design principles:
    - Independent context-specific amounts for each operation type
    - Symmetrical curves for strengthening and weakening
    - Clear separation: decay (time-based) vs weaken (explicit action)
    - Semantic similarity can only boost initial strength, never weaken

    Example:
        config = PlasticityConfig(
            learning_rate=1.0,
            curve=Curve.EXPONENTIAL,
            retrieval_strengthens=True
        )
        client = MemoryGraphClient(plasticity_config=config)
    """

    # === MASTER CONTROL ===
    # Global multiplier for all plasticity operations (0=disabled, 1=normal)
    learning_rate: float = 1.0

    # === CONTEXT-SPECIFIC AMOUNTS ===
    # Each context has its own independent base amount (0-1 scale)
    # Effective amount = context_amount * learning_rate * curve_adjustment
    strengthen_amount: float = 0.1    # For explicit strengthen operations
    weaken_amount: float = 0.1        # For explicit weaken operations
    hebbian_amount: float = 0.05      # For co-access strengthening
    retrieval_amount: float = 0.02    # For retrieval-induced changes
    decay_amount: float = 0.05        # For time-based decay

    # === INITIAL CONNECTION STRENGTH ===
    # Starting strength when new connections are created
    initial_strength_explicit: float = 0.5   # User-created/explicit connections
    initial_strength_implicit: float = 0.3   # Hebbian/emergent connections
    # Optional: augment initial strength with semantic similarity (0-1 multiplier)
    use_semantic_similarity: bool = False
    # Callback for semantic similarity (set at runtime if use_semantic_similarity=True)
    # Should be a function(content1: str, content2: str) -> float (0-1)
    # Not serialized - must be set programmatically
    _semantic_similarity_fn: Optional[Any] = field(default=None, repr=False)

    # === STRENGTH BOUNDS ===
    max_strength: float = 1.0         # Connection strength ceiling
    min_strength: float = 0.0         # Connection strength floor

    # === PLASTICITY CURVE ===
    # How current strength affects rate of change
    # Applies symmetrically: strengthening uses curve directly, weakening uses inverse
    curve: Curve = Curve.LINEAR
    curve_steepness: float = 0.5      # Controls curve intensity (0.1=steep, 0.9=gentle)

    # === TIME-BASED DECAY ===
    # Decay is separate from weakening - it's automatic/time-based
    decay_curve: Curve = Curve.EXPONENTIAL
    decay_half_life: float = 0.1      # Fraction of 100 cycles for half-life (0.1=10 cycles)
    decay_threshold: float = 0.5      # Only connections below this decay (unless decay_all=True)
    decay_all: bool = False           # If True, all connections decay regardless of strength

    # === PRUNING ===
    prune_threshold: float = 0.01     # Remove connections at or below this strength
    auto_prune: bool = True           # Automatically prune during decay operations

    # === RETRIEVAL EFFECTS ===
    retrieval_strengthens: bool = True           # Strengthen connections to accessed memories
    retrieval_weakens_competitors: bool = False  # Weaken related but not-accessed memories
    competitor_distance: float = 0.1             # How much to scale competitor weakening

    # === HEBBIAN LEARNING ===
    hebbian_creates_connections: bool = True     # Create new links between co-accessed memories

    def get_initial_strength(self, explicit: bool, content1: str = None, content2: str = None) -> float:
        """Calculate initial strength for a new connection.

        Args:
            explicit: True for user-created connections, False for implicit/Hebbian
            content1: Optional content of first memory (for semantic similarity)
            content2: Optional content of second memory (for semantic similarity)

        Returns:
            Initial strength value (0-1)
        """
        base = self.initial_strength_explicit if explicit else self.initial_strength_implicit

        # Optionally boost with semantic similarity (can only increase, never decrease)
        if self.use_semantic_similarity and self._semantic_similarity_fn and content1 and content2:
            try:
                similarity = self._semantic_similarity_fn(content1, content2)
                # Use similarity to scale the headroom between base and max
                # e.g., base=0.5, max=1.0, similarity=0.8 -> 0.5 + (0.5 * 0.8) = 0.9
                headroom = self.max_strength - base
                base = base + (headroom * similarity)
            except Exception:
                pass  # Fall back to base strength if similarity fails

        return min(self.max_strength, max(self.min_strength, base))

    def set_semantic_similarity_fn(self, fn):
        """Set the semantic similarity function.

        Args:
            fn: A callable(content1: str, content2: str) -> float (0-1)
        """
        self._semantic_similarity_fn = fn

    @classmethod
    def default(cls) -> "PlasticityConfig":
        """Return default configuration with balanced settings."""
        return cls()

    @classmethod
    def aggressive_learning(cls) -> "PlasticityConfig":
        """Fast learning with quick adaptation."""
        return cls(
            learning_rate=1.0,
            strengthen_amount=0.15,
            hebbian_amount=0.1,
            retrieval_amount=0.05,
            decay_threshold=0.3,
        )

    @classmethod
    def conservative_learning(cls) -> "PlasticityConfig":
        """Slow, stable learning with gradual changes."""
        return cls(
            learning_rate=0.5,
            curve=Curve.EXPONENTIAL,
            decay_threshold=0.7,
            prune_threshold=0.005,
        )

    @classmethod
    def no_plasticity(cls) -> "PlasticityConfig":
        """Disable all automatic plasticity (manual operations only)."""
        return cls(
            learning_rate=0.0,
            retrieval_strengthens=False,
            retrieval_weakens_competitors=False,
            auto_prune=False,
        )

    @classmethod
    def high_decay(cls) -> "PlasticityConfig":
        """Aggressive forgetting for memory pressure scenarios."""
        return cls(
            decay_amount=0.1,
            decay_threshold=0.7,
            decay_all=True,
            prune_threshold=0.05,
            decay_half_life=0.05,
        )

    def _apply_curve(self, amount: float, current_strength: float, for_increase: bool) -> float:
        """Apply the plasticity curve to an amount.

        Args:
            amount: Base amount before curve adjustment
            current_strength: Current connection strength (0-1)
            for_increase: True if strengthening, False if weakening

        Returns:
            Adjusted amount based on curve
        """
        if self.curve == Curve.LINEAR:
            return amount

        # Convert 0-1 steepness to effective exponent (0.1 -> 10, 0.5 -> 2, 0.9 -> 1.1)
        steepness = max(0.1, min(0.9, self.curve_steepness))
        exponent = 1.0 / steepness

        if self.curve == Curve.EXPONENTIAL:
            # Exponential: faster changes near the starting point
            if for_increase:
                # Harder to strengthen already-strong connections
                factor = 1.0 - (current_strength ** exponent)
            else:
                # Harder to weaken already-weak connections (symmetrical)
                factor = current_strength ** exponent
            return amount * max(0.1, factor)

        if self.curve == Curve.LOGARITHMIC:
            # Logarithmic: slower changes near the starting point, faster near limits
            if for_increase:
                # Easier to strengthen already-strong connections
                factor = (1.0 - steepness) + (current_strength * steepness)
            else:
                # Easier to weaken already-weak connections (symmetrical)
                factor = steepness + ((1.0 - current_strength) * (1.0 - steepness))
            return amount * factor

        return amount

    def effective_amount(self, context: str, current_strength: float = 0.5) -> float:
        """Calculate effective plasticity amount for a given context.

        Args:
            context: One of 'strengthen', 'weaken', 'hebbian', 'retrieval', 'decay'
            current_strength: Current connection strength (for curve calculation)

        Returns:
            Effective amount to apply (0-1 scale)
        """
        amounts = {
            'strengthen': self.strengthen_amount,
            'weaken': self.weaken_amount,
            'hebbian': self.hebbian_amount,
            'retrieval': self.retrieval_amount,
            'decay': self.decay_amount,
        }
        base = amounts.get(context, 0.1) * self.learning_rate

        # Apply curve (for_increase=True for strengthen/hebbian/retrieval, False for weaken/decay)
        for_increase = context in ('strengthen', 'hebbian', 'retrieval')
        return self._apply_curve(base, current_strength, for_increase)

    def effective_decay(self, current_strength: float, cycles: int = 1) -> float:
        """Calculate decay amount based on curve and cycles since access.

        Args:
            current_strength: Current connection strength
            cycles: Number of decay cycles elapsed

        Returns:
            Amount to decay (subtract from strength), 0-1 scale
        """
        if current_strength > self.decay_threshold and not self.decay_all:
            return 0.0

        base = self.decay_amount * self.learning_rate

        if self.decay_curve == Curve.LINEAR:
            return min(1.0, base * cycles)
        elif self.decay_curve == Curve.EXPONENTIAL:
            # Convert 0-1 half_life to effective cycles (0.1 = 10 cycles, 0.5 = 50 cycles)
            effective_half_life = max(1, int(self.decay_half_life * 100))
            return current_strength * (1.0 - (0.5 ** (cycles / effective_half_life)))
        elif self.decay_curve == Curve.LOGARITHMIC:
            import math
            return min(1.0, base * math.log1p(cycles))

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
            data["decay_curve"] = Curve(data["decay_curve"])
        if "curve" in data and isinstance(data["curve"], str):
            data["curve"] = Curve(data["curve"])

        # Remove internal fields that shouldn't be in serialized data
        data.pop('_semantic_similarity_fn', None)

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
        self._active_compartment_id: Optional[str] = None  # Active compartment for new memories

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
    # COMPARTMENT OPERATIONS
    # ========================================================================

    def create_compartment(self, compartment: Compartment) -> str:
        """Create a new compartment for memory isolation."""
        # Check if compartment with same name exists
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
            # Check if compartment has memories
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
        Adding to a compartment the memory is already in is a no-op.

        Args:
            memory_ids: Single memory ID (str) or list of memory IDs
            compartment_id: The compartment to add to
        """
        # Normalize to list
        if isinstance(memory_ids, str):
            memory_ids = [memory_ids]

        for memory_id in memory_ids:
            # Check if already in this compartment
            check_query = """
            MATCH (m:Memory {id: $mid})-[:IN_COMPARTMENT]->(c:Compartment {id: $cid})
            RETURN count(*) AS cnt
            """
            result = self._run_query(check_query, {"mid": memory_id, "cid": compartment_id})
            if result and result[0]["cnt"] > 0:
                continue  # Already in this compartment

            # Add to compartment
            query = """
            MATCH (m:Memory {id: $mid}), (c:Compartment {id: $cid})
            CREATE (m)-[:IN_COMPARTMENT]->(c)
            """
            self._run_write(query, {"mid": memory_id, "cid": compartment_id})

    def remove_memory_from_compartment(self, memory_ids, compartment_id: str = None):
        """Remove one or more memories from compartment(s).

        Args:
            memory_ids: Single memory ID (str) or list of memory IDs
            compartment_id: Specific compartment to remove from. If None, removes from ALL compartments.
        """
        # Normalize to list
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

    def can_form_connection(self, memory_id_1: str, memory_id_2: str) -> bool:
        """Check if an organic connection can form between two memories.

        This checks compartment boundaries using strict fail-safe logic:
        - ALL compartments of BOTH memories must allow external connections
        - Exception: memories in the SAME single compartment (both only in that one)

        Fail-safe: Any single compartment that disallows external connections will block,
        even if the memories share another compartment.
        """
        comps1 = self.get_memory_compartments(memory_id_1)
        comps2 = self.get_memory_compartments(memory_id_2)

        # Both without compartment - allowed
        if not comps1 and not comps2:
            return True

        # Special case: both memories are in exactly the same set of compartments
        # (i.e., they're fully co-located, not just sharing one)
        ids1 = {c["id"] for c in comps1}
        ids2 = {c["id"] for c in comps2}
        if ids1 == ids2 and ids1:  # Same non-empty set of compartments
            return True

        # Fail-safe: ANY compartment that blocks external connections will block
        for comp in comps1:
            if not comp.get("allowExternalConnections", True):
                return False
        for comp in comps2:
            if not comp.get("allowExternalConnections", True):
                return False

        return True

    def can_data_flow(self, from_memory_id: str, to_memory_id: str,
                      connection_permeability: str = None) -> bool:
        """Check if data can flow from one memory to another.

        This implements multi-layer permeability checking with fail-safe logic:
        1. Source memory must allow OUTWARD flow
        2. ALL source compartments must allow OUTWARD flow
        3. ALL destination compartments must allow INWARD flow
        4. Destination memory must allow INWARD flow
        5. Connection must allow this direction (if provided)

        Fail-safe: ANY layer that blocks will block the entire data flow.
        This means if a memory is in multiple compartments, ALL of them must
        allow the flow direction.

        Args:
            from_memory_id: Memory where data originates
            to_memory_id: Memory requesting the data (query origin)
            connection_permeability: Permeability of the connection (if known)

        Returns:
            True if data can flow from source to destination
        """
        # Check source memory allows outward flow
        from_mem_perm = self.get_memory_permeability(from_memory_id)
        if from_mem_perm and not Permeability(from_mem_perm).allows_outward():
            return False

        # Check destination memory allows inward flow
        to_mem_perm = self.get_memory_permeability(to_memory_id)
        if to_mem_perm and not Permeability(to_mem_perm).allows_inward():
            return False

        # Get ALL compartments for both memories
        from_comps = self.get_memory_compartments(from_memory_id)
        to_comps = self.get_memory_compartments(to_memory_id)

        # Fail-safe: ALL source compartments must allow outward flow
        for comp in from_comps:
            perm = Permeability(comp.get("permeability", "open"))
            if not perm.allows_outward():
                return False

        # Fail-safe: ALL destination compartments must allow inward flow
        for comp in to_comps:
            perm = Permeability(comp.get("permeability", "open"))
            if not perm.allows_inward():
                return False

        # Check connection permeability (if provided)
        if connection_permeability:
            conn_perm = Permeability(connection_permeability)
            # Connection permeability is from perspective of the "owner" (first memory in link)
            # For data to flow from->to, we need the connection to allow that direction
            # This depends on which direction the connection was created
            # For simplicity, we treat OSMOTIC_INWARD as allowing flow toward the connection owner
            if not conn_perm.allows_inward():
                return False

        return True

    def set_connection_permeability(self, memory_id_1: str, memory_id_2: str,
                                    permeability: Permeability):
        """Set the permeability of a specific connection."""
        query = """
        MATCH (m1:Memory {id: $id1})-[r:RELATES_TO]->(m2:Memory {id: $id2})
        SET r.permeability = $perm
        """
        self._run_write(query, {"id1": memory_id_1, "id2": memory_id_2, "perm": permeability.value})

    def get_connection_permeability(self, memory_id_1: str, memory_id_2: str) -> Optional[str]:
        """Get the permeability of a specific connection."""
        query = """
        MATCH (m1:Memory {id: $id1})-[r:RELATES_TO]->(m2:Memory {id: $id2})
        RETURN r.permeability AS permeability
        """
        result = self._run_query(query, {"id1": memory_id_1, "id2": memory_id_2})
        return result[0]["permeability"] if result else None

    def get_memory_permeability(self, memory_id: str) -> Optional[str]:
        """Get the permeability of a specific memory."""
        query = """
        MATCH (m:Memory {id: $id})
        RETURN m.permeability AS permeability
        """
        result = self._run_query(query, {"id": memory_id})
        return result[0]["permeability"] if result else None

    def set_memory_permeability(self, memory_ids, permeability: Permeability):
        """Set the permeability of one or more memories.

        Args:
            memory_ids: Single memory ID (str) or list of memory IDs
            permeability: The new permeability setting
        """
        # Normalize to list
        if isinstance(memory_ids, str):
            memory_ids = [memory_ids]

        for memory_id in memory_ids:
            query = """
            MATCH (m:Memory {id: $id})
            SET m.permeability = $perm
            """
            self._run_write(query, {"id": memory_id, "perm": permeability.value})

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
        if check_compartments and not self.can_form_connection(memory_id_1, memory_id_2):
            return False

        perm_value = permeability.value if permeability else Permeability.OPEN.value
        query = """
        MATCH (m1:Memory), (m2:Memory)
        WHERE m1.id = $id1 AND m2.id = $id2
        CREATE (m1)-[:RELATES_TO {strength: $strength, relType: $relType, permeability: $perm}]->(m2)
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
        """Weaken the connection between two memories.

        This emulates synaptic depression - connections weaken when not reinforced.

        Args:
            memory_id_1: First memory ID
            memory_id_2: Second memory ID
            amount: Override for weakening amount. If None, uses config.
        """
        # Get current strength to apply curve
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
        """Increase the relevance of a concept to a memory.

        Use when a concept proves particularly useful for retrieving this memory.
        """
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
        """Strengthen connections between all memories accessed together.

        When multiple memories are retrieved in the same context, strengthen
        all pairwise connections. This implements "neurons that fire together
        wire together".

        If plasticity.hebbian_creates_connections is True, creates new connections
        between memories that aren't already linked (subject to compartment rules).

        Args:
            memory_ids: List of memory IDs that were accessed together
            amount: Override for strengthening amount. If None, uses config.
            respect_compartments: If True, new connections won't be created across
                                 compartment boundaries that disallow external connections.
        """
        # Strengthen all pairwise connections
        for i, id1 in enumerate(memory_ids):
            for id2 in memory_ids[i+1:]:
                # Check if connection exists
                strength = self.get_memory_link_strength(id1, id2)
                if strength is None and self.plasticity.hebbian_creates_connections:
                    # Check compartment rules before creating new connection
                    if respect_compartments and not self.can_form_connection(id1, id2):
                        continue  # Skip - compartment rules block this connection

                    # Create new connection with initial implicit strength
                    initial = self.plasticity.get_initial_strength(explicit=False)
                    self.link_memories(id1, id2, initial, "hebbian")
                    self.link_memories(id2, id1, initial, "hebbian")
                elif strength is not None:
                    # Use hebbian context for effective amount (only if connection exists)
                    effective = amount if amount else self.plasticity.effective_amount('hebbian', strength)
                    self.strengthen_memory_link(id1, id2, effective)
                    self.strengthen_memory_link(id2, id1, effective)

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
            decay_amount = self.plasticity.effective_amount('decay', 0.5)

        if decay_amount <= 0:
            return

        min_strength = self.plasticity.min_strength

        if self.plasticity.decay_all:
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
            min_strength = self.plasticity.prune_threshold

        query = """
        MATCH (m1:Memory)-[r:RELATES_TO]->(m2:Memory)
        WHERE r.strength <= $min_strength
        DELETE r
        """
        self._run_write(query, {"min_strength": min_strength})

    def get_strongest_connections(self, memory_id: str, limit: int = 10,
                                  respect_permeability: bool = True) -> List[Dict]:
        """Get the strongest connections from a memory (most relevant associations).

        Args:
            memory_id: ID of the memory to find connections for
            limit: Maximum number of results
            respect_permeability: If True, filters results based on compartment permeability.

        Returns:
            Memories sorted by connection strength, highest first.
        """
        # Fetch extra to account for permeability filtering
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
        """Get the weakest connections from a memory (candidates for pruning).

        Args:
            memory_id: ID of the memory to find connections for
            limit: Maximum number of results
            respect_permeability: If True, filters results based on compartment permeability.

        Returns:
            Memories sorted by connection strength, lowest first.
        """
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
            "pruning_candidates": sum(1 for s in strengths if s <= self.plasticity.prune_threshold),
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

        # Boost concept relevance if accessed via concept
        if via_concept_id:
            self.strengthen_concept_relevance(memory_id, via_concept_id)

        # Weaken competitors if enabled
        if self.plasticity.retrieval_weakens_competitors:
            self._weaken_competitors(memory_id)

    def _weaken_competitors(self, accessed_memory_id: str):
        """Weaken memories that are related to but weren't accessed.

        This implements retrieval-induced forgetting - accessing one memory
        can make related memories harder to recall.
        """
        # Use weaken amount scaled by competitor_distance
        amount = self.plasticity.weaken_amount * self.plasticity.learning_rate * self.plasticity.competitor_distance
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
        """Strengthen all memory connections to a question.

        Call when a question is answered or progressed.
        """
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

    def get_related_memories(self, memory_id: str, hops: int = 2, limit: int = 20,
                             respect_permeability: bool = True) -> List[Dict]:
        """Get memories related to a given memory through shared concepts/keywords/topics.

        Args:
            memory_id: ID of the memory to find relations for
            hops: Number of relationship hops (currently only used for direct relations)
            limit: Maximum number of results
            respect_permeability: If True, filters results based on compartment permeability.
                                 Only returns memories whose data can flow to the requester.
        """
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
        # Request more than needed to account for permeability filtering
        fetch_limit = limit * 3 if respect_permeability else limit
        results = self._run_query(query, {"id": memory_id, "limit": fetch_limit})

        # Also check keyword relationships
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
            # Merge results avoiding duplicates
            seen_ids = {r["id"] for r in results}
            for r in keyword_results:
                if r["id"] not in seen_ids:
                    results.append(r)
                    seen_ids.add(r["id"])

        # Filter by permeability if requested
        if respect_permeability:
            results = self._filter_by_permeability(memory_id, results)

        return results[:limit]

    def _filter_by_permeability(self, requester_memory_id: str, results: List[Dict]) -> List[Dict]:
        """Filter query results based on permeability rules.

        Data flows FROM each result TO the requester, so:
        - Result's compartment must allow OUTWARD flow
        - Requester's compartment must allow INWARD flow
        """
        if not results:
            return results

        filtered = []
        for r in results:
            if self.can_data_flow(r["id"], requester_memory_id):
                filtered.append(r)
        return filtered

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
            "Contradiction": "MATCH (n:Contradiction) RETURN n.id AS id, n.description AS description, n.status AS status, n.created AS created",
            "Compartment": "MATCH (n:Compartment) RETURN n.id AS id, n.name AS name, n.permeability AS permeability, n.allowExternalConnections AS allowExternalConnections, n.description AS description, n.created AS created"
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
            "TemporalMarker", "Contradiction", "Compartment"
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
                    elif node_type == "Concept":
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
            "TemporalMarker", "Contradiction", "Compartment"
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
    confidence: float = 1.0,
    compartment_id: str = None  # Optional compartment (None uses active compartment)
) -> str:
    """Quickly store a memory with its associations.

    Args:
        client: MemoryGraphClient instance
        content: Full memory content
        summary: Brief summary of the memory
        concepts: List of concept names to associate
        keywords: List of keyword terms to associate
        topics: List of topic names to associate
        entities: List of (name, type) tuples for entities
        confidence: Confidence level (0-1)
        compartment_id: Optional compartment ID. If None, uses client's active compartment.
                       Pass empty string "" to create without compartment.
    """
    # Create the memory (will use active compartment if compartment_id is None)
    memory = Memory(content=content, summary=summary, confidence=confidence)
    memory_id = client.create_memory(memory, compartment_id=compartment_id)

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
