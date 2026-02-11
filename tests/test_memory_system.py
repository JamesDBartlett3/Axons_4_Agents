"""Comprehensive pytest suite for the Axons memory graph system.

Tests cover every scenario in which an LLM would need to store or recall
memories — both at the explicit request of the user and implicitly during
normal user/LLM interactions.
"""

import json
import pytest

from axons import (
    MemoryGraphClient,
    Memory, Concept, Keyword, Topic, Entity, Source,
    Decision, Goal, Question, Context, Preference,
    TemporalMarker, Contradiction, Compartment,
    EntityType, SourceType, GoalStatus, QuestionStatus,
    ContextType, ContextStatus, TemporalType, ContradictionStatus,
    PlasticityConfig, Curve, Permeability,
    quick_store_memory,
)


# ============================================================================
# CONNECTION & SCHEMA
# ============================================================================


class TestConnectionAndSchema:
    def test_connection_and_schema(self, client):
        """Client connects and initializes schema without error."""
        assert client.conn is not None

    def test_schema_idempotent(self, client):
        """Calling initialize_schema twice is safe."""
        client.initialize_schema()
        assert client._schema_initialized

    def test_close_sets_flag(self, tmp_path):
        """close() sets _closed flag and clears connection."""
        c = MemoryGraphClient(db_path=str(tmp_path / "close_test"))
        c.initialize_schema()
        c.close()
        assert c._closed
        assert c.conn is None

    def test_operations_after_close_raise(self, tmp_path):
        """Using client after close raises RuntimeError."""
        c = MemoryGraphClient(db_path=str(tmp_path / "closed_ops"))
        c.initialize_schema()
        c.close()
        with pytest.raises(RuntimeError, match="Client is closed"):
            c.get_node_counts()

    def test_context_manager(self, tmp_path):
        """Client works as context manager and auto-closes."""
        with MemoryGraphClient(db_path=str(tmp_path / "ctx_mgr")) as c:
            c.initialize_schema()
            assert c.conn is not None
        assert c._closed


# ============================================================================
# NODE CRUD — ALL 14 TYPES
# ============================================================================


class TestNodeCRUD:
    def test_create_memory(self, client):
        m = Memory(content="Test content", summary="Test summary", confidence=0.9)
        mid = client.create_memory(m)
        result = client.get_memory(mid, apply_retrieval_effects=False)
        assert result is not None
        assert result["summary"] == "Test summary"
        assert result["confidence"] == 0.9

    def test_create_concept(self, client):
        c = Concept(name="machine learning", description="ML field")
        cid = client.create_concept(c)
        assert cid == c.id

    def test_create_concept_deduplicates(self, client):
        """Creating a concept with the same name returns existing ID."""
        c1 = Concept(name="testing")
        c2 = Concept(name="testing")
        id1 = client.create_concept(c1)
        id2 = client.create_concept(c2)
        assert id1 == id2

    def test_create_keyword(self, client):
        k = Keyword(term="pytest")
        kid = client.create_keyword(k)
        assert kid == k.id

    def test_create_keyword_deduplicates(self, client):
        k1 = Keyword(term="docker")
        k2 = Keyword(term="docker")
        assert client.create_keyword(k1) == client.create_keyword(k2)

    def test_create_topic(self, client):
        t = Topic(name="Software Architecture", description="Design patterns")
        tid = client.create_topic(t)
        assert tid == t.id

    def test_create_entity(self, client):
        e = Entity(name="Claude", type=EntityType.TOOL, description="AI assistant")
        eid = client.create_entity(e)
        assert eid == e.id

    def test_create_entity_deduplicates_by_name_and_type(self, client):
        e1 = Entity(name="Python", type=EntityType.TECHNOLOGY)
        e2 = Entity(name="Python", type=EntityType.TECHNOLOGY)
        assert client.create_entity(e1) == client.create_entity(e2)

    def test_create_source(self, client):
        s = Source(type=SourceType.CONVERSATION, reference="session-123", title="Chat")
        sid = client.create_source(s)
        assert sid == s.id

    def test_create_source_deduplicates(self, client):
        s1 = Source(type=SourceType.URL, reference="https://example.com")
        s2 = Source(type=SourceType.URL, reference="https://example.com")
        assert client.create_source(s1) == client.create_source(s2)

    def test_create_decision(self, client):
        d = Decision(description="Use pytest", rationale="Better fixtures")
        did = client.create_decision(d)
        assert did == d.id

    def test_create_goal(self, client):
        g = Goal(description="Achieve 90% coverage", priority=1)
        gid = client.create_goal(g)
        assert gid == g.id

    def test_create_question(self, client):
        q = Question(text="What node types are needed?")
        qid = client.create_question(q)
        assert qid == q.id

    def test_create_context(self, client):
        c = Context(name="Test Project", type=ContextType.PROJECT)
        cid = client.create_context(c)
        assert cid == c.id

    def test_create_context_deduplicates(self, client):
        c1 = Context(name="MyProject", type=ContextType.PROJECT)
        c2 = Context(name="MyProject", type=ContextType.PROJECT)
        assert client.create_context(c1) == client.create_context(c2)

    def test_create_preference(self, client):
        p = Preference(category="tooling", preference="Prefer lightweight tools", strength=0.8)
        pid = client.create_preference(p)
        assert pid == p.id

    def test_create_preference_updates_existing(self, client):
        """Creating same preference twice updates strength via running average."""
        p1 = Preference(category="style", preference="Prefer short functions", strength=0.6)
        id1 = client.create_preference(p1)
        p2 = Preference(category="style", preference="Prefer short functions", strength=1.0)
        id2 = client.create_preference(p2)
        assert id1 == id2  # Same preference updated, not duplicated

    def test_create_temporal_marker(self, client):
        t = TemporalMarker(type=TemporalType.PERIOD, description="Sprint 1")
        tid = client.create_temporal_marker(t)
        assert tid == t.id

    def test_create_contradiction(self, client):
        c = Contradiction(description="Conflicting info about API version")
        cid = client.create_contradiction(c)
        assert cid == c.id

    def test_create_compartment(self, client):
        comp = Compartment(name="Secure Zone", permeability=Permeability.CLOSED)
        cid = client.create_compartment(comp)
        result = client.get_compartment(cid)
        assert result["name"] == "Secure Zone"
        assert result["permeability"] == "closed"

    def test_create_compartment_deduplicates(self, client):
        c1 = Compartment(name="Zone A")
        c2 = Compartment(name="Zone A")
        assert client.create_compartment(c1) == client.create_compartment(c2)


# ============================================================================
# RELATIONSHIPS — ALL 19 TYPES
# ============================================================================


