"""Axons — Graph-based memory system for AI agents."""

from .enums import (
    EntityType,
    SourceType,
    GoalStatus,
    QuestionStatus,
    ContextType,
    ContextStatus,
    TemporalType,
    ContradictionStatus,
    Curve,
    Permeability,
)

from .models import (
    Memory,
    Concept,
    Keyword,
    Topic,
    Entity,
    Source,
    Decision,
    Goal,
    Question,
    Context,
    Preference,
    TemporalMarker,
    Contradiction,
    Compartment,
)

from .plasticity import PlasticityConfig

from .client import (
    MemoryGraphClient,
    create_client,
    quick_store_memory,
)

__all__ = [
    # Client
    "MemoryGraphClient",
    "create_client",
    "quick_store_memory",
    # Enums
    "EntityType",
    "SourceType",
    "GoalStatus",
    "QuestionStatus",
    "ContextType",
    "ContextStatus",
    "TemporalType",
    "ContradictionStatus",
    "Curve",
    "Permeability",
    # Models
    "Memory",
    "Concept",
    "Keyword",
    "Topic",
    "Entity",
    "Source",
    "Decision",
    "Goal",
    "Question",
    "Context",
    "Preference",
    "TemporalMarker",
    "Contradiction",
    "Compartment",
    # Plasticity
    "PlasticityConfig",
]
