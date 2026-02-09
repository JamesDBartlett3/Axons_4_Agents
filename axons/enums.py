"""Enumeration types for the Axons memory graph system."""

from enum import Enum


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
