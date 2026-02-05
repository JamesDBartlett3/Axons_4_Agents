// Memory Graph Schema Initialization
// Run this script to set up indexes and constraints for the memory system

// ============================================================================
// INDEXES FOR FAST LOOKUPS
// ============================================================================

// Core nodes - indexed by primary identifiers
CREATE INDEX ON :Memory(id);
CREATE INDEX ON :Memory(created);
CREATE INDEX ON :Memory(lastAccessed);
CREATE INDEX ON :Concept(id);
CREATE INDEX ON :Concept(name);
CREATE INDEX ON :Keyword(id);
CREATE INDEX ON :Keyword(term);
CREATE INDEX ON :Topic(id);
CREATE INDEX ON :Topic(name);

// Entity nodes
CREATE INDEX ON :Entity(id);
CREATE INDEX ON :Entity(name);
CREATE INDEX ON :Entity(type);
CREATE INDEX ON :Source(id);
CREATE INDEX ON :Source(type);
CREATE INDEX ON :Source(reference);

// Intentional nodes
CREATE INDEX ON :Decision(id);
CREATE INDEX ON :Decision(date);
CREATE INDEX ON :Goal(id);
CREATE INDEX ON :Goal(status);
CREATE INDEX ON :Question(id);
CREATE INDEX ON :Question(status);

// Contextual nodes
CREATE INDEX ON :Context(id);
CREATE INDEX ON :Context(name);
CREATE INDEX ON :Context(status);
CREATE INDEX ON :Preference(id);
CREATE INDEX ON :Preference(category);
CREATE INDEX ON :TemporalMarker(id);
CREATE INDEX ON :TemporalMarker(type);

// Meta nodes
CREATE INDEX ON :Contradiction(id);
CREATE INDEX ON :Contradiction(status);

// ============================================================================
// TEXT SEARCH INDEXES (for content search)
// ============================================================================

CREATE TEXT INDEX ON :Memory(content);
CREATE TEXT INDEX ON :Memory(summary);
CREATE TEXT INDEX ON :Concept(description);
CREATE TEXT INDEX ON :Entity(description);
CREATE TEXT INDEX ON :Decision(description);
CREATE TEXT INDEX ON :Decision(rationale);
CREATE TEXT INDEX ON :Goal(description);
CREATE TEXT INDEX ON :Question(text);
