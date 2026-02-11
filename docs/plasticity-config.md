# Plasticity Configuration Guide

This document describes all tuneable parameters for the brain-like plasticity system.

## Overview

The plasticity system emulates how biological neural networks learn:
- **Hebbian Learning**: "Neurons that fire together wire together" - co-accessed memories strengthen their connections
- **Synaptic Potentiation**: Connections can be strengthened through use
- **Synaptic Depression**: Connections weaken when not reinforced
- **Synaptic Pruning**: Very weak connections are removed entirely
- **Retrieval-Induced Modification**: Accessing a memory changes how it's stored (like human recall)

All behavior is controlled by `PlasticityConfig`, which can be customized or use presets.

## Design Principles

1. **Independent amounts**: Each operation context has its own base amount (not shared)
2. **Unified curves**: The same `Curve` enum works for both plasticity and decay
3. **0-1 scale**: All numeric values are floats between 0.0 and 1.0
4. **Symmetrical operations**: Strengthening and weakening use the same curve (inverted)

## Quick Start

```python
from memory_client import MemoryGraphClient, PlasticityConfig, Curve

# Default configuration (balanced)
client = MemoryGraphClient()

# Custom configuration
config = PlasticityConfig(
    learning_rate=1.0,
    strengthen_amount=0.15,
    curve=Curve.EXPONENTIAL,
    retrieval_strengthens=True,
)
client = MemoryGraphClient(plasticity_config=config)

# Use a preset
client = MemoryGraphClient(plasticity_config=PlasticityConfig.aggressive_learning())
```

---

## Configuration Parameters

### Master Control

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `learning_rate` | float | 1.0 | Global multiplier for all operations. 0=disabled, 1=normal. |

### Context-Specific Amounts

Each context has its own independent base amount. Effective amount = `context_amount * learning_rate * curve_adjustment`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `strengthen_amount` | float | 0.1 | Base amount for explicit strengthen operations |
| `weaken_amount` | float | 0.1 | Base amount for explicit weaken operations |
| `hebbian_amount` | float | 0.05 | Base amount for co-access strengthening |
| `retrieval_amount` | float | 0.02 | Base amount for retrieval-induced changes |
| `decay_amount` | float | 0.05 | Base amount for time-based decay |

### Initial Connection Strength

When new connections are created, these parameters determine the starting strength.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `initial_strength_explicit` | float | 0.5 | Starting strength for user-created/explicit connections |
| `initial_strength_implicit` | float | 0.3 | Starting strength for Hebbian/emergent connections |
| `use_semantic_similarity` | bool | False | Augment initial strength with semantic similarity |

When `use_semantic_similarity` is True, you must provide a similarity function:

```python
config = PlasticityConfig(use_semantic_similarity=True)
config.set_semantic_similarity_fn(lambda s1, s2: compute_similarity(s1, s2))
```

The function should accept two strings and return a float (0-1). Semantic similarity can only **boost** the initial strength, never weaken it. The similarity score scales the headroom between the base strength and `max_strength`:

```
final_strength = base + (headroom * similarity)
```

Examples (with max_strength=1.0):
- base=0.5, similarity=0.8 → 0.5 + (0.5 × 0.8) = 0.9
- base=0.5, similarity=0.2 → 0.5 + (0.5 × 0.2) = 0.6
- base=0.3, similarity=1.0 → 0.3 + (0.7 × 1.0) = 1.0

