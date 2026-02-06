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

## Quick Start

```python
from memory_client import MemoryGraphClient, PlasticityConfig, DecayCurve

# Default configuration (balanced)
client = MemoryGraphClient()

# Custom configuration
config = PlasticityConfig(
    learning_rate=1.5,
    decay_curve=DecayCurve.EXPONENTIAL,
    retrieval_strengthens=True,
)
client = MemoryGraphClient(plasticity_config=config)

# Use a preset
client = MemoryGraphClient(plasticity_config=PlasticityConfig.aggressive_learning())
```

---

## Configuration Parameters

### Learning Rates

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `learning_rate` | float | 1.0 | Global multiplier for all plasticity operations. Set to 0 to disable all automatic plasticity. Values > 1.0 accelerate learning. |

### Strengthening Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `base_strengthening_amount` | float | 0.1 | Base amount to strengthen connections (before learning_rate multiplier) |
| `max_strength` | float | 1.0 | Maximum connection strength (ceiling) |
| `min_strength` | float | 0.0 | Minimum connection strength (floor) |
| `strengthening_curve` | StrengtheningCurve | LINEAR | How strengthening scales with current strength |
| `diminishing_factor` | float | 2.0 | For DIMINISHING curve: controls how much harder it is to strengthen strong connections |

**Strengthening Curves:**
- `LINEAR`: Constant strengthening regardless of current strength
- `DIMINISHING`: Easier to strengthen weak connections, harder to strengthen strong ones (more realistic)
- `ACCELERATING`: Easier to strengthen already-strong connections (rich-get-richer)

### Weakening Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `base_weakening_amount` | float | 0.1 | Base amount to weaken connections |
| `symmetric_curves` | bool | True | Whether weakening uses inverted strengthening curve |

### Hebbian Learning

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `hebbian_learning_amount` | float | 0.05 | Amount to strengthen when memories are co-accessed |
| `hebbian_creates_connections` | bool | True | Create new connections if none exist when co-accessed |
| `hebbian_initial_strength` | float | 0.3 | Initial strength for Hebbian-created connections |

**Usage:**
```python
# When multiple memories are accessed together
client.apply_hebbian_learning([memory_id_1, memory_id_2, memory_id_3])
```

### Decay Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `decay_curve` | DecayCurve | EXPONENTIAL | Mathematical function for decay |
| `base_decay_rate` | float | 0.05 | Base decay rate per cycle |
| `decay_threshold` | float | 0.5 | Connections below this threshold decay |
| `decay_half_life` | int | 10 | For exponential: cycles until strength halves |
| `decay_affects_all` | bool | False | If True, all connections decay (not just weak ones) |

**Decay Curves:**
- `LINEAR`: Constant decay rate over time
- `EXPONENTIAL`: Fast initial decay, slowing over time (most realistic)
- `LOGARITHMIC`: Slow initial decay, accelerating over time
- `SIGMOID`: S-curve - slow start, fast middle, slow end

**Half-Life Example:**
With `decay_half_life=10`, a connection at strength 0.8 will be approximately:
- 0.57 after 5 cycles
- 0.40 after 10 cycles
- 0.20 after 20 cycles

### Pruning Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `pruning_threshold` | float | 0.01 | Connections at or below this are pruned |
| `auto_prune` | bool | True | Automatically prune during decay operations |
| `pruning_grace_period` | int | 0 | Minimum age before pruning (reserved for future) |

### Retrieval-Induced Modification

These parameters control how accessing/recalling a memory affects the graph - emulating how human memory recall actually changes the memory.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `retrieval_strengthens` | bool | True | Accessing a memory strengthens its connections |
| `retrieval_strengthening_amount` | float | 0.02 | How much to strengthen on access |
| `retrieval_weakens_competitors` | bool | False | Weaken related but not-accessed memories |
| `competitor_weakening_amount` | float | 0.01 | How much to weaken competitors |
| `competitor_hops` | int | 1 | How many relationship hops to consider as "competitors" |

**Retrieval-Induced Forgetting:**
When `retrieval_weakens_competitors=True`, accessing memory A will slightly weaken memories B and C that are connected to A but weren't accessed. This emulates the psychological phenomenon where recalling one memory can make related memories harder to recall.

### Concept Relevance

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `concept_relevance_adjustment` | float | 0.1 | Base amount to adjust concept relevance |
| `access_boosts_concept_relevance` | bool | True | Boost concept relevance when accessed via concept search |

### Goal/Question Support

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `goal_progress_strengthening` | float | 0.1 | Strengthen memory-goal links when goal progresses |
| `question_answer_strengthening` | float | 0.15 | Strengthen memory-question links when answered |

### Time-Based Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `use_real_time_decay` | bool | False | Use wall-clock time instead of access cycles |
| `hourly_decay_rate` | float | 0.001 | Decay rate per hour (if using real time) |

### Relationship Type Weights

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `relationship_weights` | Dict[str, float] | {...} | Per-relationship-type multipliers |

**Default weights (all 1.0):**
```python
{
    "RELATES_TO": 1.0,
    "HAS_CONCEPT": 1.0,
    "HAS_KEYWORD": 1.0,
    "BELONGS_TO": 1.0,
    "MENTIONS": 1.0,
    "SUPPORTS": 1.0,
    "PARTIALLY_ANSWERS": 1.0,
}
```

---

## Preset Configurations

### `PlasticityConfig.default()`
Balanced settings suitable for most use cases.

### `PlasticityConfig.aggressive_learning()`
Fast adaptation with quick strengthening:
- `learning_rate=1.5`
- `base_strengthening_amount=0.15`
- `hebbian_learning_amount=0.1`
- `retrieval_strengthening_amount=0.05`

### `PlasticityConfig.conservative_learning()`
Slow, stable learning with gradual changes:
- `learning_rate=0.5`
- `base_strengthening_amount=0.05`
- `decay_threshold=0.7`
- `pruning_threshold=0.005`

### `PlasticityConfig.no_plasticity()`
Disables all automatic plasticity (manual operations only):
- `learning_rate=0.0`
- `retrieval_strengthens=False`
- `auto_prune=False`

### `PlasticityConfig.high_decay()`
Aggressive forgetting for memory pressure scenarios:
- `base_decay_rate=0.1`
- `decay_threshold=0.7`
- `decay_affects_all=True`
- `decay_half_life=5`

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
print(f"Average strength: {stats['avg']:.3f}")
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
from memory_client import MemoryGraphClient, PlasticityConfig, DecayCurve, StrengtheningCurve

# Create a system that:
# - Learns quickly but forgets slowly
# - Makes it hard to strengthen already-strong connections
# - Enables retrieval-induced forgetting
config = PlasticityConfig(
    learning_rate=1.2,
    strengthening_curve=StrengtheningCurve.DIMINISHING,
    diminishing_factor=3.0,  # Strong diminishing returns
    decay_curve=DecayCurve.LOGARITHMIC,  # Slow decay
    decay_half_life=20,  # Long half-life
    retrieval_strengthens=True,
    retrieval_weakens_competitors=True,
    competitor_weakening_amount=0.02,
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
   - Long-term memory: Use conservative learning, slow decay
   - Working memory: Use aggressive learning, fast decay
   - Static knowledge base: Use `no_plasticity()` preset
