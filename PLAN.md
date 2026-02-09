# Axons_4_Agents — Implementation Plan

> Upgrades the project from a single-file prototype into a production-quality, installable Python
> package with bug fixes, performance improvements, full test coverage, and MCP server integration.
> Phases 1–4 harden the core; Phases 5–6 build the MCP server on a solid foundation.

---

## Phase 1 — Package Structure & Modularization

Split the 2,600-line monolith `src/memory_client.py` into a proper installable package.

### Steps

1. **Create package scaffolding:**
   - `axons/` top-level package with `__init__.py`
   - `pyproject.toml` (PEP 621) replacing `requirements.txt`, declaring `kuzu>=0.4.0` as
     dependency and `pytest` as optional test dependency
   - Keep `docs/` at project root (already there)

2. **Extract modules from `memory_client.py`:**
   - `axons/enums.py` — `MemoryType`, `ConnectionType`, `Permeability`, `ContextStatus`,
     `PlasticityCurve`, `StrengthBounds` (currently lines ~14–112)
   - `axons/models.py` — All 11 dataclasses: `Memory`, `Concept`, `Keyword`, `Topic`, `Entity`,
     `Source`, `Decision`, `Goal`, `Question`, `Context`, `Preference`, `TemporalMarker`,
     `Contradiction`, `Compartment` (currently lines ~114–310)
   - `axons/plasticity.py` — `PlasticityConfig` class with presets, curves, serialization
     (currently lines ~312–560)
   - `axons/permeability.py` — `can_data_flow()`, `can_form_connection()`,
     `_filter_by_permeability()`, permeability getters/setters
     (currently lines ~1350–1470 and ~2350–2380)
   - `axons/client.py` — `MemoryGraphClient` (schema init, CRUD, linking, queries, search,
     maintenance, directory export)
   - `axons/__init__.py` — Public API re-exports

3. **Use relative imports** within the package.

4. **Move tests:** `src/test_memory_system.py` → `tests/test_memory_system.py`; update imports.

5. **Fix `src/directory.md`:** Update to reflect new structure; fix the `K�zuDB` → `KùzuDB`
   encoding issue.

### Verification

- `pip install -e .` succeeds
- `from axons import MemoryGraphClient` works
- All existing tests pass with updated imports

---

## Phase 2 — Bug Fixes & Correctness

Fix the bugs and correctness issues discovered during code review.

### Steps