### Strength Bounds

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_strength` | float | 1.0 | Maximum connection strength (ceiling) |
| `min_strength` | float | 0.0 | Minimum connection strength (floor) |

### Plasticity Curve

The curve affects how current strength influences the rate of change. Applies symmetrically to strengthening (direct) and weakening (inverted).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `curve` | Curve | LINEAR | How current strength affects rate of change |
| `curve_steepness` | float | 0.5 | Controls curve intensity (0.1=steep, 0.9=gentle) |

**Curve Types:**
- `LINEAR`: Constant rate regardless of current strength
- `EXPONENTIAL`: Harder to change connections near their limits
- `LOGARITHMIC`: Easier to change connections near their limits

### Time-Based Decay

Decay is automatic weakening based on time/cycles, separate from explicit weaken operations.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `decay_curve` | Curve | EXPONENTIAL | How time affects decay rate |
| `decay_half_life` | float | 0.1 | Fraction of 100 cycles for half-life (0.1=10 cycles) |
| `decay_threshold` | float | 0.5 | Only connections below this decay |
| `decay_all` | bool | False | If True, all connections decay regardless of strength |

### Pruning

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `prune_threshold` | float | 0.01 | Remove connections at or below this strength |
| `auto_prune` | bool | True | Automatically prune during decay operations |

### Retrieval Effects

These parameters control how accessing/recalling a memory affects the graph.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `retrieval_strengthens` | bool | True | Accessing strengthens connections to the memory |
| `retrieval_weakens_competitors` | bool | False | Also weaken related but not-accessed memories |
| `competitor_distance` | float | 0.1 | How much to scale competitor weakening |

### Hebbian Learning

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `hebbian_creates_connections` | bool | True | Create new links between co-accessed memories |

Note: The initial strength for Hebbian-created connections is controlled by `initial_strength_implicit` (see Initial Connection Strength section above).

---

## Preset Configurations

### `PlasticityConfig.default()`
Balanced settings suitable for most use cases.

### `PlasticityConfig.aggressive_learning()`
Fast adaptation:
- `strengthen_amount=0.15`
- `hebbian_amount=0.1`
- `retrieval_amount=0.05`
- `decay_threshold=0.3`

### `PlasticityConfig.conservative_learning()`
Slow, stable learning:
- `learning_rate=0.5`
- `curve=Curve.EXPONENTIAL`
- `decay_threshold=0.7`
- `prune_threshold=0.005`

### `PlasticityConfig.no_plasticity()`
Disables all automatic plasticity:
- `learning_rate=0.0`
- `retrieval_strengthens=False`
- `auto_prune=False`

### `PlasticityConfig.high_decay()`
Aggressive forgetting:
- `decay_amount=0.1`
- `decay_threshold=0.7`
- `decay_all=True`
- `prune_threshold=0.05`
- `decay_half_life=0.05`

---

## Operations

### Manual Plasticity

```python
# Strengthen a specific connection
client.strengthen_memory_link(id1, id2, amount=0.1)

# Weaken a specific connection
client.weaken_memory_link(id1, id2, amount=0.1)

# Get current strength
strength = client.get_memory_link_strength(id1, id2)
```

### Hebbian Learning

```python
# Strengthen all connections between co-accessed memories
client.apply_hebbian_learning([id1, id2, id3])
```

### Decay and Pruning

```python
# Run decay on weak connections
client.decay_weak_connections()

# Prune near-zero connections
client.prune_dead_connections()

# Combined maintenance cycle
client.run_maintenance_cycle()

# Aggressive cleanup (multiple cycles)
client.run_aggressive_maintenance(cycles=5)
```

### Statistics

```python
# Get connection statistics
stats = client.get_connection_statistics()
print(f"Count: {stats['count']}")
print(f"Average strength: {stats['avg']:.5f}")
print(f"Below threshold: {stats['below_threshold']}")
print(f"Pruning candidates: {stats['pruning_candidates']}")
```

### Configuration Management

```python
# Get current config
config = client.get_plasticity_config()

# Update config at runtime
client.set_plasticity_config(new_config)

# Save to file
client.save_plasticity_config("my_config.json")

# Load from file
client.load_plasticity_config("my_config.json")
```

---

## Example: Custom Memory Dynamics

```python
from memory_client import MemoryGraphClient, PlasticityConfig, Curve

# Create a system that:
# - Learns quickly but forgets slowly
# - Makes it hard to strengthen already-strong connections
# - Enables retrieval-induced forgetting
config = PlasticityConfig(
    learning_rate=1.0,
    strengthen_amount=0.15,
    curve=Curve.EXPONENTIAL,
    curve_steepness=0.3,  # Steeper curve = more diminishing returns
    decay_curve=Curve.LOGARITHMIC,  # Slow decay
    decay_half_life=0.2,  # 20 cycles to halve
    retrieval_strengthens=True,
    retrieval_weakens_competitors=True,
    competitor_distance=0.2,
)

client = MemoryGraphClient(plasticity_config=config)
```

---

## Best Practices

1. **Start with defaults**: The default configuration is well-balanced for general use.

2. **Tune incrementally**: Change one parameter at a time to understand its effects.

3. **Monitor statistics**: Use `get_connection_statistics()` to understand how your graph evolves.

4. **Run maintenance**: Call `run_maintenance_cycle()` periodically (e.g., end of session).

5. **Save working configs**: Once you find settings that work, save them with `save_plasticity_config()`.

6. **Consider your use case**:
   - Long-term memory: Use conservative learning, low decay
   - Working memory: Use aggressive learning, high decay
   - Static knowledge base: Use `no_plasticity()` preset