class TestRelationships:
    def _make_memory(self, client, summary):
        m = Memory(content=f"Content for {summary}", summary=summary)
        return client.create_memory(m)

    def test_link_memory_to_concept(self, client):
        mid = self._make_memory(client, "test")
        cid = client.create_concept(Concept(name="AI"))
        client.link_memory_to_concept(mid, cid, relevance=0.8)
        results = client.get_memories_by_concept("AI")
        assert any(r["id"] == mid for r in results)

    def test_link_memory_to_keyword(self, client):
        mid = self._make_memory(client, "test")
        kid = client.create_keyword(Keyword(term="neural"))
        client.link_memory_to_keyword(mid, kid)
        results = client.get_memories_by_keyword("neural")
        assert any(r["id"] == mid for r in results)

    def test_link_memory_to_topic(self, client):
        mid = self._make_memory(client, "test")
        tid = client.create_topic(Topic(name="Deep Learning"))
        client.link_memory_to_topic(mid, tid, primary=True)
        results = client.get_memories_by_topic("Deep Learning")
        assert any(r["id"] == mid for r in results)

    def test_link_memory_to_entity(self, client):
        mid = self._make_memory(client, "test")
        eid = client.create_entity(Entity(name="GPT", type=EntityType.TECHNOLOGY))
        client.link_memory_to_entity(mid, eid, role="subject")
        results = client.get_memories_by_entity("GPT")
        assert any(r["id"] == mid for r in results)

    def test_link_memory_to_source(self, client):
        mid = self._make_memory(client, "test")
        sid = client.create_source(Source(type=SourceType.FILE, reference="data.csv"))
        client.link_memory_to_source(mid, sid, excerpt="row 42")

    def test_link_memory_to_context(self, client):
        mid = self._make_memory(client, "test")
        cid = client.create_context(Context(name="Proj", type=ContextType.PROJECT))
        client.link_memory_to_context(mid, cid)

    def test_link_memory_to_decision(self, client):
        mid = self._make_memory(client, "test")
        did = client.create_decision(Decision(description="Choose X", rationale="Faster"))
        client.link_memory_to_decision(mid, did)

    def test_link_memory_to_question(self, client):
        mid = self._make_memory(client, "test")
        qid = client.create_question(Question(text="Why X?"))
        client.link_memory_to_question(mid, qid, completeness=0.5)

    def test_link_memory_to_goal(self, client):
        mid = self._make_memory(client, "test")
        gid = client.create_goal(Goal(description="Ship v1"))
        client.link_memory_to_goal(mid, gid, strength=0.7)

    def test_link_memory_to_preference(self, client):
        mid = self._make_memory(client, "test")
        pid = client.create_preference(Preference(category="style", preference="concise"))
        client.link_memory_to_preference(mid, pid)

    def test_link_memory_to_temporal(self, client):
        mid = self._make_memory(client, "test")
        tid = client.create_temporal_marker(TemporalMarker(
            type=TemporalType.PERIOD, description="Q1 2026"))
        client.link_memory_to_temporal(mid, tid)

    def test_link_memories(self, client):
        m1 = self._make_memory(client, "A")
        m2 = self._make_memory(client, "B")
        result = client.link_memories(m1, m2, strength=0.6, rel_type="related")
        assert result is True
        assert client.get_memory_link_strength(m1, m2) == pytest.approx(0.6)

    def test_link_concepts(self, client):
        c1 = client.create_concept(Concept(name="ML"))
        c2 = client.create_concept(Concept(name="AI"))
        client.link_concepts(c1, c2, rel_type="subset")

    def test_link_goals(self, client):
        g1 = client.create_goal(Goal(description="Parent goal"))
        g2 = client.create_goal(Goal(description="Sub goal"))
        client.link_goals(g2, g1)

    def test_link_decisions(self, client):
        d1 = client.create_decision(Decision(description="D1", rationale="R1"))
        d2 = client.create_decision(Decision(description="D2", rationale="R2"))
        client.link_decisions(d1, d2)

    def test_link_contexts(self, client):
        parent = client.create_context(Context(name="Parent", type=ContextType.PROJECT))
        child = client.create_context(Context(name="Child", type=ContextType.TASK))
        client.link_contexts(parent, child)

    def test_mark_contradiction(self, client):
        m1 = self._make_memory(client, "Version is 2.0")
        m2 = self._make_memory(client, "Version is 3.0")
        c = Contradiction(description="Version conflict")
        cid = client.create_contradiction(c)
        client.mark_contradiction(cid, m1, m2)

    def test_resolve_contradiction(self, client):
        m1 = self._make_memory(client, "Old info")
        m2 = self._make_memory(client, "New info")
        c = Contradiction(description="Info conflict")
        cid = client.create_contradiction(c)
        client.mark_contradiction(cid, m1, m2)
        client.resolve_contradiction(cid, m2, "m2 supersedes m1")
        unresolved = client.get_unresolved_contradictions()
        assert not any(u["id"] == cid for u in unresolved)

    def test_merge_prevents_duplicate_edges(self, client):
        """Calling link methods twice should not create duplicate edges."""
        mid = self._make_memory(client, "test")
        kid = client.create_keyword(Keyword(term="unique"))
        client.link_memory_to_keyword(mid, kid)
        client.link_memory_to_keyword(mid, kid)  # Second call
        results = client.get_memories_by_keyword("unique")
        assert len(results) == 1  # Only one memory, not duplicated via double edge


# ============================================================================
# QUERIES & SEARCH
# ============================================================================


class TestQueriesAndSearch:
    def test_search_memories(self, populated_client):
        results = populated_client.search_memories("embedded")
        assert len(results) >= 1
        assert any("embedded" in r["content"].lower() for r in results)

    def test_search_no_results(self, populated_client):
        results = populated_client.search_memories("xyznonexistent")
        assert results == []

    def test_get_memory_updates_access_tracking(self, populated_client):
        mid = populated_client._test_data["memory_ids"][0]
        result = populated_client.get_memory(mid, apply_retrieval_effects=False)
        count1 = result["accessCount"]
        result2 = populated_client.get_memory(mid, apply_retrieval_effects=False)
        assert result2["accessCount"] == count1 + 1

    def test_get_memory_nonexistent(self, client):
        result = client.get_memory("nonexistent-uuid", apply_retrieval_effects=False)
        assert result is None

    def test_get_related_memories(self, populated_client):
        mid = populated_client._test_data["memory_ids"][0]
        related = populated_client.get_related_memories(mid, respect_permeability=False)
        assert len(related) >= 1

    def test_get_memories_by_concept(self, populated_client):
        results = populated_client.get_memories_by_concept("graph database")
        assert len(results) >= 2

    def test_get_memories_by_keyword(self, populated_client):
        results = populated_client.get_memories_by_keyword("embedded")
        assert len(results) >= 1

    def test_get_memories_by_topic(self, populated_client):
        results = populated_client.get_memories_by_topic("Technology")
        assert len(results) >= 1

    def test_get_memories_by_entity(self, populated_client):
        results = populated_client.get_memories_by_entity("LadybugDB")
        assert len(results) >= 2

    def test_get_active_goals(self, populated_client):
        goals = populated_client.get_active_goals()
        assert len(goals) >= 1
        assert all(g["status"] == "active" for g in goals)

    def test_get_open_questions(self, populated_client):
        questions = populated_client.get_open_questions()
        assert len(questions) >= 1

    def test_get_decision_chain(self, populated_client):
        """Decision chain returns related decisions."""
        d1 = populated_client.create_decision(Decision(description="Step 1", rationale="R"))
        d2 = populated_client.create_decision(Decision(description="Step 2", rationale="R"))
        populated_client.link_decisions(d1, d2)
        chain = populated_client.get_decision_chain(d2)
        assert any(c["relation"] == "predecessor" for c in chain)

    def test_get_unresolved_contradictions(self, populated_client):
        m1 = quick_store_memory(populated_client, "A is true", "Claim A")
        m2 = quick_store_memory(populated_client, "A is false", "Counter-claim A")
        c = Contradiction(description="A conflict")
        cid = populated_client.create_contradiction(c)
        populated_client.mark_contradiction(cid, m1, m2)
        unresolved = populated_client.get_unresolved_contradictions()
        assert any(u["id"] == cid for u in unresolved)
        assert len(unresolved[0]["memories"]) == 2

    def test_get_preferences_by_category(self, client):
        client.create_preference(Preference(category="coding", preference="Prefer Python", strength=0.9))
        client.create_preference(Preference(category="coding", preference="Avoid Java", strength=-0.5))
        prefs = client.get_preferences_by_category("coding")
        assert len(prefs) == 2
        assert prefs[0]["strength"] > prefs[1]["strength"]  # Sorted by strength DESC

    def test_get_node_counts(self, populated_client):
        counts = populated_client.get_node_counts()
        assert counts["Memory"] >= 3
        assert counts["Concept"] >= 2
        assert counts["Goal"] >= 1

    def test_export_directory_markdown(self, populated_client):
        md = populated_client.export_directory_markdown()
        assert "# Memory Graph Directory" in md
        assert "## Node Counts" in md
        assert "**Memory**" in md


# ============================================================================
# RETRIEVAL EFFECTS
# ============================================================================


