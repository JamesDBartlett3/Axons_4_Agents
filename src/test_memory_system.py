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
    Decision, Goal, Question, Context, Preference,
    EntityType, SourceType, GoalStatus, QuestionStatus, ContextType,
    PlasticityConfig, Curve,
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
        results["plasticity"] = test_plasticity_config()
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
