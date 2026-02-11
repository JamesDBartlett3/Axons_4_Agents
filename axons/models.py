"""Data models (dataclasses) for the Axons memory graph system."""

import uuid
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass, field

from .enums import (
    EntityType, SourceType, GoalStatus, QuestionStatus,
    ContextType, ContextStatus, TemporalType, ContradictionStatus,
    Permeability,
)


def _validate_range(value: float, min_val: float, max_val: float, name: str) -> float:
    """Validate a numeric value is within range, raise ValueError if not."""
    if not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number, got {type(value).__name__}")
    if value < min_val or value > max_val:
        raise ValueError(f"{name} must be between {min_val} and {max_val}, got {value}")
    return float(value)


def _validate_required_str(value: str, name: str) -> str:
    """Validate a required string field is not empty or None."""
    if not value or not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required and cannot be empty")
    return value


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

    def __post_init__(self):
        _validate_required_str(self.content, "content")
        _validate_required_str(self.summary, "summary")
        self.confidence = _validate_range(self.confidence, 0.0, 1.0, "confidence")


@dataclass
class Concept:
    name: str
    description: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        _validate_required_str(self.name, "name")


@dataclass
class Keyword:
    term: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        _validate_required_str(self.term, "term")


@dataclass
class Topic:
    name: str
    description: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        _validate_required_str(self.name, "name")


@dataclass
class Entity:
    name: str
    type: EntityType
    description: str = ""
    aliases: List[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        _validate_required_str(self.name, "name")


@dataclass
class Source:
    type: SourceType
    reference: str
    title: str = ""
    reliability: float = 1.0
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        _validate_required_str(self.reference, "reference")
        self.reliability = _validate_range(self.reliability, 0.0, 1.0, "reliability")


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

    def __post_init__(self):
        _validate_required_str(self.category, "category")
        _validate_required_str(self.preference, "preference")
        self.strength = _validate_range(self.strength, -1.0, 1.0, "strength")


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
