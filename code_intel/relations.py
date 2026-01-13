"""
relations.py

Defines the data models for relationships between entities (edges in the graph).
"""

from dataclasses import dataclass
from typing import Dict, Any

# Relationship Types
REL_CALLS = "CALLS"       # Function A calls Function B
REL_DEFINES = "DEFINES"   # Class A defines Method B
REL_INHERITS = "INHERITS" # Class A inherits from Class B
REL_IMPORTS = "IMPORTS"   # File A imports Module B

@dataclass
class Relationship:
    """
    Represents a directed relationship between two entities.
    
    Attributes:
        source_id (str): The ID of the source entity.
        target_id (str): The ID of the target entity.
        type (str): The type of relationship (e.g., CALLS, INHERITS).
    """
    source_id: str
    target_id: str
    type: str

    def to_dict(self) -> Dict[str, Any]:
        """Returns a dictionary representation of the relationship."""
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "type": self.type
        }
