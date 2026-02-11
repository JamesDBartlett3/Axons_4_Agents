"""Permeability checking and data flow control for compartmentalized memories.

Provides PermeabilityMixin, which is mixed into MemoryGraphClient to add
permeability-related methods. These methods depend on _run_query, _run_write,
and get_memory_compartments being available on self (provided by the client).
"""

from typing import Optional, List, Dict

from .enums import Permeability


class PermeabilityMixin:
    """Mixin providing permeability and data-flow methods for MemoryGraphClient."""

    def can_form_connection(self, memory_id_1: str, memory_id_2: str) -> bool:
        """Check if an organic connection can form between two memories.

        This checks compartment boundaries using strict fail-safe logic:
        - ALL compartments of BOTH memories must allow external connections
        - Exception: memories in the SAME single compartment (both only in that one)

        Fail-safe: Any single compartment that disallows external connections will block,
        even if the memories share another compartment.
        """
        comps1 = self.get_memory_compartments(memory_id_1)
        comps2 = self.get_memory_compartments(memory_id_2)

        # Both without compartment - allowed
        if not comps1 and not comps2:
            return True

        # Special case: both memories are in exactly the same set of compartments
        # (i.e., they're fully co-located, not just sharing one)
        ids1 = {c["id"] for c in comps1}
        ids2 = {c["id"] for c in comps2}
        if ids1 == ids2 and ids1:  # Same non-empty set of compartments
            return True

        # Fail-safe: ANY compartment that blocks external connections will block
        for comp in comps1:
            if not comp.get("allowExternalConnections", True):
                return False
        for comp in comps2:
            if not comp.get("allowExternalConnections", True):
                return False

        return True

    def can_data_flow(self, from_memory_id: str, to_memory_id: str,
                      connection_permeability: str = None) -> bool:
        """Check if data can flow from one memory to another.

        This implements multi-layer permeability checking with fail-safe logic:
        1. Source memory must allow OUTWARD flow
        2. ALL source compartments must allow OUTWARD flow
        3. ALL destination compartments must allow INWARD flow
        4. Destination memory must allow INWARD flow
        5. Connection must allow this direction (if provided)

        Fail-safe: ANY layer that blocks will block the entire data flow.
        This means if a memory is in multiple compartments, ALL of them must
        allow the flow direction.

        Args:
            from_memory_id: Memory where data originates
            to_memory_id: Memory requesting the data (query origin)
            connection_permeability: Permeability of the connection (if known)

        Returns:
            True if data can flow from source to destination
        """
        # Check source memory allows outward flow
        from_mem_perm = self.get_memory_permeability(from_memory_id)
        if from_mem_perm and not Permeability(from_mem_perm).allows_outward():
            return False

        # Check destination memory allows inward flow
        to_mem_perm = self.get_memory_permeability(to_memory_id)
        if to_mem_perm and not Permeability(to_mem_perm).allows_inward():
            return False

        # Get ALL compartments for both memories
        from_comps = self.get_memory_compartments(from_memory_id)
        to_comps = self.get_memory_compartments(to_memory_id)

        # Fail-safe: ALL source compartments must allow outward flow
        for comp in from_comps:
            perm = Permeability(comp.get("permeability", "open"))
            if not perm.allows_outward():
                return False

        # Fail-safe: ALL destination compartments must allow inward flow
        for comp in to_comps:
            perm = Permeability(comp.get("permeability", "open"))
            if not perm.allows_inward():
                return False

        # Check connection permeability (if provided)
        if connection_permeability:
            conn_perm = Permeability(connection_permeability)
            # Connection permeability is from perspective of the "owner" (first memory in link)
            # For data to flow from->to, we need the connection to allow that direction
            # This depends on which direction the connection was created
            # For simplicity, we treat OSMOTIC_INWARD as allowing flow toward the connection owner
            if not conn_perm.allows_inward():
                return False

        return True

    def set_connection_permeability(self, memory_id_1: str, memory_id_2: str,
                                    permeability: Permeability):
        """Set the permeability of a specific connection."""
        query = """
        MATCH (m1:Memory {id: $id1})-[r:RELATES_TO]->(m2:Memory {id: $id2})
        SET r.permeability = $perm
        """
        self._run_write(query, {"id1": memory_id_1, "id2": memory_id_2, "perm": permeability.value})

    def get_connection_permeability(self, memory_id_1: str, memory_id_2: str) -> Optional[str]:
        """Get the permeability of a specific connection."""
        query = """
        MATCH (m1:Memory {id: $id1})-[r:RELATES_TO]->(m2:Memory {id: $id2})
        RETURN r.permeability AS permeability
        """
        result = self._run_query(query, {"id1": memory_id_1, "id2": memory_id_2})
        return result[0]["permeability"] if result else None

    def get_memory_permeability(self, memory_id: str) -> Optional[str]:
        """Get the permeability of a specific memory."""
        query = """
        MATCH (m:Memory {id: $id})
        RETURN m.permeability AS permeability
        """
        result = self._run_query(query, {"id": memory_id})
        return result[0]["permeability"] if result else None

    def set_memory_permeability(self, memory_ids, permeability: Permeability):
        """Set the permeability of one or more memories.

        Args:
            memory_ids: Single memory ID (str) or list of memory IDs
            permeability: The new permeability setting
        """
        # Normalize to list
        if isinstance(memory_ids, str):
            memory_ids = [memory_ids]

        for memory_id in memory_ids:
            query = """
            MATCH (m:Memory {id: $id})
            SET m.permeability = $perm
            """
            self._run_write(query, {"id": memory_id, "perm": permeability.value})

    def _filter_by_permeability(self, requester_memory_id: str, results: List[Dict]) -> List[Dict]:
        """Filter query results based on permeability rules.

        Uses batched queries to fetch all permeability data at once instead of
        per-result queries. Data flows FROM each result TO the requester, so:
        - Source memory must allow OUTWARD flow
        - Source compartments must allow OUTWARD flow
        - Requester compartments must allow INWARD flow
        - Requester memory must allow INWARD flow
        """
        if not results:
            return results

        all_ids = [r["id"] for r in results] + [requester_memory_id]

        # Batch query 1: get permeability for all involved memories
        perm_query = """
        UNWIND $ids AS mid
        MATCH (m:Memory {id: mid})
        RETURN m.id AS id, m.permeability AS permeability
        """
        perm_rows = self._run_query(perm_query, {"ids": all_ids})
        mem_perms = {row["id"]: row["permeability"] for row in perm_rows}

        # Batch query 2: get compartments for all involved memories
        comp_query = """
        UNWIND $ids AS mid
        MATCH (m:Memory {id: mid})-[:IN_COMPARTMENT]->(c:Compartment)
        RETURN m.id AS mem_id, c.permeability AS permeability
        """
        comp_rows = self._run_query(comp_query, {"ids": all_ids})
        mem_comps: Dict[str, List[str]] = {}
        for row in comp_rows:
            mem_comps.setdefault(row["mem_id"], []).append(row["permeability"])

        # Check requester can receive data (inward flow)
        req_perm = mem_perms.get(requester_memory_id)
        if req_perm and not Permeability(req_perm).allows_inward():
            return []  # Requester blocks all inward flow

        req_comps = mem_comps.get(requester_memory_id, [])
        for cp in req_comps:
            if not Permeability(cp).allows_inward():
                return []  # A requester compartment blocks inward flow

        # Filter results: each source must allow outward flow
        filtered = []
        for r in results:
            rid = r["id"]

            # Check source memory allows outward
            src_perm = mem_perms.get(rid)
            if src_perm and not Permeability(src_perm).allows_outward():
                continue

            # Check all source compartments allow outward
            src_comps = mem_comps.get(rid, [])
            blocked = False
            for cp in src_comps:
                if not Permeability(cp).allows_outward():
                    blocked = True
                    break
            if blocked:
                continue

            filtered.append(r)

        return filtered