1. **Duplicate edge prevention** — Replace all 16 `CREATE` relationship queries with `MERGE`
   (or check-then-create if KùzuDB doesn't support `MERGE` for relationships).
   Affected methods:
   - `link_memory_to_concept`, `link_memory_to_keyword`, `link_memory_to_topic`,
     `link_memory_to_entity`, `link_memory_to_source`, `link_memory_to_context`,
     `link_memory_to_decision`, `link_memory_to_question`, `link_memory_to_goal`,
     `link_memory_to_preference`, `link_memory_to_temporal`
   - `link_memories`, `link_concepts`, `link_goals`, `link_decisions`, `link_contexts`,
     `mark_contradiction`

2. **`PlasticityConfig.to_dict()` serialization bug** — Exclude `_semantic_similarity_fn` from
   output. Add a filter: `if key.startswith('_'): continue`.

3. **Input validation** — Add bounds checking to all methods that accept numeric parameters:
   - `confidence`: clamp/raise on values outside `[0.0, 1.0]`
   - `strength`, `relevance`: clamp/raise on values outside `[0.0, 1.0]`
   - `Preference.strength`: enforce `[-1.0, 1.0]` range per `docs/schema.md`
   - Empty-string and `None` checks for required text fields (`content`, `name`, `term`)

4. **`close()` guard** — After closing, set `_closed = True`. Add a check at the top of public
   methods that raises `RuntimeError("Client is closed")` instead of `AttributeError`.

5. **Remove misleading `hops` parameter** — In `get_related_memories()`, either implement true
   variable-depth traversal via KùzuDB's recursive path syntax, or remove the parameter and
   document the single-hop behavior.

6. **Bidirectional Hebbian duplication** — In `apply_hebbian_learning()`, check if the reverse
   edge already exists before creating it. Or switch to undirected `RELATES_TO` semantics where
   only one edge is stored and queries match both directions.

7. **`_run_write()` error swallowing** — Narrow the `"already exists"` exception handling to only
   apply during schema initialization, not data writes. Split into `_run_schema_write()` and
   `_run_data_write()`.

### Verification

- New tests confirm duplicate edges are prevented
- Invalid inputs raise `ValueError`
- Closed client raises `RuntimeError`
- `to_dict()` / `from_dict()` round-trips without error

---

## Phase 3 — Performance & Scalability

Address N+1 queries, missing indexes, and batching issues.

### Steps

1. **Secondary indexes** — Add index creation to `initialize_schema()`:
   - `Concept.name`, `Keyword.term`, `Topic.name`, `Entity.name`
   - `Memory.memory_type`, `Memory.summary` (if KùzuDB supports text indexing)
   - `Compartment.name`

2. **Batch `_filter_by_permeability()`** — Replace the per-result `can_data_flow()` loop with a
   single Cypher query that returns permeability data for all candidate memories, then filter in
   Python. Reduces 4N+1 queries to ~2 queries.

3. **Batch `add_memory_to_compartment()`** — Accept a list of memory IDs and use a single query
   with `UNWIND` instead of per-ID check-then-create.

4. **Consolidate `get_all_nodes_summary()`** — Replace 14 separate count queries with a single
   query using `UNION ALL` or batch execution. Same for `get_node_counts()`. Ensure
   `export_directory_markdown()` calls only one of them.

5. **Full-text search** — Investigate KùzuDB's full-text search capabilities. If unavailable, add
   an in-memory inverted index (e.g., `whoosh` or a simple dict-based approach) for
   `search_memories()` to avoid `CONTAINS` scans.

6. **Connection pooling** — Create a small connection pool (configurable size) in
   `MemoryGraphClient.__init__()` for read concurrency. KùzuDB supports multiple read connections.

7. **Transaction wrapper for `quick_store_memory()`** — Wrap multi-step operations in KùzuDB
   transactions so partial failures roll back cleanly.

### Verification

- Profile query counts with a 1,000-memory dataset
- Verify permeability filtering uses ≤3 queries total
- Verify `search_memories` uses indexes
- `quick_store_memory` rolls back on mid-operation failure

---

## Phase 4 — Test Coverage & Framework Migration

Migrate to pytest and fill all coverage gaps.

### Steps

1. **Pytest migration** — Convert `test_memory_system.py`:
   - Replace manual `assert` + `print()` with pytest assertions
   - Replace `get_test_db_path()` global with `@pytest.fixture(scope="function")` using `tmp_path`
   - Replace `if __name__ == "__main__"` runner with pytest discovery
   - Add `tests/conftest.py` with shared fixtures (`memory_client`, `populated_client`)

2. **Node CRUD tests** — Cover all 14 node types:
   - `test_create_source`, `test_create_decision`, `test_create_context`,
     `test_create_preference`, `test_create_temporal_marker`, `test_create_contradiction`

3. **Relationship tests** — Cover all 19 relationship types:
   - `test_link_memory_to_source`, `test_link_memory_to_context`,
     `test_link_memory_to_decision`, `test_link_memory_to_preference`,
     `test_link_memory_to_temporal`
   - `test_link_concepts`, `test_link_goals`, `test_link_decisions`, `test_link_contexts`

4. **Query/search tests:**
   - `test_search_memories`, `test_get_memories_by_keyword`, `test_get_memories_by_topic`,
     `test_get_memories_by_entity`
   - `test_get_memory_retrieval_effects` (verify retrieval-induced modification)
   - `test_get_decision_chain`, `test_get_unresolved_contradictions`,
     `test_resolve_contradiction`, `test_get_preferences_by_category`

5. **Negative/edge case tests:**
   - Invalid UUIDs, empty strings, `None` values
   - Duplicate edge creation (verify idempotency after Phase 2 fixes)
   - Operations on closed client
   - Out-of-range numeric values

6. **Delete tests:** `test_delete_compartment`, `test_delete_all_data`

7. **Boundary tests:** `_weaken_competitors` doesn't modify unrelated graph regions.

8. **Serialization round-trip test:** `save_plasticity_config` / `load_plasticity_config`.

9. **CI config** — Add `[tool.pytest.ini_options]` section in `pyproject.toml`.

### Verification

- `pytest --cov` shows ≥90% line coverage on `axons/` package
- All 50+ tests pass in isolation (no ordering dependencies)

---

## Phase 5 — MCP Server (Core)

Build the MCP server as outlined in `TODO.md` Phases 1–5, on top of the now-hardened package.

### Steps

1. **Server skeleton** (`axons/mcp/server.py`) — Set up a FastMCP server with lifespan management
   that initializes a `MemoryGraphClient` on startup and closes it on shutdown. Add `fastmcp` to
   `pyproject.toml` dependencies.

2. **Memory tools** (TODO Phase 2) — Expose MCP tools:
   - `store_memory` (wraps `quick_store_memory`)
   - `recall_memory` (wraps `get_memory`)
   - `search_memories` (wraps `search_memories`)
   - `get_related` (wraps `get_related_memories`)

3. **Concept/association tools** (TODO Phase 3) — Expose:
   - `create_concept`, `link_concept`
   - `get_memories_by_concept`, `link_concepts`
   - `create_entity`, `create_keyword`, `create_topic` and their link operations

4. **Plasticity tools** (TODO Phase 4) — Expose:
   - `strengthen_connection`, `weaken_connection`
   - `run_maintenance`, `get_connection_stats`
   - `configure_plasticity` (with preset support)

5. **Compartmentalization tools** (TODO Phase 5) — Expose:
   - `create_compartment`, `add_to_compartment`
   - `set_active_compartment`, `set_permeability`
   - `check_data_flow`

6. **Input/output schemas** — Define Pydantic models for all tool inputs and outputs to get proper
   MCP schema generation.

7. **Error handling** — Map client exceptions to MCP error responses with clear messages.

### Verification

- MCP server starts without errors
- Agent can call all core tools end-to-end
- Integration test: create memory → recall it → search for it

---

## Phase 6 — MCP Server (Advanced) & Documentation

Complete `TODO.md` Phases 6–9 and update all documentation.

### Steps

1. **Resource endpoints** (TODO Phase 6) — Add MCP resources:
   - `memory://directory` — Returns the directory markdown
   - `memory://stats` — Returns node counts and connection statistics
   - `memory://config` — Returns current plasticity config

2. **Advanced tools** (TODO Phase 7) — Add:
   - `execute_cypher` with safety checking (whitelist read-only keywords, block
     `DELETE`/`DROP`/`DETACH` unless explicitly allowed)
   - `bulk_store` for batch memory creation
   - `export_subgraph` for extracting a connected subgraph

3. **Goal, Decision, Context, Contradiction tools** (TODO Phase 8) — Expose remaining node types:
   - CRUD and link operations for goals, decisions, contexts, questions, preferences,
     temporal markers, contradictions

4. **MCP server tests** (`tests/test_mcp_server.py`) — Test all tools/resources against a live
   server with test database.

5. **Documentation updates:**
   - Create `docs/mcp-server-guide.md` per TODO
   - Update `README.md` with installation instructions (`pip install -e .`)
   - Update `docs/usage-guide.md` to fix the `ContextStatus` import block
   - Reconcile `docs/schema.md` `Preference.strength` range description with code validation
   - Add `respect_permeability` parameter documentation to usage guide
   - Clarify in `docs/design-decisions.md` that `max_strength` is only enforced during
     plasticity operations, not direct `link_memories()` calls
   - Update `src/directory.md` to reflect new package structure

### Verification

- `execute_cypher` blocks destructive queries
- `bulk_store` handles 100+ memories
- All documentation builds without broken links or inconsistencies
- Full MCP test suite passes

---

## Key Decisions

| Decision                                 | Rationale                                                                                                |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Package name `axons`                     | Short, memorable, matches project name                                                                   |
| `MERGE` over check-then-create for edges | Cleaner, atomic, fewer round-trips (fall back to check-then-create if KùzuDB lacks relationship `MERGE`) |
| pytest over unittest                     | Better fixtures, parametrize, plugin ecosystem                                                           |
| Full package with `pyproject.toml`       | Enables `pip install`, proper versioning, future PyPI publishing                                         |
| MCP server after core fixes (Phases 5–6) | Building on a buggy foundation would compound problems                                                   |
| Split `_run_write` into schema vs. data  | Prevents silent swallowing of real data errors                                                           |
