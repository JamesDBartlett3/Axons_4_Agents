"""
Test script for the Memory Graph System.
Verifies connection to KùzuDB and tests basic operations.

Cross-platform compatible: Works on Windows, macOS, and Linux.
"""

import sys
import os
import shutil
import tempfile
import uuid
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from memory_client import (
    MemoryGraphClient,
    Memory, Concept, Keyword, Topic, Entity, Source,
    Decision, Goal, Question, Context, Preference, Compartment,
    EntityType, SourceType, GoalStatus, QuestionStatus, ContextType,
    PlasticityConfig, Curve, Permeability,
    quick_store_memory
)


# Use a temporary directory for test database
TEST_DB_PATH = None


def get_test_db_path():
    """Get or create a temporary database path for testing."""
    global TEST_DB_PATH
    if TEST_DB_PATH is None:
        # KùzuDB creates the directory itself, so we just need a unique path
        # that doesn't exist yet
        temp_dir = tempfile.gettempdir()
        TEST_DB_PATH = os.path.join(temp_dir, f"axons_test_{uuid.uuid4().hex[:8]}")
    return TEST_DB_PATH


def test_connection():
    """Test basic connection to KùzuDB."""
    print("Testing connection to KùzuDB...")
    try:
        client = MemoryGraphClient(db_path=get_test_db_path())
        # Simple query to verify connection - just check we can initialize
        client.initialize_schema()
        print("  Connection successful!")
        client.close()
        return True
    except Exception as e:
        print(f"  Connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_schema_initialization():
    """Test schema initialization."""
    print("\nInitializing schema...")
    try:
        with MemoryGraphClient(db_path=get_test_db_path()) as client:
            client.initialize_schema()
        print("  Schema initialized!")
        return True
    except Exception as e:
        print(f"  Schema initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_create_memory():
    """Test creating a memory with associations."""
    print("\nTesting memory creation...")
    try:
        with MemoryGraphClient(db_path=get_test_db_path()) as client:
            client.initialize_schema()

            # Create a test memory
            memory_id = quick_store_memory(
                client,
                content="User prefers to use KùzuDB for graph database needs because it's cross-platform and easy to install.",
                summary="User preference for KùzuDB database",
                concepts=["graph database", "data persistence", "cross-platform"],
                keywords=["kuzu", "embedded", "simple"],
                topics=["Technology Preferences", "Software Architecture"],
                entities=[("User", "person"), ("KùzuDB", "technology")],
                confidence=1.0
            )
            print(f"  Created memory: {memory_id}")

            # Verify memory was created
            memory = client.get_memory(memory_id)
            assert memory is not None
            print(f"  Retrieved memory: {memory['summary']}")

        return True
    except Exception as e:
        print(f"  Memory creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_relationships():
    """Test creating and querying relationships."""
    print("\nTesting relationships...")
    try:
        with MemoryGraphClient(db_path=get_test_db_path()) as client:
            client.initialize_schema()

            # Create two related memories
            memory1_id = quick_store_memory(
                client,
                content="The memory graph system uses KùzuDB as its backend database.",
                summary="Memory system architecture decision",
                concepts=["architecture", "graph database"],
                keywords=["kuzu", "memory system"],
                topics=["Software Architecture"]
            )

            memory2_id = quick_store_memory(
                client,
                content="KùzuDB was chosen for its cross-platform compatibility and simple installation.",
                summary="Database selection rationale",
                concepts=["architecture", "cross-platform", "graph database"],
                keywords=["kuzu", "pip install", "comparison"],
                topics=["Software Architecture", "Technology Decisions"]
            )

            # Link the memories
            client.link_memories(memory1_id, memory2_id, strength=0.9, rel_type="context")
            print("  Created memory relationship")

            # Query related memories
            related = client.get_related_memories(memory1_id, hops=2)
            print(f"  Found {len(related)} related memories")

            # Query by concept
            arch_memories = client.get_memories_by_concept("architecture")
            print(f"  Found {len(arch_memories)} memories with 'architecture' concept")

        return True
    except Exception as e:
        print(f"  Relationship test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_goals_and_questions():
    """Test goals and questions functionality."""
    print("\nTesting goals and questions...")
    try:
        with MemoryGraphClient(db_path=get_test_db_path()) as client:
            client.initialize_schema()

            # Create a goal
            goal = Goal(
                description="Build a comprehensive memory system for AI agents",
                status=GoalStatus.ACTIVE,
                priority=1
            )
            goal_id = client.create_goal(goal)
            print(f"  Created goal: {goal_id}")

            # Create a question
            question = Question(
                text="What additional node types might be useful for the memory system?",
                status=QuestionStatus.OPEN
            )
            question_id = client.create_question(question)
            print(f"  Created question: {question_id}")

            # Get active goals
            active_goals = client.get_active_goals()
            print(f"  Found {len(active_goals)} active goals")

            # Get open questions
            open_questions = client.get_open_questions()
            print(f"  Found {len(open_questions)} open questions")

        return True
    except Exception as e:
        print(f"  Goals/questions test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_directory_export():
    """Test directory markdown export."""
    print("\nTesting directory export...")
    try:
        with MemoryGraphClient(db_path=get_test_db_path()) as client:
            client.initialize_schema()

            markdown = client.export_directory_markdown()
            print("  Generated directory markdown:")
            print("-" * 40)
            # Print first 50 lines
            for line in markdown.split("\n")[:50]:
                print(f"  {line}")
            print("-" * 40)

            # Save to file
            directory_path = Path(__file__).parent / "directory.md"
            with open(directory_path, "w") as f:
                f.write(markdown)
            print(f"  Saved to {directory_path}")

        return True
    except Exception as e:
        print(f"  Directory export failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_plasticity_config():
    """Test plasticity configuration and brain-like learning."""
    print("\nTesting plasticity configuration...")
    try:
        # Test with custom plasticity config
        config = PlasticityConfig(
            learning_rate=1.00000,
            strengthen_amount=0.20000,
            hebbian_amount=0.10000,
            decay_curve=Curve.EXPONENTIAL,
            retrieval_strengthens=True,
            retrieval_amount=0.05000,
        )

        with MemoryGraphClient(db_path=get_test_db_path(), plasticity_config=config) as client:
            client.initialize_schema()

            # Create two memories and link them
            memory1_id = quick_store_memory(
                client,
                content="First test memory for plasticity.",
                summary="Plasticity test memory 1",
                concepts=["testing"],
                keywords=["plasticity"],
            )

            memory2_id = quick_store_memory(
                client,
                content="Second test memory for plasticity.",
                summary="Plasticity test memory 2",
                concepts=["testing"],
                keywords=["plasticity"],
            )

            # Link the memories with initial strength
            client.link_memories(memory1_id, memory2_id, strength=0.5)
            print(f"  Initial link strength: 0.5")

            # Strengthen the connection
            client.strengthen_memory_link(memory1_id, memory2_id)
            new_strength = client.get_memory_link_strength(memory1_id, memory2_id)
            print(f"  After strengthening: {new_strength:.3f}")
            assert new_strength > 0.5, "Strength should increase"

            # Test Hebbian learning (co-accessed memories)
            client.apply_hebbian_learning([memory1_id, memory2_id])
            after_hebbian = client.get_memory_link_strength(memory1_id, memory2_id)
            print(f"  After Hebbian learning: {after_hebbian:.3f}")
            assert after_hebbian >= new_strength, "Hebbian learning should strengthen"

            # Test decay
            client.decay_weak_connections(threshold=1.0, decay_amount=0.1)
            after_decay = client.get_memory_link_strength(memory1_id, memory2_id)
            print(f"  After decay: {after_decay:.3f}")

            # Test connection statistics
            stats = client.get_connection_statistics()
            print(f"  Connection stats: {stats['count']} connections, avg={stats['avg']:.3f}")

            # Test preset configs
            aggressive = PlasticityConfig.aggressive_learning()
            conservative = PlasticityConfig.conservative_learning()
            no_plasticity = PlasticityConfig.no_plasticity()
            print(f"  Preset configs loaded: aggressive (lr={aggressive.learning_rate}), " +
                  f"conservative (lr={conservative.learning_rate}), " +
                  f"no_plasticity (lr={no_plasticity.learning_rate})")

            # Test config serialization
            config_dict = config.to_dict()
            restored_config = PlasticityConfig.from_dict(config_dict)
            assert restored_config.learning_rate == config.learning_rate
            print("  Config serialization: OK")

        return True
    except Exception as e:
        print(f"  Plasticity test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_plasticity_weaken_and_bounds():
    """Test weakening connections and strength bounds."""
    print("\nTesting weakening and bounds...")
    try:
        config = PlasticityConfig(
            weaken_amount=0.15,
            max_strength=0.9,
            min_strength=0.1,
        )

        with MemoryGraphClient(db_path=get_test_db_path(), plasticity_config=config) as client:
            client.initialize_schema()

            # Create and link memories
            m1 = quick_store_memory(client, content="Memory A", summary="A")
            m2 = quick_store_memory(client, content="Memory B", summary="B")
            client.link_memories(m1, m2, strength=0.5)

            # Test weakening
            client.weaken_memory_link(m1, m2)
            strength = client.get_memory_link_strength(m1, m2)
            print(f"  After weakening: {strength:.3f}")
            assert strength < 0.5, "Strength should decrease"

            # Test max_strength bound
            client.link_memories(m1, m2, strength=0.95)  # Try to exceed max
            strength = client.get_memory_link_strength(m1, m2)
            # Note: link_memories directly sets strength, bounds are for operations

            # Strengthen repeatedly to test max bound
            for _ in range(20):
                client.strengthen_memory_link(m1, m2, amount=0.1)
            strength = client.get_memory_link_strength(m1, m2)
            print(f"  After max strengthening: {strength:.3f}")
            assert strength <= 1.0, "Strength should not exceed 1.0"

            # Weaken repeatedly to test min bound
            for _ in range(20):
                client.weaken_memory_link(m1, m2, amount=0.1)
            strength = client.get_memory_link_strength(m1, m2)
            print(f"  After max weakening: {strength:.3f}")
            assert strength >= 0.0, "Strength should not go below 0.0"

        print("  Weaken and bounds: OK")
        return True
    except Exception as e:
        print(f"  Weaken/bounds test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_plasticity_initial_strength():
    """Test initial strength for explicit vs implicit connections."""
    print("\nTesting initial strength...")
    try:
        config = PlasticityConfig(
            initial_strength_explicit=0.6,
            initial_strength_implicit=0.25,
            hebbian_creates_connections=True,
        )

        # Test get_initial_strength method
        explicit_strength = config.get_initial_strength(explicit=True)
        implicit_strength = config.get_initial_strength(explicit=False)
        print(f"  Explicit initial: {explicit_strength:.3f}")
        print(f"  Implicit initial: {implicit_strength:.3f}")
        assert explicit_strength == 0.6, "Explicit should be 0.6"
        assert implicit_strength == 0.25, "Implicit should be 0.25"

        # Test with semantic similarity (mock function)
        config_sim = PlasticityConfig(
            initial_strength_explicit=0.5,
            initial_strength_implicit=0.3,
            use_semantic_similarity=True,
            max_strength=1.0,
        )
        # Set a mock similarity function that always returns 0.8
        config_sim.set_semantic_similarity_fn(lambda s1, s2: 0.8)

        # With similarity=0.8, base=0.5, max=1.0: 0.5 + (0.5 * 0.8) = 0.9
        boosted = config_sim.get_initial_strength(True, "content1", "content2")
        print(f"  With semantic boost (0.8): {boosted:.3f}")
        assert abs(boosted - 0.9) < 0.001, f"Should be ~0.9, got {boosted}"

        # Test that low similarity still boosts (never weakens)
        config_sim.set_semantic_similarity_fn(lambda s1, s2: 0.1)
        low_boost = config_sim.get_initial_strength(True, "content1", "content2")
        print(f"  With low similarity (0.1): {low_boost:.3f}")
        assert low_boost >= 0.5, "Should not go below base strength"

        # Test Hebbian creating new connections with implicit strength
        with MemoryGraphClient(db_path=get_test_db_path(), plasticity_config=config) as client:
            client.initialize_schema()
            m1 = quick_store_memory(client, content="Memory X", summary="X")
            m2 = quick_store_memory(client, content="Memory Y", summary="Y")

            # No link exists yet
            initial = client.get_memory_link_strength(m1, m2)
            assert initial is None, "Should have no link initially"

            # Hebbian learning should create implicit connection
            client.apply_hebbian_learning([m1, m2])
            created = client.get_memory_link_strength(m1, m2)
            print(f"  Hebbian-created link strength: {created:.3f}")
            assert created is not None, "Hebbian should create link"
            assert abs(created - 0.25) < 0.1, "Should be near implicit initial strength"

        print("  Initial strength: OK")
        return True
    except Exception as e:
        print(f"  Initial strength test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_plasticity_curves():
    """Test different plasticity curves."""
    print("\nTesting plasticity curves...")
    try:
        # Test LINEAR curve
        linear_config = PlasticityConfig(
            curve=Curve.LINEAR,
            strengthen_amount=0.1,
        )
        linear_low = linear_config.effective_amount('strengthen', 0.2)
        linear_high = linear_config.effective_amount('strengthen', 0.8)
        print(f"  LINEAR at 0.2: {linear_low:.4f}, at 0.8: {linear_high:.4f}")
        assert abs(linear_low - linear_high) < 0.001, "LINEAR should be constant"

        # Test EXPONENTIAL curve (harder to change near limits)
        exp_config = PlasticityConfig(
            curve=Curve.EXPONENTIAL,
            strengthen_amount=0.1,
            curve_steepness=0.5,
        )
        exp_low = exp_config.effective_amount('strengthen', 0.2)
        exp_high = exp_config.effective_amount('strengthen', 0.8)
        print(f"  EXPONENTIAL at 0.2: {exp_low:.4f}, at 0.8: {exp_high:.4f}")
        assert exp_low > exp_high, "EXPONENTIAL should be easier at low strength"

        # Test LOGARITHMIC curve (easier to change near limits)
        log_config = PlasticityConfig(
            curve=Curve.LOGARITHMIC,
            strengthen_amount=0.1,
            curve_steepness=0.5,
        )
        log_low = log_config.effective_amount('strengthen', 0.2)
        log_high = log_config.effective_amount('strengthen', 0.8)
        print(f"  LOGARITHMIC at 0.2: {log_low:.4f}, at 0.8: {log_high:.4f}")
        assert log_low < log_high, "LOGARITHMIC should be easier at high strength"

        # Test curve_steepness effect
        # Lower steepness = higher exponent = more uniform in middle, drops at edges
        # Higher steepness = lower exponent = more gradual variation throughout
        low_steep = PlasticityConfig(curve=Curve.EXPONENTIAL, curve_steepness=0.1, strengthen_amount=0.1)
        high_steep = PlasticityConfig(curve=Curve.EXPONENTIAL, curve_steepness=0.9, strengthen_amount=0.1)
        low_diff = low_steep.effective_amount('strengthen', 0.2) - low_steep.effective_amount('strengthen', 0.8)
        high_diff = high_steep.effective_amount('strengthen', 0.2) - high_steep.effective_amount('strengthen', 0.8)
        print(f"  Low steepness diff: {low_diff:.4f}, High steepness diff: {high_diff:.4f}")
        assert low_diff != high_diff, "Different steepness should produce different effects"

        print("  Curves: OK")
        return True
    except Exception as e:
        print(f"  Curves test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_plasticity_decay_and_pruning():
    """Test decay threshold, decay_all, and pruning."""
    print("\nTesting decay and pruning...")
    try:
        # Test decay_threshold - only weak connections decay
        config = PlasticityConfig(
            decay_threshold=0.5,
            decay_amount=0.1,
            decay_all=False,
            auto_prune=False,
        )

        with MemoryGraphClient(db_path=get_test_db_path(), plasticity_config=config) as client:
            client.initialize_schema()

            m1 = quick_store_memory(client, content="A", summary="A")
            m2 = quick_store_memory(client, content="B", summary="B")
            m3 = quick_store_memory(client, content="C", summary="C")

            # Create weak and strong connections
            client.link_memories(m1, m2, strength=0.3)  # Below threshold
            client.link_memories(m1, m3, strength=0.7)  # Above threshold

            # Run decay
            client.decay_weak_connections()

            weak_after = client.get_memory_link_strength(m1, m2)
            strong_after = client.get_memory_link_strength(m1, m3)
            print(f"  Weak connection after decay: {weak_after:.3f}")
            print(f"  Strong connection after decay: {strong_after:.3f}")
            assert weak_after < 0.3, "Weak connection should decay"
            assert strong_after == 0.7, "Strong connection should not decay"

        # Test decay_all
        config_all = PlasticityConfig(
            decay_threshold=0.5,
            decay_amount=0.1,
            decay_all=True,
            auto_prune=False,
        )

        with MemoryGraphClient(db_path=get_test_db_path(), plasticity_config=config_all) as client:
            client.initialize_schema()

            m1 = quick_store_memory(client, content="D", summary="D")
            m2 = quick_store_memory(client, content="E", summary="E")
            client.link_memories(m1, m2, strength=0.8)  # Strong connection

            client.decay_weak_connections()
            after = client.get_memory_link_strength(m1, m2)
            print(f"  Strong with decay_all: {after:.3f}")
            assert after < 0.8, "Should decay even strong connections when decay_all=True"

        # Test pruning
        config_prune = PlasticityConfig(
            prune_threshold=0.1,
            auto_prune=False,
        )

        with MemoryGraphClient(db_path=get_test_db_path(), plasticity_config=config_prune) as client:
            client.initialize_schema()

            m1 = quick_store_memory(client, content="F", summary="F")
            m2 = quick_store_memory(client, content="G", summary="G")
            m3 = quick_store_memory(client, content="H", summary="H")

            client.link_memories(m1, m2, strength=0.05)  # Below prune threshold
            client.link_memories(m1, m3, strength=0.2)   # Above prune threshold

            client.prune_dead_connections()

            pruned = client.get_memory_link_strength(m1, m2)
            kept = client.get_memory_link_strength(m1, m3)
            print(f"  Connection at 0.05 after prune: {pruned}")
            print(f"  Connection at 0.2 after prune: {kept}")
            assert pruned is None, "Should prune connections below threshold"
            assert kept == 0.2, "Should keep connections above threshold"

        # Test auto_prune during decay
        config_auto = PlasticityConfig(
            decay_amount=0.5,
            prune_threshold=0.1,
            auto_prune=True,
            decay_threshold=1.0,  # Decay all
        )

        with MemoryGraphClient(db_path=get_test_db_path(), plasticity_config=config_auto) as client:
            client.initialize_schema()

            m1 = quick_store_memory(client, content="I", summary="I")
            m2 = quick_store_memory(client, content="J", summary="J")
            client.link_memories(m1, m2, strength=0.15)

            # Decay should bring it below prune threshold, auto_prune should remove it
            client.decay_weak_connections()
            after = client.get_memory_link_strength(m1, m2)
            print(f"  After decay with auto_prune: {after}")
            assert after is None, "Auto-prune should remove decayed connection"

        print("  Decay and pruning: OK")
        return True
    except Exception as e:
        print(f"  Decay/pruning test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_plasticity_learning_rate():
    """Test learning_rate as global multiplier."""
    print("\nTesting learning rate...")
    try:
        # Test learning_rate=0 disables plasticity
        config_disabled = PlasticityConfig(
            learning_rate=0.0,
            strengthen_amount=0.2,
        )

        with MemoryGraphClient(db_path=get_test_db_path(), plasticity_config=config_disabled) as client:
            client.initialize_schema()

            m1 = quick_store_memory(client, content="LR0-A", summary="A")
            m2 = quick_store_memory(client, content="LR0-B", summary="B")
            client.link_memories(m1, m2, strength=0.5)

            # Strengthening should have no effect
            client.strengthen_memory_link(m1, m2)
            after = client.get_memory_link_strength(m1, m2)
            print(f"  With learning_rate=0 after strengthen: {after:.3f}")
            assert after == 0.5, "learning_rate=0 should disable strengthening"

        # Test learning_rate=0.5 reduces effect by half
        config_half = PlasticityConfig(
            learning_rate=0.5,
            strengthen_amount=0.2,
            curve=Curve.LINEAR,
        )
        config_full = PlasticityConfig(
            learning_rate=1.0,
            strengthen_amount=0.2,
            curve=Curve.LINEAR,
        )

        half_amount = config_half.effective_amount('strengthen', 0.5)
        full_amount = config_full.effective_amount('strengthen', 0.5)
        print(f"  Half rate amount: {half_amount:.4f}, Full rate: {full_amount:.4f}")
        assert abs(half_amount - full_amount / 2) < 0.001, "learning_rate should scale linearly"

        print("  Learning rate: OK")
        return True
    except Exception as e:
        print(f"  Learning rate test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_plasticity_maintenance():
    """Test maintenance cycle and strongest connections."""
    print("\nTesting maintenance operations...")
    try:
        config = PlasticityConfig(
            decay_amount=0.1,
            decay_threshold=1.0,
            prune_threshold=0.05,
            auto_prune=True,
        )

        with MemoryGraphClient(db_path=get_test_db_path(), plasticity_config=config) as client:
            client.initialize_schema()

            # Create multiple memories with varying connection strengths
            m1 = quick_store_memory(client, content="Main", summary="Main")
            m2 = quick_store_memory(client, content="Strong", summary="Strong")
            m3 = quick_store_memory(client, content="Medium", summary="Medium")
            m4 = quick_store_memory(client, content="Weak", summary="Weak")

            client.link_memories(m1, m2, strength=0.9)
            client.link_memories(m1, m3, strength=0.5)
            client.link_memories(m1, m4, strength=0.1)

            # Test get_strongest_connections
            strongest = client.get_strongest_connections(m1, limit=2)
            print(f"  Strongest connections: {len(strongest)} returned")
            assert len(strongest) == 2, "Should return 2 connections"
            assert strongest[0]['strength'] >= strongest[1]['strength'], "Should be sorted by strength"

            # Test run_maintenance_cycle
            client.run_maintenance_cycle()
            stats = client.get_connection_statistics()
            print(f"  After maintenance: {stats['count']} connections")

            # The weak connection (0.1) should decay and possibly be pruned
            weak_after = client.get_memory_link_strength(m1, m4)
            print(f"  Weak connection after maintenance: {weak_after}")

        print("  Maintenance: OK")
        return True
    except Exception as e:
        print(f"  Maintenance test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_plasticity_presets():
    """Test all preset configurations."""
    print("\nTesting preset configurations...")
    try:
        # Test all presets can be created
        default = PlasticityConfig.default()
        aggressive = PlasticityConfig.aggressive_learning()
        conservative = PlasticityConfig.conservative_learning()
        no_plasticity = PlasticityConfig.no_plasticity()
        high_decay = PlasticityConfig.high_decay()

        print(f"  default: lr={default.learning_rate}")
        print(f"  aggressive: lr={aggressive.learning_rate}, strengthen={aggressive.strengthen_amount}")
        print(f"  conservative: lr={conservative.learning_rate}, curve={conservative.curve.value}")
        print(f"  no_plasticity: lr={no_plasticity.learning_rate}, retrieval_strengthens={no_plasticity.retrieval_strengthens}")
        print(f"  high_decay: decay_all={high_decay.decay_all}, prune={high_decay.prune_threshold}")

        # Verify key properties
        assert no_plasticity.learning_rate == 0.0, "no_plasticity should have lr=0"
        assert no_plasticity.retrieval_strengthens == False, "no_plasticity should disable retrieval strengthening"
        assert aggressive.strengthen_amount > default.strengthen_amount, "aggressive should have higher strengthen"
        assert conservative.learning_rate < default.learning_rate, "conservative should have lower lr"
        assert high_decay.decay_all == True, "high_decay should decay all"

        print("  Presets: OK")
        return True
    except Exception as e:
        print(f"  Presets test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_compartment_basic():
    """Test basic compartment creation and memory assignment."""
    print("\nTesting compartment basics...")
    try:
        with MemoryGraphClient(db_path=get_test_db_path()) as client:
            client.initialize_schema()

            # Create a compartment
            comp = Compartment(
                name="Project Alpha",
                permeability=Permeability.CLOSED,
                allow_external_connections=False,
                description="A secure project compartment"
            )
            comp_id = client.create_compartment(comp)
            print(f"  Created compartment: {comp_id[:8]}")

            # Verify compartment was created
            retrieved = client.get_compartment(comp_id)
            assert retrieved is not None, "Should retrieve compartment"
            assert retrieved["name"] == "Project Alpha", "Name should match"
            assert retrieved["permeability"] == "closed", "Permeability should be closed"
            print(f"  Retrieved compartment: {retrieved['name']}")

            # Test get by name
            by_name = client.get_compartment_by_name("Project Alpha")
            assert by_name is not None, "Should find by name"
            assert by_name["id"] == comp_id, "IDs should match"
            print("  Get by name: OK")

            # Create memory in compartment
            m1 = quick_store_memory(
                client, content="Secret data", summary="Secret",
                compartment_id=comp_id
            )

            # Verify memory is in compartment
            comps = client.get_memory_compartments(m1)
            assert len(comps) > 0, "Memory should have compartment"
            assert comps[0]["id"] == comp_id, "Should be in correct compartment"
            print("  Memory in compartment: OK")

            # Test active compartment
            client.set_active_compartment(comp_id)
            assert client.get_active_compartment() == comp_id, "Active should be set"

            m2 = quick_store_memory(
                client, content="Another secret", summary="Secret 2"
            )
            comps2 = client.get_memory_compartments(m2)
            assert len(comps2) > 0, "Should use active compartment"
            assert comps2[0]["id"] == comp_id, "Should be in active compartment"
            print("  Active compartment: OK")

            # Test get memories in compartment
            memories = client.get_memories_in_compartment(comp_id)
            assert len(memories) == 2, f"Should have 2 memories, got {len(memories)}"
            print(f"  Memories in compartment: {len(memories)}")

            # Test remove from compartment
            client.remove_memory_from_compartment(m1)
            comps = client.get_memory_compartments(m1)
            assert len(comps) == 0, "Should be removed from compartment"
            print("  Remove from compartment: OK")

            # Test update compartment
            client.update_compartment(comp_id, permeability=Permeability.OPEN)
            updated = client.get_compartment(comp_id)
            assert updated["permeability"] == "open", "Permeability should be updated"
            print("  Update compartment: OK")

        print("  Compartment basics: OK")
        return True
    except Exception as e:
        print(f"  Compartment basics test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_compartment_connection_formation():
    """Test that compartments control organic connection formation."""
    print("\nTesting compartment connection formation...")
    try:
        with MemoryGraphClient(db_path=get_test_db_path()) as client:
            client.initialize_schema()

            # Create a closed compartment that blocks external connections
            closed_comp = Compartment(
                name="Closed Project",
                permeability=Permeability.CLOSED,
                allow_external_connections=False
            )
            closed_id = client.create_compartment(closed_comp)

            # Create an open compartment
            open_comp = Compartment(
                name="Open Project",
                permeability=Permeability.OPEN,
                allow_external_connections=True
            )
            open_id = client.create_compartment(open_comp)

            # Create memories in each compartment
            m_closed = quick_store_memory(
                client, content="Closed memory", summary="Closed",
                compartment_id=closed_id
            )
            m_open = quick_store_memory(
                client, content="Open memory", summary="Open",
                compartment_id=open_id
            )
            m_global = quick_store_memory(
                client, content="Global memory", summary="Global",
                compartment_id=""  # No compartment
            )

            # Test can_form_connection
            # Same compartment - should allow
            m_closed2 = quick_store_memory(
                client, content="Another closed", summary="Closed 2",
                compartment_id=closed_id
            )
            assert client.can_form_connection(m_closed, m_closed2), "Same compartment should allow"
            print("  Same compartment: allowed")

            # Closed to open - should block (closed doesn't allow external)
            assert not client.can_form_connection(m_closed, m_open), "Closed to open should block"
            print("  Closed to open: blocked")

            # Closed to global - should block
            assert not client.can_form_connection(m_closed, m_global), "Closed to global should block"
            print("  Closed to global: blocked")

            # Open to global - should allow (open allows external)
            assert client.can_form_connection(m_open, m_global), "Open to global should allow"
            print("  Open to global: allowed")

            # Test Hebbian learning respects compartments
            client.apply_hebbian_learning([m_closed, m_open], respect_compartments=True)
            link_strength = client.get_memory_link_strength(m_closed, m_open)
            assert link_strength is None, "Hebbian should not create cross-compartment link"
            print("  Hebbian respects compartments: OK")

            # But explicit linking can still work (with check_compartments=False)
            result = client.link_memories(m_closed, m_open, check_compartments=True)
            assert result == False, "link_memories with check should return False"
            print("  Explicit link with check: blocked")

            # Force link without check
            result = client.link_memories(m_closed, m_open, check_compartments=False)
            assert result == True, "link_memories without check should work"
            link_strength = client.get_memory_link_strength(m_closed, m_open)
            assert link_strength is not None, "Forced link should exist"
            print("  Explicit link without check: allowed")

        print("  Connection formation: OK")
        return True
    except Exception as e:
        print(f"  Connection formation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_compartment_permeability():
    """Test permeability controls for data flow direction."""
    print("\nTesting compartment permeability...")
    try:
        with MemoryGraphClient(db_path=get_test_db_path()) as client:
            client.initialize_schema()

            # Test Permeability enum methods
            assert Permeability.OPEN.allows_inward() == True
            assert Permeability.OPEN.allows_outward() == True
            assert Permeability.CLOSED.allows_inward() == False
            assert Permeability.CLOSED.allows_outward() == False
            assert Permeability.OSMOTIC_INWARD.allows_inward() == True
            assert Permeability.OSMOTIC_INWARD.allows_outward() == False
            assert Permeability.OSMOTIC_OUTWARD.allows_inward() == False
            assert Permeability.OSMOTIC_OUTWARD.allows_outward() == True
            print("  Permeability enum: OK")

            # Create compartments with different permeabilities
            # OSMOTIC_INWARD: can pull data in, but doesn't leak out
            secure_comp = Compartment(
                name="Secure",
                permeability=Permeability.OSMOTIC_INWARD,
                allow_external_connections=True  # Allow connections for testing
            )
            secure_id = client.create_compartment(secure_comp)

            # OSMOTIC_OUTWARD: shares data out, but doesn't pull in
            public_comp = Compartment(
                name="Public",
                permeability=Permeability.OSMOTIC_OUTWARD,
                allow_external_connections=True
            )
            public_id = client.create_compartment(public_comp)

            # Create memories
            m_secure = quick_store_memory(
                client, content="Secure data", summary="Secure",
                compartment_id=secure_id
            )
            m_public = quick_store_memory(
                client, content="Public data", summary="Public",
                compartment_id=public_id
            )
            m_global = quick_store_memory(
                client, content="Global data", summary="Global",
                compartment_id=""
            )

            # Create explicit links
            client.link_memories(m_secure, m_public)
            client.link_memories(m_public, m_global)

            # Test can_data_flow
            # From public to secure (secure pulls in) - should work
            assert client.can_data_flow(m_public, m_secure), "Secure should pull from public"
            print("  Secure pulls from public: allowed")

            # From secure to public (secure leaking out) - should block
            assert not client.can_data_flow(m_secure, m_public), "Secure should not leak to public"
            print("  Secure leaking to public: blocked")

            # From global to public (public pulling in) - should block (public is OSMOTIC_OUTWARD)
            assert not client.can_data_flow(m_global, m_public), "Public should not pull from global"
            print("  Public pulling from global: blocked")

            # From public to global (public sharing out) - should work
            assert client.can_data_flow(m_public, m_global), "Public should share to global"
            print("  Public sharing to global: allowed")

        print("  Permeability: OK")
        return True
    except Exception as e:
        print(f"  Permeability test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_compartment_query_filtering():
    """Test that queries respect permeability rules."""
    print("\nTesting compartment query filtering...")
    try:
        with MemoryGraphClient(db_path=get_test_db_path()) as client:
            client.initialize_schema()

            # Create a secure compartment (OSMOTIC_INWARD - can see out, outsiders can't see in)
            secure_comp = Compartment(
                name="Secure Zone",
                permeability=Permeability.OSMOTIC_INWARD,
                allow_external_connections=True
            )
            secure_id = client.create_compartment(secure_comp)

            # Create memories with shared concept
            m_secure = quick_store_memory(
                client, content="Secret project data", summary="Secret",
                concepts=["project"], compartment_id=secure_id
            )
            m_global = quick_store_memory(
                client, content="Public project info", summary="Public",
                concepts=["project"], compartment_id=""
            )

            # Create explicit connections
            client.link_memories(m_secure, m_global)
            client.link_memories(m_global, m_secure)

            # Query from secure memory should see global (pulling data in)
            related_from_secure = client.get_related_memories(
                m_secure, respect_permeability=True
            )
            global_ids = [r["id"] for r in related_from_secure]
            assert m_global in global_ids, "Secure should see global via shared concept"
            print("  Query from secure sees global: OK")

            # Query from global memory should NOT see secure (can't pull from secure)
            related_from_global = client.get_related_memories(
                m_global, respect_permeability=True
            )
            secure_ids = [r["id"] for r in related_from_global]
            assert m_secure not in secure_ids, "Global should not see secure"
            print("  Query from global doesn't see secure: OK")

            # But with respect_permeability=False, it should see both
            related_no_filter = client.get_related_memories(
                m_global, respect_permeability=False
            )
            all_ids = [r["id"] for r in related_no_filter]
            # Note: This depends on how get_related_memories finds relations
            # It uses shared concepts, so it should find the secure memory
            print(f"  Query without permeability filter: {len(related_no_filter)} results")

        print("  Query filtering: OK")
        return True
    except Exception as e:
        print(f"  Query filtering test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_compartment_connection_permeability():
    """Test connection-level permeability overrides."""
    print("\nTesting connection permeability...")
    try:
        with MemoryGraphClient(db_path=get_test_db_path()) as client:
            client.initialize_schema()

            # Create memories (no compartments for simplicity)
            m1 = quick_store_memory(
                client, content="Memory 1", summary="M1", compartment_id=""
            )
            m2 = quick_store_memory(
                client, content="Memory 2", summary="M2", compartment_id=""
            )

            # Create connection with specific permeability
            client.link_memories(m1, m2, permeability=Permeability.OSMOTIC_INWARD)

            # Verify permeability was set
            perm = client.get_connection_permeability(m1, m2)
            assert perm == "osmotic_inward", f"Permeability should be osmotic_inward, got {perm}"
            print(f"  Initial permeability: {perm}")

            # Update permeability
            client.set_connection_permeability(m1, m2, Permeability.CLOSED)
            perm = client.get_connection_permeability(m1, m2)
            assert perm == "closed", f"Permeability should be closed, got {perm}"
            print(f"  Updated permeability: {perm}")

            # Test that connection permeability affects data flow
            # With CLOSED, data should not flow
            assert not client.can_data_flow(m2, m1, connection_permeability="closed"), \
                "Closed connection should block data flow"
            print("  Closed connection blocks flow: OK")

            # Set to OPEN
            client.set_connection_permeability(m1, m2, Permeability.OPEN)
            assert client.can_data_flow(m2, m1, connection_permeability="open"), \
                "Open connection should allow data flow"
            print("  Open connection allows flow: OK")

        print("  Connection permeability: OK")
        return True
    except Exception as e:
        print(f"  Connection permeability test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_memory_permeability():
    """Test memory-level permeability controls."""
    print("\nTesting memory permeability...")
    try:
        with MemoryGraphClient(db_path=get_test_db_path()) as client:
            client.initialize_schema()

            # Create memory with specific permeability
            closed_mem = Memory(
                content="Closed memory",
                summary="Closed",
                permeability=Permeability.CLOSED
            )
            m_closed = client.create_memory(closed_mem)

            outward_mem = Memory(
                content="Outward memory",
                summary="Outward",
                permeability=Permeability.OSMOTIC_OUTWARD
            )
            m_outward = client.create_memory(outward_mem)

            inward_mem = Memory(
                content="Inward memory",
                summary="Inward",
                permeability=Permeability.OSMOTIC_INWARD
            )
            m_inward = client.create_memory(inward_mem)

            open_mem = Memory(
                content="Open memory",
                summary="Open",
                permeability=Permeability.OPEN
            )
            m_open = client.create_memory(open_mem)

            # Create links between them
            client.link_memories(m_open, m_closed)
            client.link_memories(m_open, m_outward)
            client.link_memories(m_open, m_inward)

            # Test get_memory_permeability
            assert client.get_memory_permeability(m_closed) == "closed"
            assert client.get_memory_permeability(m_outward) == "osmotic_outward"
            assert client.get_memory_permeability(m_inward) == "osmotic_inward"
            assert client.get_memory_permeability(m_open) == "open"
            print("  Get permeability: OK")

            # Test can_data_flow with memory-level permeability
            # CLOSED memory: nothing in or out
            assert not client.can_data_flow(m_closed, m_open), "Closed should not flow out"
            assert not client.can_data_flow(m_open, m_closed), "Closed should not accept in"
            print("  Closed memory blocks all: OK")

            # OSMOTIC_OUTWARD: data flows OUT, not in
            assert client.can_data_flow(m_outward, m_open), "Outward should flow out"
            assert not client.can_data_flow(m_open, m_outward), "Outward should not accept in"
            print("  Osmotic outward: flows out only: OK")

            # OSMOTIC_INWARD: data flows IN, not out
            assert not client.can_data_flow(m_inward, m_open), "Inward should not flow out"
            assert client.can_data_flow(m_open, m_inward), "Inward should accept in"
            print("  Osmotic inward: flows in only: OK")

            # OPEN: bidirectional
            assert client.can_data_flow(m_open, m_inward), "Open to inward should work"
            assert client.can_data_flow(m_outward, m_open), "Outward to open should work"
            print("  Open: bidirectional: OK")

            # Test set_memory_permeability
            client.set_memory_permeability(m_closed, Permeability.OPEN)
            assert client.get_memory_permeability(m_closed) == "open"
            # Now data should flow
            assert client.can_data_flow(m_closed, m_open), "Updated to open should flow"
            print("  Set permeability: OK")

        print("  Memory permeability: OK")
        return True
    except Exception as e:
        print(f"  Memory permeability test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_overlapping_compartments():
    """Test overlapping compartments with fail-safe logic."""
    print("\nTesting overlapping compartments...")
    try:
        with MemoryGraphClient(db_path=get_test_db_path()) as client:
            client.initialize_schema()

            # Create compartments with different permeabilities
            open_comp = Compartment(name="Open", permeability=Permeability.OPEN)
            open_id = client.create_compartment(open_comp)

            secure_comp = Compartment(
                name="Secure",
                permeability=Permeability.OSMOTIC_INWARD,
                allow_external_connections=True
            )
            secure_id = client.create_compartment(secure_comp)

            closed_comp = Compartment(
                name="Closed",
                permeability=Permeability.CLOSED,
                allow_external_connections=False
            )
            closed_id = client.create_compartment(closed_comp)

            # Create memories
            m1 = quick_store_memory(client, content="Memory 1", summary="M1", compartment_id="")
            m2 = quick_store_memory(client, content="Memory 2", summary="M2", compartment_id="")
            m3 = quick_store_memory(client, content="Memory 3", summary="M3", compartment_id="")

            # Test: Add memory to multiple compartments
            client.add_memory_to_compartment(m1, open_id)
            client.add_memory_to_compartment(m1, secure_id)

            comps = client.get_memory_compartments(m1)
            assert len(comps) == 2, f"Should have 2 compartments, got {len(comps)}"
            print("  Memory in multiple compartments: OK")

            # Test: Fail-safe data flow
            # m1 is in OPEN and OSMOTIC_INWARD
            # Data can flow IN (both allow inward)
            # Data cannot flow OUT (OSMOTIC_INWARD blocks outward)
            client.add_memory_to_compartment(m2, open_id)  # m2 in OPEN only
            client.link_memories(m1, m2)

            # m2 -> m1: Should work (m1 allows inward from both compartments)
            assert client.can_data_flow(m2, m1), "Data should flow into multi-compartment memory"
            print("  Fail-safe inward flow: OK")

            # m1 -> m2: Should block (Secure compartment blocks outward)
            assert not client.can_data_flow(m1, m2), "Secure compartment should block outward"
            print("  Fail-safe outward block: OK")

            # Test: Connection formation - same compartment set
            # m1 is in [open, secure], put m3 in same set
            client.add_memory_to_compartment(m3, open_id)
            client.add_memory_to_compartment(m3, secure_id)
            # Should allow connection (they're in exactly the same compartments)
            assert client.can_form_connection(m1, m3), "Should allow connection within same compartment set"
            print("  Same compartment set allows connection: OK")

            # Test: Connection formation with closed compartment
            m4 = quick_store_memory(client, content="Memory 4", summary="M4", compartment_id="")
            client.add_memory_to_compartment(m4, open_id)
            client.add_memory_to_compartment(m4, closed_id)
            # m4 is in OPEN and CLOSED (allow_external_connections=False)
            # Connection should be blocked due to CLOSED
            assert not client.can_form_connection(m4, m2), "Closed compartment should block external connection"
            print("  Closed compartment blocks connection: OK")

            # Test: Remove from specific compartment
            client.remove_memory_from_compartment(m1, secure_id)
            comps = client.get_memory_compartments(m1)
            assert len(comps) == 1, f"Should have 1 compartment after removal, got {len(comps)}"
            assert comps[0]["id"] == open_id, "Should still be in Open compartment"
            print("  Remove from specific compartment: OK")

            # Now m1 -> m2 should work (only in OPEN now)
            assert client.can_data_flow(m1, m2), "After removing Secure, data should flow"
            print("  Data flows after compartment removal: OK")

            # Test: Remove from all compartments
            client.remove_memory_from_compartment(m1)
            comps = client.get_memory_compartments(m1)
            assert len(comps) == 0, "Should have no compartments after full removal"
            print("  Remove from all compartments: OK")

        print("  Overlapping compartments: OK")
        return True
    except Exception as e:
        print(f"  Overlapping compartments test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def cleanup_test_data():
    """Remove all test data from the database."""
    print("\nCleaning up test data...")
    global TEST_DB_PATH
    try:
        if TEST_DB_PATH and Path(TEST_DB_PATH).exists():
            # On Windows, need to handle locked files more carefully
            import time
            time.sleep(0.1)  # Brief pause to ensure handles are released
            shutil.rmtree(TEST_DB_PATH, ignore_errors=True)
            TEST_DB_PATH = None
        print("  Cleanup complete!")
        return True
    except Exception as e:
        print(f"  Cleanup warning: {e}")
        # Not a critical failure - temp files will be cleaned up by OS
        return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Memory Graph System Test Suite (KùzuDB)")
    print("=" * 60)

    results = {}

    # Run tests
    results["connection"] = test_connection()

    if results["connection"]:
        results["schema"] = test_schema_initialization()
        results["memory"] = test_create_memory()
        results["relationships"] = test_relationships()
        results["goals_questions"] = test_goals_and_questions()
        results["plasticity_basic"] = test_plasticity_config()
        results["plasticity_weaken_bounds"] = test_plasticity_weaken_and_bounds()
        results["plasticity_initial_strength"] = test_plasticity_initial_strength()
        results["plasticity_curves"] = test_plasticity_curves()
        results["plasticity_decay_prune"] = test_plasticity_decay_and_pruning()
        results["plasticity_learning_rate"] = test_plasticity_learning_rate()
        results["plasticity_maintenance"] = test_plasticity_maintenance()
        results["plasticity_presets"] = test_plasticity_presets()
        results["compartment_basic"] = test_compartment_basic()
        results["compartment_connection"] = test_compartment_connection_formation()
        results["compartment_permeability"] = test_compartment_permeability()
        results["compartment_query"] = test_compartment_query_filtering()
        results["compartment_conn_perm"] = test_compartment_connection_permeability()
        results["memory_permeability"] = test_memory_permeability()
        results["overlapping_compartments"] = test_overlapping_compartments()
        results["directory"] = test_directory_export()

    # Always cleanup
    cleanup_test_data()

    # Summary
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {test_name}: {status}")

    all_passed = all(results.values())
    print("\n" + ("All tests passed!" if all_passed else "Some tests failed."))

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
