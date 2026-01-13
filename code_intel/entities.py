"""
entities.py

Defines the data models for code entities (nodes in the graph).
Each entity represents a code construct like a Function, Class, Method, or Module.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

@dataclass
class Entity:
    """
    Base class for all code entities.
    
    Attributes:
        id (str): Unique identifier for the entity (e.g., "module.submodule.ClassName").
        name (str): The simple name of the entity (e.g., "ClassName").
        type (str): The type of entity (function, class, method, module).
        file_path (str): Absolute path to the file containing this entity.
        line_number (int): The line number where definition starts.
        parent_id (Optional[str]): The ID of the parent entity (e.g., class or module).
    """
    id: str
    name: str
    type: str
    file_path: str
    line_number: int
    parent_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Returns a dictionary representation of the entity."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "parent_id": self.parent_id
        }

@dataclass
class ModuleEntity(Entity):
    """Represents a Python source file/module."""
    def __init__(self, id: str, name: str, file_path: str, line_number: int = 0, parent_id: Optional[str] = None):
        super().__init__(id, name, "module", file_path, line_number, parent_id)

@dataclass
class ClassEntity(Entity):
    """Represents a Class definition."""
    def __init__(self, id: str, name: str, file_path: str, line_number: int, parent_id: Optional[str] = None):
        super().__init__(id, name, "class", file_path, line_number, parent_id)

@dataclass
class FunctionEntity(Entity):
    """Represents a standalone Function definition."""
    def __init__(self, id: str, name: str, file_path: str, line_number: int, parent_id: Optional[str] = None):
        super().__init__(id, name, "function", file_path, line_number, parent_id)

@dataclass
class MethodEntity(Entity):
    """Represents a Method within a Class."""
    def __init__(self, id: str, name: str, file_path: str, line_number: int, parent_id: Optional[str] = None):
        super().__init__(id, name, "method", file_path, line_number, parent_id)