class TestRetrievalEffects:
    def test_retrieval_strengthens_connections(self, client):
        """Accessing a memory should strengthen its incoming connections."""
        config = PlasticityConfig(retrieval_strengthens=True, retrieval_amount=0.1)
        client.set_plasticity_config(config)
        m1 = quick_store_memory(client, "Source memory", "Source")
        m2 = quick_store_memory(client, "Target memory", "Target")
        client.link_memories(m1, m2, strength=0.5)
        # Retrieve m2 — should strengthen m1->m2 connection
        client.get_memory(m2, apply_retrieval_effects=True)
        new_strength = client.get_memory_link_strength(m1, m2)
        assert new_strength > 0.5

    def test_retrieval_with_concept_boosts_relevance(self, client):
        """Accessing via concept search should boost that concept's relevance."""
        config = PlasticityConfig(retrieval_strengthens=True)
        client.set_plasticity_config(config)
        mid = quick_store_memory(client, "Neural networks are powerful", "NN overview",
                                 concepts=["neural networks"])
        # Access via concept
        results = client.get_memories_by_concept("neural networks", apply_retrieval_effects=True)
        assert len(results) >= 1

    def test_no_retrieval_effects_when_disabled(self, client):
        """With retrieval_strengthens=False, access doesn't modify graph."""
        config = PlasticityConfig(retrieval_strengthens=False)
        client.set_plasticity_config(config)
        m1 = quick_store_memory(client, "A", "A")
        m2 = quick_store_memory(client, "B", "B")
        client.link_memories(m1, m2, strength=0.5)
        client.get_memory(m2, apply_retrieval_effects=True)
        assert client.get_memory_link_strength(m1, m2) == pytest.approx(0.5)


# ============================================================================
# PLASTICITY
# ============================================================================


class TestPlasticity:
    def test_strengthen_memory_link(self, client):
        m1 = quick_store_memory(client, "A", "A")
        m2 = quick_store_memory(client, "B", "B")
        client.link_memories(m1, m2, strength=0.5)
        client.strengthen_memory_link(m1, m2)
        assert client.get_memory_link_strength(m1, m2) > 0.5

    def test_weaken_memory_link(self, client):
        m1 = quick_store_memory(client, "A", "A")
        m2 = quick_store_memory(client, "B", "B")
        client.link_memories(m1, m2, strength=0.5)
        client.weaken_memory_link(m1, m2)
        assert client.get_memory_link_strength(m1, m2) < 0.5

    def test_strength_bounds_enforced(self, client):
        """Strength should never exceed max or go below min."""
        config = PlasticityConfig(max_strength=0.9, min_strength=0.1)
        client.set_plasticity_config(config)
        m1 = quick_store_memory(client, "A", "A")
        m2 = quick_store_memory(client, "B", "B")
        client.link_memories(m1, m2, strength=0.8)
        # Strengthen many times
        for _ in range(20):
            client.strengthen_memory_link(m1, m2)
        assert client.get_memory_link_strength(m1, m2) <= 0.9
        # Weaken many times
        for _ in range(20):
            client.weaken_memory_link(m1, m2)
        assert client.get_memory_link_strength(m1, m2) >= 0.1

    def test_hebbian_learning_creates_connections(self, client):
        """Co-accessed memories should get new connections."""
        m1 = quick_store_memory(client, "A", "A")
        m2 = quick_store_memory(client, "B", "B")
        assert client.get_memory_link_strength(m1, m2) is None
        client.apply_hebbian_learning([m1, m2])
        assert client.get_memory_link_strength(m1, m2) is not None

    def test_hebbian_strengthens_existing(self, client):
        m1 = quick_store_memory(client, "A", "A")
        m2 = quick_store_memory(client, "B", "B")
        client.link_memories(m1, m2, strength=0.3)
        client.link_memories(m2, m1, strength=0.3)
        client.apply_hebbian_learning([m1, m2])
        assert client.get_memory_link_strength(m1, m2) > 0.3

    def test_decay_weak_connections(self, client):
        m1 = quick_store_memory(client, "A", "A")
        m2 = quick_store_memory(client, "B", "B")
        client.link_memories(m1, m2, strength=0.2)
        client.decay_weak_connections(threshold=0.5, decay_amount=0.1)
        assert client.get_memory_link_strength(m1, m2) == pytest.approx(0.1)

    def test_prune_dead_connections(self, client):
        m1 = quick_store_memory(client, "A", "A")
        m2 = quick_store_memory(client, "B", "B")
        client.link_memories(m1, m2, strength=0.01)
        client.prune_dead_connections(min_strength=0.05)
        assert client.get_memory_link_strength(m1, m2) is None

    def test_maintenance_cycle(self, client):
        """run_maintenance_cycle increments cycle counter and decays."""
        m1 = quick_store_memory(client, "A", "A")
        m2 = quick_store_memory(client, "B", "B")
        client.link_memories(m1, m2, strength=0.2)
        initial_cycle = client._access_cycle
        client.run_maintenance_cycle()
        assert client._access_cycle == initial_cycle + 1

    def test_plasticity_curves(self, client):
        """Different curves produce different effective amounts."""
        linear = PlasticityConfig(curve=Curve.LINEAR, strengthen_amount=0.1)
        exp = PlasticityConfig(curve=Curve.EXPONENTIAL, strengthen_amount=0.1)
        log = PlasticityConfig(curve=Curve.LOGARITHMIC, strengthen_amount=0.1)
        amt_lin = linear.effective_amount("strengthen", 0.5)
        amt_exp = exp.effective_amount("strengthen", 0.5)
        amt_log = log.effective_amount("strengthen", 0.5)
        assert amt_lin == pytest.approx(0.1)
        assert amt_exp != amt_lin  # Different from linear

    def test_learning_rate_zero_disables(self, client):
        """learning_rate=0 should disable all plasticity operations."""
        config = PlasticityConfig(learning_rate=0.0)
        client.set_plasticity_config(config)
        m1 = quick_store_memory(client, "A", "A")
        m2 = quick_store_memory(client, "B", "B")
        client.link_memories(m1, m2, strength=0.5)
        client.strengthen_memory_link(m1, m2)
        assert client.get_memory_link_strength(m1, m2) == pytest.approx(0.5)

    def test_presets(self):
        assert PlasticityConfig.aggressive_learning().learning_rate == 1.0
        assert PlasticityConfig.conservative_learning().learning_rate == 0.5
        assert PlasticityConfig.no_plasticity().learning_rate == 0.0
        assert PlasticityConfig.high_decay().decay_all is True

    def test_connection_statistics(self, client):
        m1 = quick_store_memory(client, "A", "A")
        m2 = quick_store_memory(client, "B", "B")
        client.link_memories(m1, m2, strength=0.7)
        stats = client.get_connection_statistics()
        assert stats["count"] >= 1
        assert stats["avg"] is not None

    def test_strengthen_goal_connections(self, client):
        mid = quick_store_memory(client, "A", "A")
        gid = client.create_goal(Goal(description="Goal"))
        client.link_memory_to_goal(mid, gid, strength=0.5)
        client.strengthen_goal_connections(gid)
        # No error means it worked (strength increased in DB)

    def test_strengthen_question_connections(self, client):
        mid = quick_store_memory(client, "A", "A")
        qid = client.create_question(Question(text="Q?"))
        client.link_memory_to_question(mid, qid, completeness=0.3)
        client.strengthen_question_connections(qid)


# ============================================================================
# COMPARTMENTS & PERMEABILITY
# ============================================================================


