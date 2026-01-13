"""
graph.py

Implements the central graph data structure that holds all entities and relationships.
Provides methods to add data and query the graph.
"""

from typing import Dict, List, Set, Optional
from code_intel.entities import Entity
from code_intel.relations import Relationship

class CodeGraph:
    """
    A unified in-memory graph model for the codebase.
    Nodes are Entities, Edges are Relationships.
    """
    def __init__(self):
        # Map entity ID -> Entity object
        self.nodes: Dict[str, Entity] = {}
        # List of all relationships
        self.edges: List[Relationship] = []
        
        # Adjacency lists for fast traversal
        # source_id -> list of Relationships where this node is source
        self.outgoing: Dict[str, List[Relationship]] = {}
        # target_id -> list of Relationships where this node is target
        self.incoming: Dict[str, List[Relationship]] = {}

    def add_entity(self, entity: Entity):
        """Adds an entity to the graph."""
        if entity.id in self.nodes:
            # In case of duplicates (e.g. same name in different conditional blocks),
            # we generally keep the first one or simply overwrite.
            # For static analysis, we'll overwrite to update with latest info if needed,
            # but usually IDs should be unique.
            pass
        self.nodes[entity.id] = entity

    def add_relationship(self, rel: Relationship):
        """Adds a relationship to the graph."""
        self.edges.append(rel)
        
        if rel.source_id not in self.outgoing:
            self.outgoing[rel.source_id] = []
        self.outgoing[rel.source_id].append(rel)
        
        if rel.target_id not in self.incoming:
            self.incoming[rel.target_id] = []
        self.incoming[rel.target_id].append(rel)

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Retrieves an entity by its ID."""
        return self.nodes.get(entity_id)

    def get_outgoing_edges(self, source_id: str) -> List[Relationship]:
        """Returns all relationships starting from the given source ID."""
        return self.outgoing.get(source_id, [])

    def get_incoming_edges(self, target_id: str) -> List[Relationship]:
        """Returns all relationships pointing to the given target ID."""
        return self.incoming.get(target_id, [])

    def to_json(self):
        """Serializes the entire graph structure to primitives."""
        return {
            "context": {
                "total_nodes": len(self.nodes),
                "total_edges": len(self.edges)
            },
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": [edge.to_dict() for edge in self.edges]
        }