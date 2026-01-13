"""
scanner.py

This module handles the static analysis of the codebase.
It walks the directory structure, parses Python files into ASTs,
and uses visitors to extract Entities and Relationships.
"""

import ast
import os
from typing import List, Tuple, Dict, Optional, Set

from code_intel.entities import Entity, FunctionEntity, ClassEntity, MethodEntity, ModuleEntity
from code_intel.relations import Relationship, REL_CALLS, REL_DEFINES, REL_INHERITS, REL_IMPORTS
from code_intel.graph import CodeGraph

class DefinitionVisitor(ast.NodeVisitor):
    """
    Pass 1 Visitor: Extracts definitions of Classes, Functions, and Methods.
    Populates various Entity objects and adds them to the graph.
    """
    def __init__(self, graph: CodeGraph, file_path: str, module_id: str):
        self.graph = graph
        self.file_path = file_path
        self.module_id = module_id
        
        # Stack to track current scope/parent (e.g., [module_id, class_id])
        self.scope_stack: List[str] = [module_id]

    @property
    def current_parent(self) -> str:
        return self.scope_stack[-1]

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Handle function and method definitions."""
        # Determine if this is a method (inside a class) or top-level function
        # A simple heuristic: if parent is a class ID (not module), it's a method.
        # But we need to know the type of the parent. 
        # For this simplified model, we check if we are deeper than module level.
        # Ideally, we look up the parent entity in the graph, but it might not be fully added yet.
        # So we trust the stack.
        
        # Check if parent is a ClassEntity (by checking the graph or context)
        is_method = False
        parent_entity = self.graph.get_entity(self.current_parent)
        if parent_entity and parent_entity.type == 'class':
            is_method = True

        name = node.name
        # Create a unique ID. 
        # Strategy: parent_id.name
        # Note: This strategy fails for nested functions with same name in different scopes, 
        # but works for standard class/module structures.
        entity_id = f"{self.current_parent}.{name}"
        
        line = node.lineno
        
        if is_method:
            entity = MethodEntity(entity_id, name, self.file_path, line, self.current_parent)
            # Relationship: Class DEFINES Method
            rel = Relationship(self.current_parent, entity_id, REL_DEFINES)
            self.graph.add_relationship(rel)
        else:
            entity = FunctionEntity(entity_id, name, self.file_path, line, self.current_parent)

        self.graph.add_entity(entity)
        
        # Enter scope and continue visiting children (for nested functions/classes)
        self.scope_stack.append(entity_id)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Treat async functions same as regular functions."""
        self.visit_FunctionDef(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        """Handle class definitions."""
        name = node.name
        entity_id = f"{self.current_parent}.{name}"
        line = node.lineno
        
        entity = ClassEntity(entity_id, name, self.file_path, line, self.current_parent)
        self.graph.add_entity(entity)
        
        # Handle Inheritance (Base Classes)
        # Note: We can only statically determine base class names here.
        # Resolving "Base" to "module.Base" requires import resolution (Pass 2 logic typically, 
        # but we can store the name now and try to link later, or do it here).
        # We'll extract the text name of bases for now.
        for base in node.bases:
            # Simple case: Class name (Attribute access like module.Class is harder to resolve without imports)
            base_name = self._get_name_from_node(base)
            if base_name:
                # We record a simplified INHERITS relationship where target is just the name for now?
                # Or we wait for Pass 2 to resolve it?
                # Better: Wait for Pass 2 or just store raw names in graph and post-process.
                # For this exercise, we will try to emit a relationship if we can guess the ID, 
                # but "RelationshipVisitor" is better suited for linking things.
                # However, usually inheritance is part of definition.
                # We'll skip adding INHERITS edges here and do it in Pass 2 
                # or simplified: just check if base_name exists in current module.
                pass

        self.scope_stack.append(entity_id)
        self.generic_visit(node)
        self.scope_stack.pop()

    def _get_name_from_node(self, node) -> Optional[str]:
        """Helper to extract name from Name or Attribute nodes."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name_from_node(node.value)}.{node.attr}"
        return None

class RelationshipVisitor(ast.NodeVisitor):
    """
    Pass 2 Visitor: Extracts relationships (CALLS, INHERITS usage, IMPORTS).
    Why Pass 2? Because we need to know all definitions to resolve references.
    """
    def __init__(self, graph: CodeGraph, file_path: str, module_id: str, imports_map: Dict[str, str]):
        self.graph = graph
        self.module_id = module_id
        self.scope_stack: List[str] = [module_id]
        
        # Map of local_alias -> full_qualified_name (e.g. "np" -> "numpy", "MyClass" -> "other_mod.MyClass")
        # Included from imports_map passed in
        self.scope_imports = imports_map.copy()

    @property
    def current_context(self) -> str:
        return self.scope_stack[-1]

    def visit_FunctionDef(self, node: ast.FunctionDef):
        entity_id = f"{self.current_context}.{node.name}"
        self.scope_stack.append(entity_id)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.visit_FunctionDef(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        entity_id = f"{self.current_context}.{node.name}"
        
        # INHERITS relationships
        for base in node.bases:
            base_name = self._get_full_name(base)
            # Resolve against imports or local module
            resolved_id = self._resolve_id(base_name)
            if resolved_id:
                 self.graph.add_relationship(Relationship(entity_id, resolved_id, REL_INHERITS))
        
        self.scope_stack.append(entity_id)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_Call(self, node: ast.Call):
        """Handle function calls."""
        # Extract the name of the function being called
        func_name = self._get_full_name(node.func)
        if func_name:
            # Attempt to resolve the function to an Entity ID
            target_id = self._resolve_id(func_name)
            
            # Even if we can't fully resolve it (e.g. library function), 
            # we might want to track it if it's internal.
            # For now, only add if we think it's in our graph (or we can validly guess).
            if target_id and self.graph.get_entity(target_id):
                 self.graph.add_relationship(Relationship(self.current_context, target_id, REL_CALLS))
            elif target_id:
                # Even if not in graph (e.g. potential cross-module call we missed?), add strict checking?
                # We'll be lenient: if we resolved it to a likely ID, add it.
                pass
        
        self.generic_visit(node)

    def _get_full_name(self, node) -> Optional[str]:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            # Recursively get name (e.g. module.func)
            value_name = self._get_full_name(node.value)
            if value_name:
                return f"{value_name}.{node.attr}"
        return None

    def _resolve_id(self, name: str) -> Optional[str]:
        """
        Resolves a name (e.g. 'MyClass' or 'utils.helper') to a canonical Entity ID.
        Uses imports and simple heuristics.
        """
        if not name: return None

        # 1. Check if it's a direct import alias
        # e.g. from utils import helper (helper -> utils.helper)
        if name in self.scope_imports:
            return self.scope_imports[name]

        # 2. Check splits (e.g. 'os.path.join') - HARD without full type inference.
        # We assume standard project structure: 'module.function'.
        
        # 3. Check current module (local definition)
        # e.g. function defined in same file
        local_candidate = f"{self.module_id}.{name}"
        if self.graph.get_entity(local_candidate):
            return local_candidate
            
        # 4. Check global imports (e.g. import utils -> utils.helper)
        parts = name.split('.', 1)
        if len(parts) > 1:
            base, suffix = parts[0], parts[1]
            if base in self.scope_imports:
                # e.g. import utils; utils.helper -> utilsId.helper
                # But imports_map maps 'utils' -> 'utils_module_id' (or path)
                # This is tricky. Let's assume the import map stores the fully qualified module name.
                resolved_base = self.scope_imports[base]
                return f"{resolved_base}.{suffix}"
                
        return None

class ProjectScanner:
    """
    Orchestrates the scanning process.
    """
    def __init__(self, root_path: str, graph: CodeGraph):
        self.root_path = os.path.abspath(root_path)
        self.graph = graph

    def scan(self):
        """Runs the two-pass scan on the project."""
        python_files = self._find_files()
        
        # Pass 1: Definitions
        print(f"Scanning {len(python_files)} files for definitions...")
        for file_path in python_files:
            self._scan_definitions(file_path)
            
        # Pass 2: Relationships
        print(f"Scanning relationships...")
        for file_path in python_files:
            self._scan_relationships(file_path)

    def _find_files(self) -> List[str]:
        """Walks directory and returns list of .py files."""
        py_files = []
        for root, _, files in os.walk(self.root_path):
            for file in files:
                if file.endswith(".py"):
                    py_files.append(os.path.join(root, file))
        return py_files

    def _get_module_id(self, file_path: str) -> str:
        """Converts file path to dot-notation module ID relative to root."""
        rel_path = os.path.relpath(file_path, self.root_path)
        # Remove extension
        name_no_ext = os.path.splitext(rel_path)[0]
        # Replace separators
        module_id = name_no_ext.replace(os.sep, ".")
        return module_id

    def _scan_definitions(self, file_path: str):
        module_id = self._get_module_id(file_path)
        
        # Create Module Entity
        # We model the file itself as a node
        mod_entity = ModuleEntity(module_id, module_id.split('.')[-1], file_path)
        self.graph.add_entity(mod_entity)
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source, filename=file_path)
            
            visitor = DefinitionVisitor(self.graph, file_path, module_id)
            visitor.visit(tree)
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")

    def _scan_relationships(self, file_path: str):
        module_id = self._get_module_id(file_path)
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source, filename=file_path)
            
            # Pre-scan imports for this file to build resolution map
            imports_map = self._extract_imports(tree, module_id)
            
            visitor = RelationshipVisitor(self.graph, file_path, module_id, imports_map)
            visitor.visit(tree)
        except Exception as e:
             # Already logged in pass 1 usually
             pass

    def _extract_imports(self, tree: ast.AST, current_module_id: str) -> Dict[str, str]:
        """
        Extracts imports to build a symbol map for the file.
        Returns: { 'alias/name': 'fully.qualified.id' }
        """
        imports_map = {}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # import x as y
                    local_name = alias.asname if alias.asname else alias.name
                    # Map local name to full name
                    imports_map[local_name] = alias.name
                    
                    # Also add relationship: File IMPORTS Module
                    # (Simplified: logic assumes alias.name is the module ID, which is often true)
                    self.graph.add_relationship(Relationship(current_module_id, alias.name, REL_IMPORTS))

            elif isinstance(node, ast.ImportFrom):
                # from x import y
                module = node.module or ""
                # Resolve relative imports
                if node.level > 0:
                    # Handle . or ..
                    # This is complex to get perfect without full path logic, 
                    # but we can approximation:
                    parts = current_module_id.split('.')
                    # level 1 = ., level 2 = ..
                    # remove (level) parts from end
                    base_parts = parts[:-node.level] if (len(parts) >= node.level) else []
                    if module:
                        base = ".".join(base_parts + [module])
                    else:
                        base = ".".join(base_parts)
                    full_module_name = base
                else:
                    full_module_name = module

                for alias in node.names:
                    local_name = alias.asname if alias.asname else alias.name
                    # y resolves to x.y
                    full_target = f"{full_module_name}.{alias.name}"
                    imports_map[local_name] = full_target
                    
                    # We usually say the file imports the *module*, not the specific function in the relationship (often)
                    # But "code_intel" might want dependencies.
                    # We'll add dependency on the module `full_module_name`
                    self.graph.add_relationship(Relationship(current_module_id, full_module_name, REL_IMPORTS))
                    
        return imports_map