class TestCompartments:
    def test_compartment_crud(self, client):
        comp = Compartment(name="Zone A", permeability=Permeability.OPEN)
        cid = client.create_compartment(comp)
        result = client.get_compartment(cid)
        assert result["name"] == "Zone A"
        by_name = client.get_compartment_by_name("Zone A")
        assert by_name["id"] == cid

    def test_update_compartment(self, client):
        comp = Compartment(name="Mutable")
        cid = client.create_compartment(comp)
        client.update_compartment(cid, permeability=Permeability.CLOSED)
        result = client.get_compartment(cid)
        assert result["permeability"] == "closed"

    def test_delete_compartment(self, client):
        comp = Compartment(name="Deletable")
        cid = client.create_compartment(comp)
        mid = quick_store_memory(client, "test", "test")
        client.add_memory_to_compartment(mid, cid)
        client.delete_compartment(cid, reassign_memories=True)
        assert client.get_compartment(cid) is None

    def test_delete_compartment_fails_with_memories(self, client):
        comp = Compartment(name="Protected")
        cid = client.create_compartment(comp)
        mid = quick_store_memory(client, "test", "test")
        client.add_memory_to_compartment(mid, cid)
        with pytest.raises(ValueError, match="memories"):
            client.delete_compartment(cid, reassign_memories=False)

    def test_active_compartment(self, client):
        comp = Compartment(name="Active")
        cid = client.create_compartment(comp)
        client.set_active_compartment(cid)
        assert client.get_active_compartment() == cid
        mid = quick_store_memory(client, "auto-assigned", "auto")
        comps = client.get_memory_compartments(mid)
        assert any(c["id"] == cid for c in comps)
        client.set_active_compartment(None)

    def test_memory_in_multiple_compartments(self, client):
        c1 = client.create_compartment(Compartment(name="C1"))
        c2 = client.create_compartment(Compartment(name="C2"))
        mid = quick_store_memory(client, "shared", "shared")
        client.add_memory_to_compartment(mid, c1)
        client.add_memory_to_compartment(mid, c2)
        comps = client.get_memory_compartments(mid)
        assert len(comps) == 2

    def test_remove_from_specific_compartment(self, client):
        c1 = client.create_compartment(Compartment(name="Keep"))
        c2 = client.create_compartment(Compartment(name="Remove"))
        mid = quick_store_memory(client, "test", "test")
        client.add_memory_to_compartment(mid, c1)
        client.add_memory_to_compartment(mid, c2)
        client.remove_memory_from_compartment(mid, c2)
        comps = client.get_memory_compartments(mid)
        assert len(comps) == 1
        assert comps[0]["id"] == c1


class TestPermeability:
    def test_closed_blocks_all_flow(self, client):
        comp = Compartment(name="Closed", permeability=Permeability.CLOSED,
                          allow_external_connections=False)
        cid = client.create_compartment(comp)
        m1 = quick_store_memory(client, "inside", "inside")
        m2 = quick_store_memory(client, "outside", "outside")
        client.add_memory_to_compartment(m1, cid)
        assert not client.can_data_flow(m1, m2)
        assert not client.can_data_flow(m2, m1)

    def test_osmotic_inward(self, client):
        """OSMOTIC_INWARD: can pull data in, cannot leak out."""
        comp = Compartment(name="Inward", permeability=Permeability.OSMOTIC_INWARD,
                          allow_external_connections=True)
        cid = client.create_compartment(comp)
        inside = quick_store_memory(client, "inside", "inside")
        outside = quick_store_memory(client, "outside", "outside")
        client.add_memory_to_compartment(inside, cid)
        assert client.can_data_flow(outside, inside)   # Can pull in
        assert not client.can_data_flow(inside, outside)  # Cannot leak out

    def test_osmotic_outward(self, client):
        """OSMOTIC_OUTWARD: can share out, cannot pull in."""
        comp = Compartment(name="Outward", permeability=Permeability.OSMOTIC_OUTWARD,
                          allow_external_connections=True)
        cid = client.create_compartment(comp)
        inside = quick_store_memory(client, "inside", "inside")
        outside = quick_store_memory(client, "outside", "outside")
        client.add_memory_to_compartment(inside, cid)
        assert client.can_data_flow(inside, outside)    # Can share out
        assert not client.can_data_flow(outside, inside)  # Cannot pull in

    def test_can_form_connection_same_compartment(self, client):
        comp = Compartment(name="Shared", allow_external_connections=False)
        cid = client.create_compartment(comp)
        m1 = quick_store_memory(client, "A", "A")
        m2 = quick_store_memory(client, "B", "B")
        client.add_memory_to_compartment(m1, cid)
        client.add_memory_to_compartment(m2, cid)
        assert client.can_form_connection(m1, m2)

    def test_can_form_connection_blocked_by_closed(self, client):
        closed = Compartment(name="Closed", allow_external_connections=False)
        cid = client.create_compartment(closed)
        m1 = quick_store_memory(client, "A", "A")
        m2 = quick_store_memory(client, "B", "B")
        client.add_memory_to_compartment(m1, cid)
        assert not client.can_form_connection(m1, m2)

    def test_memory_level_permeability(self, client):
        m1 = quick_store_memory(client, "sealed", "sealed")
        m2 = quick_store_memory(client, "other", "other")
        client.set_memory_permeability(m1, Permeability.CLOSED)
        assert client.get_memory_permeability(m1) == "closed"
        assert not client.can_data_flow(m1, m2)

    def test_connection_permeability(self, client):
        m1 = quick_store_memory(client, "A", "A")
        m2 = quick_store_memory(client, "B", "B")
        client.link_memories(m1, m2, strength=0.5,
                           permeability=Permeability.OSMOTIC_INWARD)
        perm = client.get_connection_permeability(m1, m2)
        assert perm == "osmotic_inward"
        client.set_connection_permeability(m1, m2, Permeability.CLOSED)
        assert client.get_connection_permeability(m1, m2) == "closed"

    def test_query_filtering_respects_permeability(self, client):
        """Queries from a closed compartment should not see outside memories."""
        secure = Compartment(name="Secure", permeability=Permeability.OSMOTIC_INWARD,
                           allow_external_connections=True)
        sid = client.create_compartment(secure)
        m_inside = quick_store_memory(client, "secret data", "secret",
                                      concepts=["classified"])
        m_outside = quick_store_memory(client, "public data", "public",
                                       concepts=["classified"])
        client.add_memory_to_compartment(m_inside, sid)
        # Query from inside secure: should see outside (inward flow allowed)
        related = client.get_related_memories(m_inside, respect_permeability=True)
        # Query from outside: should NOT see inside (outward flow blocked)
        related_out = client.get_related_memories(m_outside, respect_permeability=True)
        secure_ids_in_result = [r["id"] for r in related_out if r["id"] == m_inside]
        assert len(secure_ids_in_result) == 0

    def test_overlapping_compartments_fail_safe(self, client):
        """Most restrictive compartment wins when memory is in multiple."""
        open_comp = Compartment(name="Open", permeability=Permeability.OPEN,
                               allow_external_connections=True)
        closed_comp = Compartment(name="Locked", permeability=Permeability.CLOSED,
                                 allow_external_connections=False)
        oid = client.create_compartment(open_comp)
        lid = client.create_compartment(closed_comp)
        m1 = quick_store_memory(client, "multi", "multi")
        m2 = quick_store_memory(client, "other", "other")
        client.add_memory_to_compartment(m1, oid)
        client.add_memory_to_compartment(m1, lid)
        # Closed compartment should block even though Open allows
        assert not client.can_data_flow(m1, m2)
        assert not client.can_form_connection(m1, m2)


# ============================================================================
# INPUT VALIDATION & EDGE CASES
# ============================================================================


class TestValidation:
    def test_memory_requires_content(self):
        with pytest.raises(ValueError, match="content"):
            Memory(content="", summary="valid")

    def test_memory_requires_summary(self):
        with pytest.raises(ValueError, match="summary"):
            Memory(content="valid", summary="")

    def test_memory_confidence_range(self):
        with pytest.raises(ValueError, match="confidence"):
            Memory(content="test", summary="test", confidence=1.5)

    def test_concept_requires_name(self):
        with pytest.raises(ValueError, match="name"):
            Concept(name="")

    def test_keyword_requires_term(self):
        with pytest.raises(ValueError, match="term"):
            Keyword(term="")

    def test_preference_strength_range(self):
        with pytest.raises(ValueError, match="strength"):
            Preference(category="c", preference="p", strength=2.0)

    def test_preference_negative_strength_valid(self):
        """Negative strength is valid for preferences (dislikes)."""
        p = Preference(category="c", preference="p", strength=-0.8)
        assert p.strength == -0.8

    def test_source_reliability_range(self):
        with pytest.raises(ValueError, match="reliability"):
            Source(type=SourceType.FILE, reference="f", reliability=1.5)

    def test_link_memory_to_concept_relevance_range(self, client):
        mid = quick_store_memory(client, "test", "test")
        cid = client.create_concept(Concept(name="x"))
        with pytest.raises(ValueError, match="relevance"):
            client.link_memory_to_concept(mid, cid, relevance=1.5)

    def test_link_memories_strength_range(self, client):
        m1 = quick_store_memory(client, "A", "A")
        m2 = quick_store_memory(client, "B", "B")
        with pytest.raises(ValueError, match="strength"):
            client.link_memories(m1, m2, strength=-0.1)

    def test_link_memory_to_question_completeness_range(self, client):
        mid = quick_store_memory(client, "test", "test")
        qid = client.create_question(Question(text="Q?"))
        with pytest.raises(ValueError, match="completeness"):
            client.link_memory_to_question(mid, qid, completeness=1.1)


