"""Plasticity configuration for brain-like learning behavior."""

import math
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

from .enums import Curve


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

        # self.curve == Curve.LOGARITHMIC
        # Logarithmic: slower changes near the starting point, faster near limits
        if for_increase:
            # Easier to strengthen already-strong connections
            factor = (1.0 - steepness) + (current_strength * steepness)
        else:
            # Easier to weaken already-weak connections (symmetrical)
            factor = steepness + ((1.0 - current_strength) * (1.0 - steepness))
        return amount * factor

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
        else:  # Curve.LOGARITHMIC
            return min(1.0, base * math.log1p(cycles))

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for serialization."""
        result = {}
        for key, value in self.__dict__.items():
            if key.startswith('_'):
                continue
            if isinstance(value, Enum):
                result[key] = value.value
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
