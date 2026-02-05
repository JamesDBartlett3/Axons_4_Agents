"""
Test script for the Memory Graph System.
Verifies connection to Memgraph and tests basic operations.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from memory_client import (
    MemoryGraphClient,
    Memory, Concept, Keyword, Topic, Entity, Source,
    Decision, Goal, Question, Context, Preference,
    EntityType, SourceType, GoalStatus, QuestionStatus, ContextType,
    quick_store_memory
)


def test_connection():
    """Test basic connection to Memgraph."""
    print("Testing connection to Memgraph...")
    try:
        client = MemoryGraphClient(uri="bolt://localhost:7687")
        # Simple query to verify connection
        result = client._run_query("RETURN 1 as test")
        assert result[0]["test"] == 1
        print("  Connection successful!")
        client.close()
        return True
    except Exception as e:
        print(f"  Connection failed: {e}")
        return False


def test_schema_initialization():
    """Test schema initialization."""
    print("\nInitializing schema...")
    try:
        with MemoryGraphClient(uri="bolt://localhost:7687") as client:
            client.initialize_schema()
        print("  Schema initialized!")
        return True
    except Exception as e:
        print(f"  Schema initialization failed: {e}")
        return False


def test_create_memory():
    """Test creating a memory with associations."""
    print("\nTesting memory creation...")
    try:
        with MemoryGraphClient(uri="bolt://localhost:7687") as client:
            # Create a test memory
            memory_id = quick_store_memory(
                client,
                content="James prefers to use Memgraph for graph database needs because of its speed and Cypher compatibility.",
                summary="User preference for Memgraph database",
                concepts=["graph database", "data persistence", "performance"],
                keywords=["memgraph", "cypher", "speed"],
                topics=["Technology Preferences", "Software Architecture"],
                entities=[("James", "person"), ("Memgraph", "technology")],
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
        with MemoryGraphClient(uri="bolt://localhost:7687") as client:
            # Create two related memories
            memory1_id = quick_store_memory(
                client,
                content="The memory graph system uses Memgraph as its backend database.",
                summary="Memory system architecture decision",
                concepts=["architecture", "graph database"],
                keywords=["memgraph", "memory system"],
                topics=["Software Architecture"]
            )

            memory2_id = quick_store_memory(
                client,
                content="Memgraph was chosen over Neo4j for its better performance and lower resource usage.",
                summary="Database selection rationale",
                concepts=["architecture", "performance", "graph database"],
                keywords=["memgraph", "neo4j", "comparison"],
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
        with MemoryGraphClient(uri="bolt://localhost:7687") as client:
            # Create a goal
            goal = Goal(
                description="Build a comprehensive memory system for Claude",
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
        with MemoryGraphClient(uri="bolt://localhost:7687") as client:
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


def cleanup_test_data():
    """Remove all test data from the database."""
    print("\nCleaning up test data...")
    try:
        with MemoryGraphClient(uri="bolt://localhost:7687") as client:
            client._run_write("MATCH (n) DETACH DELETE n")
        print("  Cleanup complete!")
        return True
    except Exception as e:
        print(f"  Cleanup failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Memory Graph System Test Suite")
    print("=" * 60)

    results = {}

    # Run tests
    results["connection"] = test_connection()

    if results["connection"]:
        results["schema"] = test_schema_initialization()
        results["memory"] = test_create_memory()
        results["relationships"] = test_relationships()
        results["goals_questions"] = test_goals_and_questions()
        results["directory"] = test_directory_export()

        # Optionally cleanup
        # cleanup_test_data()

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