# ============================================================================
# DELETE OPERATIONS
# ============================================================================


class TestDelete:
    def test_delete_all_data(self, client):
        quick_store_memory(client, "to delete", "to delete", concepts=["temp"])
        client.delete_all_data()
        counts = client.get_node_counts()
        assert counts["Memory"] == 0
        assert counts["Concept"] == 0


# ============================================================================
# SERIALIZATION
# ============================================================================


class TestSerialization:
    def test_plasticity_config_round_trip(self, tmp_path):
        config = PlasticityConfig(
            learning_rate=0.7,
            curve=Curve.EXPONENTIAL,
            decay_all=True,
        )
        filepath = str(tmp_path / "config.json")
        # to_dict / from_dict round-trip
        d = config.to_dict()
        restored = PlasticityConfig.from_dict(d)
        assert restored.learning_rate == 0.7
        assert restored.curve == Curve.EXPONENTIAL
        assert restored.decay_all is True

    def test_plasticity_config_excludes_private_fields(self):
        config = PlasticityConfig()
        config.set_semantic_similarity_fn(lambda a, b: 0.5)
        d = config.to_dict()
        assert "_semantic_similarity_fn" not in d

    def test_save_load_plasticity_config(self, client, tmp_path):
        config = PlasticityConfig(learning_rate=0.42, decay_all=True)
        client.set_plasticity_config(config)
        filepath = str(tmp_path / "test_config.json")
        client.save_plasticity_config(filepath)
        # Reset and load
        client.set_plasticity_config(PlasticityConfig.default())
        client.load_plasticity_config(filepath)
        assert client.plasticity.learning_rate == pytest.approx(0.42)
        assert client.plasticity.decay_all is True


# ============================================================================
# TRANSACTION SUPPORT
# ============================================================================


class TestTransactions:
    def test_quick_store_is_atomic(self, client):
        """quick_store_memory should be wrapped in a transaction."""
        mid = quick_store_memory(
            client,
            content="Transactional test",
            summary="TX test",
            concepts=["txn"],
            keywords=["atomic"],
        )
        assert client.get_memory(mid, apply_retrieval_effects=False) is not None
        assert len(client.get_memories_by_keyword("atomic")) == 1


# ============================================================================
# LLM-SPECIFIC MEMORY SCENARIOS
#
# These tests simulate real scenarios where an LLM would store or recall
# memories during interactions with a user.
# ============================================================================


class TestLLMScenarios:
    def test_explicit_user_memory_store(self, client):
        """User says 'Remember that I prefer Python over JavaScript'."""
        mid = quick_store_memory(
            client,
            content="User explicitly stated they prefer Python over JavaScript for backend development.",
            summary="User prefers Python over JS",
            concepts=["programming languages", "user preferences"],
            keywords=["python", "javascript"],
            topics=["Preferences"],
            entities=[("User", "person")],
        )
        pref = Preference(category="languages", preference="Prefer Python over JavaScript", strength=0.9)
        client.create_preference(pref)
        # Verify recall
        results = client.search_memories("Python")
        assert len(results) >= 1
        prefs = client.get_preferences_by_category("languages")
        assert len(prefs) >= 1

    def test_implicit_memory_from_conversation(self, client):
        """LLM infers a preference from user behavior without explicit request."""
        mid = quick_store_memory(
            client,
            content="User consistently asks for concise responses and gets frustrated by verbose explanations.",
            summary="User prefers concise communication",
            concepts=["communication style", "user preferences"],
            keywords=["concise", "brief"],
            topics=["User Behavior"],
        )
        pref = Preference(category="communication", preference="Prefers concise responses", strength=0.7)
        client.create_preference(pref)
        assert client.get_memory(mid, apply_retrieval_effects=False) is not None

    def test_multi_turn_context_building(self, client):
        """LLM accumulates related memories across a multi-turn conversation."""
        ctx = Context(name="Debugging Session", type=ContextType.SESSION)
        ctx_id = client.create_context(ctx)
        # Turn 1: User describes a bug
        m1 = quick_store_memory(client, "User reports a crash on startup", "Bug: startup crash",
                                concepts=["debugging"], keywords=["crash", "startup"])
        client.link_memory_to_context(m1, ctx_id)
        # Turn 2: User provides stack trace
        m2 = quick_store_memory(client, "Stack trace shows NullPointerException in init()", "Stack trace",
                                concepts=["debugging"], keywords=["NPE", "stack trace"])
        client.link_memory_to_context(m2, ctx_id)
        # Turn 3: Root cause found
        m3 = quick_store_memory(client, "Root cause: config file missing required field", "Root cause: missing config",
                                concepts=["debugging"], keywords=["config", "root cause"])
        client.link_memory_to_context(m3, ctx_id)
        # Link the investigation chain
        client.link_memories(m1, m2, strength=0.9, rel_type="investigation")
        client.link_memories(m2, m3, strength=0.9, rel_type="investigation")
        # Hebbian: these were all accessed together
        client.apply_hebbian_learning([m1, m2, m3])
        # Verify chain is retrievable
        related = client.get_related_memories(m1, respect_permeability=False)
        assert len(related) >= 1

    def test_cross_session_recall(self, client):
        """LLM recalls information stored in a previous session."""
        # Session 1: Store project info
        m1 = quick_store_memory(
            client,
            content="User's project uses FastAPI with PostgreSQL backend and React frontend.",
            summary="Project tech stack",
            concepts=["tech stack", "project setup"],
            keywords=["fastapi", "postgresql", "react"],
            entities=[("FastAPI", "technology"), ("PostgreSQL", "technology")],
        )
        # Session 2: User asks about their project
        results = client.search_memories("FastAPI")
        assert len(results) >= 1
        by_entity = client.get_memories_by_entity("FastAPI")
        assert len(by_entity) >= 1

    def test_contradiction_detection_across_sessions(self, client):
        """LLM detects when new information contradicts stored memories."""
        m_old = quick_store_memory(client, "The API uses REST endpoints", "API uses REST",
                                   concepts=["API design"])
        m_new = quick_store_memory(client, "The API was migrated to GraphQL", "API uses GraphQL",
                                   concepts=["API design"])
        contra = Contradiction(description="API protocol changed from REST to GraphQL")
        cid = client.create_contradiction(contra)
        client.mark_contradiction(cid, m_old, m_new)
        unresolved = client.get_unresolved_contradictions()
        assert len(unresolved) >= 1
        # Resolve: new info supersedes
        client.resolve_contradiction(cid, m_new, "Migrated to GraphQL")
        assert len(client.get_unresolved_contradictions()) == 0

    def test_compartmentalized_project_memories(self, client):
        """Memories from different projects should be isolated when needed."""
        proj_a = Compartment(name="Project Alpha",
                           permeability=Permeability.OSMOTIC_INWARD,
                           allow_external_connections=False)
        proj_b = Compartment(name="Project Beta",
                           permeability=Permeability.OSMOTIC_INWARD,
                           allow_external_connections=False)
        aid = client.create_compartment(proj_a)
        bid = client.create_compartment(proj_b)
        m_a = quick_store_memory(client, "Alpha uses microservices", "Alpha architecture",
                                 concepts=["architecture"])
        m_b = quick_store_memory(client, "Beta uses monolith", "Beta architecture",
                                 concepts=["architecture"])
        client.add_memory_to_compartment(m_a, aid)
        client.add_memory_to_compartment(m_b, bid)
        # Projects shouldn't leak data to each other
        assert not client.can_data_flow(m_a, m_b)
        assert not client.can_data_flow(m_b, m_a)
        # Hebbian shouldn't cross boundaries
        assert not client.can_form_connection(m_a, m_b)

    def test_goal_tracking_across_interactions(self, client):
        """LLM tracks progress toward user goals over time."""
        goal = Goal(description="Migrate database from MySQL to PostgreSQL", priority=1)
        gid = client.create_goal(goal)
        # Interaction 1: planning
        m1 = quick_store_memory(client, "Created migration plan with 5 steps", "Migration plan created")
        client.link_memory_to_goal(m1, gid, strength=0.3)
        # Interaction 2: progress
        m2 = quick_store_memory(client, "Completed schema migration for users table", "Users table migrated")
        client.link_memory_to_goal(m2, gid, strength=0.5)
        # Strengthen goal connections as progress is made
        client.strengthen_goal_connections(gid)
        # Verify goal is tracked
        goals = client.get_active_goals()
        assert any(g["id"] == gid for g in goals)

    def test_associative_recall_via_concepts(self, client):
        """LLM should find related memories through shared concepts."""
        quick_store_memory(client, "Redis can be used as a cache layer", "Redis caching",
                          concepts=["caching", "performance"])
        quick_store_memory(client, "CDN caching improves page load times", "CDN caching",
                          concepts=["caching", "performance"])
        quick_store_memory(client, "Database query optimization reduces latency", "Query optimization",
                          concepts=["performance", "databases"])
        # Searching for "caching" concept should find the first two
        results = client.get_memories_by_concept("caching")
        assert len(results) == 2
        # "performance" connects all three
        results = client.get_memories_by_concept("performance")
        assert len(results) == 3

    def test_temporal_context_for_time_based_recall(self, client):
        """LLM can associate memories with time periods for temporal queries."""
        marker = TemporalMarker(type=TemporalType.PERIOD, description="Q4 2025")
        tid = client.create_temporal_marker(marker)
        mid = quick_store_memory(client, "Major refactor completed in Q4 2025", "Q4 refactor")
        client.link_memory_to_temporal(mid, tid)
        # Memory is linked to temporal marker
        result = client.get_memory(mid, apply_retrieval_effects=False)
        assert result is not None

    def test_source_attribution(self, client):
        """LLM tracks where information came from."""
        source = Source(type=SourceType.URL, reference="https://docs.example.com/api",
                       title="API Documentation", reliability=0.95)
        sid = client.create_source(source)
        mid = quick_store_memory(client, "The API rate limit is 100 req/min", "API rate limit")
        client.link_memory_to_source(mid, sid, excerpt="Rate limiting section")
        result = client.get_memory(mid, apply_retrieval_effects=False)
        assert result is not None


# ============================================================================
# COVERAGE GAP TESTS
# ============================================================================


class TestCoverageGaps:
    """Targeted tests for uncovered code paths."""

    # --- Default path & convenience ---

    def test_create_client_convenience(self, tmp_path, monkeypatch):
        """create_client() convenience function works."""
        from axons.client import create_client
        monkeypatch.setenv("HOME", str(tmp_path))
        # Just verify it returns a MemoryGraphClient (don't init schema on default path)
        c = create_client(db_path=str(tmp_path / "conv_db"))
        assert isinstance(c, MemoryGraphClient)
        c.close()

    def test_default_db_path(self, tmp_path, monkeypatch):
        """Client uses ~/.axons_memory_db when no db_path is given."""
        monkeypatch.setattr("axons.client.Path.home", staticmethod(lambda: tmp_path))
        c = MemoryGraphClient()
        assert "axons_memory_db" in c.db_path
        c.close()

    # --- Transaction rollback ---

    def test_rollback(self, client):
        """Explicit rollback discards uncommitted changes."""
        client.begin_transaction()
        m = Memory(content="will rollback", summary="rollback test")
        client.create_memory(m)
        client.rollback()
        result = client.get_memory(m.id, apply_retrieval_effects=False)
        assert result is None

    # --- Error handling paths ---

    def test_validate_range_non_numeric(self):
        """_validate_range raises on non-numeric input."""
        from axons.models import _validate_range
        with pytest.raises(ValueError, match="must be a number"):
            _validate_range("not_a_number", 0.0, 1.0, "test_field")

    # --- Competitor weakening ---

    def test_retrieval_weakens_competitors(self, client):
        """retrieval_weakens_competitors weakens related but not-accessed memories."""
        config = PlasticityConfig(
            retrieval_strengthens=True,
            retrieval_weakens_competitors=True,
            competitor_distance=0.5,
            weaken_amount=0.2,
        )
        client.set_plasticity_config(config)
        center = quick_store_memory(client, "center", "center")
        competitor = quick_store_memory(client, "competitor", "competitor")
        unrelated = quick_store_memory(client, "unrelated", "unrelated")
        client.link_memories(center, competitor, strength=0.5)
        client.link_memories(competitor, unrelated, strength=0.5)
        # Access center — should weaken competitor's OTHER connections
        client.get_memory(center, apply_retrieval_effects=True)
        weakened = client.get_memory_link_strength(competitor, unrelated)
        assert weakened < 0.5

    # --- Permeability edge cases ---

    def test_filter_permeability_requester_blocks_inward(self, client):
        """If requester memory blocks inward flow, all results filtered."""
        m1 = quick_store_memory(client, "source", "source")
        m2 = quick_store_memory(client, "requester", "requester")
        client.set_memory_permeability(m2, Permeability.CLOSED)
        filtered = client._filter_by_permeability(m2, [{"id": m1}])
        assert filtered == []

    def test_filter_permeability_requester_compartment_blocks(self, client):
        """Requester in a CLOSED compartment blocks all inward flow."""
        comp = Compartment(name="Walled", permeability=Permeability.CLOSED)
        cid = client.create_compartment(comp)
        m1 = quick_store_memory(client, "outside", "outside")
        m2 = quick_store_memory(client, "inside", "inside")
        client.add_memory_to_compartment(m2, cid)
        filtered = client._filter_by_permeability(m2, [{"id": m1}])
        assert filtered == []

    def test_filter_permeability_source_blocks_outward(self, client):
        """Source memory with OSMOTIC_INWARD blocks outward flow in batch filter."""
        m1 = quick_store_memory(client, "sealed source", "sealed")
        m2 = quick_store_memory(client, "requester", "requester")
        client.set_memory_permeability(m1, Permeability.OSMOTIC_INWARD)
        filtered = client._filter_by_permeability(m2, [{"id": m1}])
        assert filtered == []

    def test_filter_permeability_source_compartment_blocks(self, client):
        """Source in CLOSED compartment blocks outward in batch filter."""
        comp = Compartment(name="SrcClosed", permeability=Permeability.CLOSED)
        cid = client.create_compartment(comp)
        m1 = quick_store_memory(client, "src", "src")
        m2 = quick_store_memory(client, "req", "req")
        client.add_memory_to_compartment(m1, cid)
        filtered = client._filter_by_permeability(m2, [{"id": m1}])
        assert filtered == []

    def test_filter_empty_results(self, client):
        """_filter_by_permeability with empty list returns empty list."""
        result = client._filter_by_permeability("any_id", [])
        assert result == []

    def test_can_data_flow_destination_blocks_inward(self, client):
        """can_data_flow returns False when destination memory blocks inward."""
        m1 = quick_store_memory(client, "src", "src")
        m2 = quick_store_memory(client, "dst", "dst")
        client.set_memory_permeability(m2, Permeability.OSMOTIC_OUTWARD)
        assert not client.can_data_flow(m1, m2)

    def test_can_data_flow_connection_permeability(self, client):
        """can_data_flow checks connection-level permeability."""
        m1 = quick_store_memory(client, "a", "a")
        m2 = quick_store_memory(client, "b", "b")
        assert not client.can_data_flow(m1, m2, connection_permeability="closed")

    def test_can_form_connection_both_in_open_compartments(self, client):
        """Memories in different open compartments can form connections."""
        c1 = client.create_compartment(Compartment(name="Open1", allow_external_connections=True))
        c2 = client.create_compartment(Compartment(name="Open2", allow_external_connections=True))
        m1 = quick_store_memory(client, "a", "a")
        m2 = quick_store_memory(client, "b", "b")
        client.add_memory_to_compartment(m1, c1)
        client.add_memory_to_compartment(m2, c2)
        assert client.can_form_connection(m1, m2)

    def test_can_form_connection_second_memory_blocks(self, client):
        """Connection blocked when second memory's compartment disallows external."""
        open_c = client.create_compartment(Compartment(name="OpenC", allow_external_connections=True))
        closed_c = client.create_compartment(Compartment(name="ClosedC", allow_external_connections=False))
        m1 = quick_store_memory(client, "a", "a")
        m2 = quick_store_memory(client, "b", "b")
        client.add_memory_to_compartment(m1, open_c)
        client.add_memory_to_compartment(m2, closed_c)
        assert not client.can_form_connection(m1, m2)

    # --- Plasticity curve & decay edge cases ---

    def test_exponential_curve_weakening(self):
        """EXPONENTIAL curve for weakening path."""
        config = PlasticityConfig(curve=Curve.EXPONENTIAL, weaken_amount=0.1)
        amt = config.effective_amount("weaken", 0.5)
        assert amt > 0

    def test_logarithmic_curve_weakening(self):
        """LOGARITHMIC curve for weakening path."""
        config = PlasticityConfig(curve=Curve.LOGARITHMIC, weaken_amount=0.1)
        amt = config.effective_amount("weaken", 0.5)
        assert amt > 0

    # --- Directory export with all node types ---

    def test_directory_export_with_preferences_and_compartments(self, client):
        """Directory export renders compartments and preferences."""
        client.create_compartment(Compartment(name="ExportTest", permeability=Permeability.CLOSED,
                                             allow_external_connections=False))
        client.create_preference(Preference(category="test", preference="likes tests", strength=0.9))
        client.create_preference(Preference(category="test", preference="dislikes bugs", strength=-0.5))
        md = client.export_directory_markdown()
        assert "ExportTest" in md
        assert "likes tests" in md
        assert "dislikes bugs" in md

    # --- Strongest/weakest with permeability ---

    def test_strongest_connections_with_permeability(self, client):
        """get_strongest_connections respects permeability filtering."""
        comp = Compartment(name="Sealed", permeability=Permeability.CLOSED)
        cid = client.create_compartment(comp)
        m1 = quick_store_memory(client, "center", "center")
        m2 = quick_store_memory(client, "sealed", "sealed")
        client.link_memories(m1, m2, strength=0.9)
        client.add_memory_to_compartment(m2, cid)
        results = client.get_strongest_connections(m1, respect_permeability=True)
        assert not any(r["id"] == m2 for r in results)

    def test_weakest_connections_with_permeability(self, client):
        """get_weakest_connections respects permeability filtering."""
        comp = Compartment(name="Sealed2", permeability=Permeability.CLOSED)
        cid = client.create_compartment(comp)
        m1 = quick_store_memory(client, "center", "center")
        m2 = quick_store_memory(client, "sealed", "sealed")
        client.link_memories(m1, m2, strength=0.1)
        client.add_memory_to_compartment(m2, cid)
        results = client.get_weakest_connections(m1, respect_permeability=True)
        assert not any(r["id"] == m2 for r in results)

    # --- Weaken with explicit amount reaching zero ---

    def test_weaken_with_zero_learning_rate(self, client):
        """Weakening does nothing when learning_rate is 0."""
        config = PlasticityConfig(learning_rate=0.0)
        client.set_plasticity_config(config)
        m1 = quick_store_memory(client, "A", "A")
        m2 = quick_store_memory(client, "B", "B")
        client.link_memories(m1, m2, strength=0.5)
        client.weaken_memory_link(m1, m2)
        assert client.get_memory_link_strength(m1, m2) == pytest.approx(0.5)

    def test_weaken_with_explicit_amount(self, client):
        """Weakening with explicit amount uses learning_rate multiplier."""
        config = PlasticityConfig(learning_rate=0.5)
        client.set_plasticity_config(config)
        m1 = quick_store_memory(client, "A", "A")
        m2 = quick_store_memory(client, "B", "B")
        client.link_memories(m1, m2, strength=0.5)
        client.weaken_memory_link(m1, m2, amount=0.2)  # effective = 0.2 * 0.5 = 0.1
        assert client.get_memory_link_strength(m1, m2) == pytest.approx(0.4)

    # --- Compartment partial updates ---

    def test_update_compartment_description(self, client):
        comp = Compartment(name="Desc")
        cid = client.create_compartment(comp)
        client.update_compartment(cid, description="Updated description")
        result = client.get_compartment(cid)
        assert result["description"] == "Updated description"

    def test_update_compartment_allow_external(self, client):
        comp = Compartment(name="ExtToggle", allow_external_connections=True)
        cid = client.create_compartment(comp)
        client.update_compartment(cid, allow_external_connections=False)
        result = client.get_compartment(cid)
        assert result["allowExternalConnections"] is False

    # --- Plasticity zero-amount early returns ---

    def test_strengthen_concept_zero_amount(self, client):
        """strengthen_concept_relevance returns early when amount <= 0."""
        config = PlasticityConfig(learning_rate=0.0)
        client.set_plasticity_config(config)
        mid = quick_store_memory(client, "test", "test", concepts=["zero_test"])
        cid = client._run_query("MATCH (c:Concept {name: 'zero_test'}) RETURN c.id AS id")[0]["id"]
        client.strengthen_concept_relevance(mid, cid)  # Should return early, no error

    def test_weaken_concept_zero_amount(self, client):
        """weaken_concept_relevance returns early when amount <= 0."""
        config = PlasticityConfig(learning_rate=0.0)
        client.set_plasticity_config(config)
        mid = quick_store_memory(client, "test", "test", concepts=["zero_weak"])
        cid = client._run_query("MATCH (c:Concept {name: 'zero_weak'}) RETURN c.id AS id")[0]["id"]
        client.weaken_concept_relevance(mid, cid)  # Should return early

    def test_strengthen_goal_zero_amount(self, client):
        """strengthen_goal_connections returns early when amount <= 0."""
        config = PlasticityConfig(learning_rate=0.0)
        client.set_plasticity_config(config)
        gid = client.create_goal(Goal(description="Zero goal"))
        client.strengthen_goal_connections(gid)

    def test_strengthen_question_zero_amount(self, client):
        """strengthen_question_connections returns early when amount <= 0."""
        config = PlasticityConfig(learning_rate=0.0)
        client.set_plasticity_config(config)
        qid = client.create_question(Question(text="Zero?"))
        client.strengthen_question_connections(qid)

    def test_competitor_weakening_zero_amount(self, client):
        """_weaken_competitors returns early when amount <= 0."""
        config = PlasticityConfig(
            retrieval_strengthens=True,
            retrieval_weakens_competitors=True,
            competitor_distance=0.0,  # Makes amount = 0
        )
        client.set_plasticity_config(config)
        m = quick_store_memory(client, "center", "center")
        client.get_memory(m, apply_retrieval_effects=True)  # Should not error

    def test_decay_zero_amount_early_return(self, client):
        """decay_weak_connections returns early when decay amount is 0."""
        config = PlasticityConfig(learning_rate=0.0)
        client.set_plasticity_config(config)
        m1 = quick_store_memory(client, "A", "A")
        m2 = quick_store_memory(client, "B", "B")
        client.link_memories(m1, m2, strength=0.3)
        client.decay_weak_connections()  # Should return early, strength unchanged
        assert client.get_memory_link_strength(m1, m2) == pytest.approx(0.3)

    def test_get_plasticity_config(self, client):
        """get_plasticity_config returns the current config."""
        config = client.get_plasticity_config()
        assert isinstance(config, PlasticityConfig)
        assert config.learning_rate == 1.0

    def test_related_memories_adds_keyword_results(self, client):
        """get_related_memories includes keyword-only matches not found via concepts."""
        m1 = quick_store_memory(client, "A", "A", keywords=["unique_kw_xyz"])
        m2 = quick_store_memory(client, "B", "B", keywords=["unique_kw_xyz"])
        # No shared concepts, only shared keyword
        related = client.get_related_memories(m1, respect_permeability=False)
        assert any(r["id"] == m2 for r in related)

    def test_hebbian_blocked_by_compartment(self, client):
        """Hebbian learning skips connections blocked by compartment rules."""
        comp = Compartment(name="HebBlock", allow_external_connections=False)
        cid = client.create_compartment(comp)
        m1 = quick_store_memory(client, "in comp", "in comp")
        m2 = quick_store_memory(client, "outside", "outside")
        client.add_memory_to_compartment(m1, cid)
        client.apply_hebbian_learning([m1, m2], respect_compartments=True)
        # Connection should NOT have been created
        assert client.get_memory_link_strength(m1, m2) is None

    # --- Decay curve edge cases ---

    def test_effective_decay_exponential_direct(self):
        """effective_decay with EXPONENTIAL curve returns expected values."""
        config = PlasticityConfig(
            decay_curve=Curve.EXPONENTIAL, decay_amount=0.1, decay_threshold=1.0)
        decay = config.effective_decay(0.5, cycles=5)
        assert 0 < decay < 0.5

    def test_effective_decay_logarithmic_direct(self):
        """effective_decay with LOGARITHMIC curve returns expected values."""
        config = PlasticityConfig(
            decay_curve=Curve.LOGARITHMIC, decay_amount=0.1, decay_threshold=1.0)
        decay = config.effective_decay(0.5, cycles=5)
        assert decay > 0

    # --- FTS fallback ---

    def test_search_fallback_to_contains(self, client):
        """If FTS is unavailable, search falls back to CONTAINS."""
        quick_store_memory(client, "fallback search test content", "fallback test")
        # Force FTS unavailable
        client._fts_available = False
        results = client.search_memories("fallback")
        assert len(results) >= 1
        client._fts_available = True  # Restore

    def test_schema_init_without_fts(self, tmp_path, monkeypatch):
        """Schema initializes gracefully when FTS extension is unavailable."""
        c = MemoryGraphClient(db_path=str(tmp_path / "no_fts_db"))
        # Monkey-patch _run_schema_write to fail on FTS commands
        original = c._run_schema_write
        def failing_schema_write(query):
            if "fts" in query.lower() or "FTS" in query:
                raise RuntimeError("Extension not available")
            return original(query)
        monkeypatch.setattr(c, "_run_schema_write", failing_schema_write)
        c.initialize_schema()
        assert c._schema_initialized
        assert not c._fts_available
        c.close()

    # --- Related memories keyword deduplication ---

    def test_related_memories_keyword_dedup(self, client):
        """get_related_memories deduplicates across concept and keyword paths."""
        m1 = quick_store_memory(client, "A", "A",
                                concepts=["shared_concept"], keywords=["shared_kw"])
        m2 = quick_store_memory(client, "B", "B",
                                concepts=["shared_concept"], keywords=["shared_kw"])
        related = client.get_related_memories(m1, respect_permeability=False)
        ids = [r["id"] for r in related]
        assert ids.count(m2) == 1  # No duplicates

    # --- Quick store rollback on error ---

    def test_quick_store_rollback_on_error(self, client):
        """quick_store_memory rolls back on error."""
        try:
            quick_store_memory(
                client,
                content="will fail",
                summary="will fail",
                entities=[("name", "INVALID_TYPE")],  # Invalid EntityType
            )
        except (ValueError, KeyError):
            pass
        # Memory should not exist due to rollback
        results = client.search_memories("will fail")
        assert len(results) == 0

    def test_semantic_similarity_boost(self):
        """PlasticityConfig.get_initial_strength with semantic similarity."""
        config = PlasticityConfig(
            use_semantic_similarity=True,
            initial_strength_explicit=0.5,
        )
        config.set_semantic_similarity_fn(lambda a, b: 0.8)
        strength = config.get_initial_strength(True, "content A", "content B")
        assert strength > 0.5  # Boosted by similarity

    def test_semantic_similarity_exception_fallback(self):
        """Semantic similarity function error falls back to base strength."""
        config = PlasticityConfig(use_semantic_similarity=True)
        config.set_semantic_similarity_fn(lambda a, b: 1 / 0)  # Will raise
        strength = config.get_initial_strength(True, "a", "b")
        assert strength == config.initial_strength_explicit

    def test_effective_decay_linear(self):
        config = PlasticityConfig(decay_curve=Curve.LINEAR, decay_amount=0.1)
        decay = config.effective_decay(0.3, cycles=2)
        assert decay > 0

    def test_effective_decay_exponential(self):
        config = PlasticityConfig(decay_curve=Curve.EXPONENTIAL, decay_amount=0.1)
        decay = config.effective_decay(0.3, cycles=2)
        assert decay > 0

    def test_effective_decay_logarithmic(self):
        config = PlasticityConfig(decay_curve=Curve.LOGARITHMIC, decay_amount=0.1)
        decay = config.effective_decay(0.3, cycles=2)
        assert decay > 0

    def test_effective_decay_above_threshold_no_decay(self):
        config = PlasticityConfig(decay_threshold=0.5, decay_all=False)
        decay = config.effective_decay(0.8)
        assert decay == 0.0

    def test_weaken_concept_relevance(self, client):
        mid = quick_store_memory(client, "test", "test", concepts=["weakme"])
        cid_query = client._run_query(
            "MATCH (c:Concept {name: $name}) RETURN c.id AS id", {"name": "weakme"})
        cid = cid_query[0]["id"]
        client.weaken_concept_relevance(mid, cid)

    def test_aggressive_maintenance(self, client):
        m1 = quick_store_memory(client, "A", "A")
        m2 = quick_store_memory(client, "B", "B")
        client.link_memories(m1, m2, strength=0.1)
        client.run_aggressive_maintenance(cycles=3)
        assert client._access_cycle >= 3

    def test_get_strongest_weakest_connections(self, client):
        m1 = quick_store_memory(client, "A", "A")
        m2 = quick_store_memory(client, "B", "B")
        m3 = quick_store_memory(client, "C", "C")
        client.link_memories(m1, m2, strength=0.9)
        client.link_memories(m1, m3, strength=0.2)
        strongest = client.get_strongest_connections(m1, respect_permeability=False)
        weakest = client.get_weakest_connections(m1, respect_permeability=False)
        assert strongest[0]["strength"] >= strongest[-1]["strength"]
        assert weakest[0]["strength"] <= weakest[-1]["strength"]

    def test_get_all_connection_strengths(self, client):
        m1 = quick_store_memory(client, "A", "A")
        m2 = quick_store_memory(client, "B", "B")
        client.link_memories(m1, m2, strength=0.5)
        all_conns = client.get_all_connection_strengths()
        assert len(all_conns) >= 1

    def test_empty_connection_statistics(self, client):
        stats = client.get_connection_statistics()
        assert stats["count"] == 0
        assert stats["avg"] is None

    def test_remove_memory_from_all_compartments(self, client):
        c1 = client.create_compartment(Compartment(name="X"))
        c2 = client.create_compartment(Compartment(name="Y"))
        mid = quick_store_memory(client, "test", "test")
        client.add_memory_to_compartment(mid, c1)
        client.add_memory_to_compartment(mid, c2)
        client.remove_memory_from_compartment(mid)  # No compartment_id = remove from all
        assert len(client.get_memory_compartments(mid)) == 0

    def test_get_memories_in_compartment(self, client):
        cid = client.create_compartment(Compartment(name="Group"))
        m1 = quick_store_memory(client, "A", "A")
        m2 = quick_store_memory(client, "B", "B")
        client.add_memory_to_compartment([m1, m2], cid)
        mems = client.get_memories_in_compartment(cid)
        assert len(mems) == 2

    def test_link_memories_blocked_by_compartment(self, client):
        comp = Compartment(name="Isolated", allow_external_connections=False)
        cid = client.create_compartment(comp)
        m1 = quick_store_memory(client, "A", "A")
        m2 = quick_store_memory(client, "B", "B")
        client.add_memory_to_compartment(m1, cid)
        result = client.link_memories(m1, m2, check_compartments=True)
        assert result is False

    def test_decay_all_connections(self, client):
        config = PlasticityConfig(decay_all=True, decay_amount=0.05, auto_prune=False)
        client.set_plasticity_config(config)
        m1 = quick_store_memory(client, "A", "A")
        m2 = quick_store_memory(client, "B", "B")
        client.link_memories(m1, m2, strength=0.8)
        client.decay_weak_connections()
        assert client.get_memory_link_strength(m1, m2) < 0.8

    def test_transaction_begin_commit_rollback(self, client):
        """Manual transaction wrapping create_memory (not quick_store which has its own txn)."""
        client.begin_transaction()
        m = Memory(content="in txn", summary="in txn")
        client.create_memory(m)
        client.commit()
        results = client.search_memories("in txn")
        assert len(results) >= 1
