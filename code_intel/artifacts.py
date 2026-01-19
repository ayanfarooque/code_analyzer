"""code_intel.artifacts

Clean-room artifact generation for AI-assisted code understanding.

This module converts the in-memory CodeGraph into a set of AI-ready artifacts:
- domain_overview.md
- entity_map.json
- call_graph.json (+ optional call_graph.gexf if networkx installed)
- dependency_report.md
- business_rules.json (+ optional business_rules.md)
- ai_context.json

All logic here is original and based on best-effort static analysis heuristics.
"""

from __future__ import annotations

import ast
import json
import os
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from code_intel.graph import CodeGraph
from code_intel.relations import REL_CALLS, REL_DEFINES, REL_IMPORTS, REL_INHERITS, Relationship


def _safe_read_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            return ""


def _first_module_docstring(source: str) -> str:
    try:
        tree = ast.parse(source)
        ds = ast.get_docstring(tree)
        return (ds or "").strip()
    except Exception:
        return ""


def _shorten(text: str, max_len: int = 240) -> str:
    text = (text or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def _group_by_file(graph: CodeGraph) -> Dict[str, List[Dict[str, Any]]]:
    by_file: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for ent in graph.nodes.values():
        by_file[ent.file_path].append(ent.to_dict())
    for fp in by_file:
        by_file[fp].sort(key=lambda e: (e.get("type", ""), e.get("name", ""), e.get("line_number", 0)))
    return dict(by_file)


def _calls_adjacency(graph: CodeGraph) -> Dict[str, List[str]]:
    adj: Dict[str, List[str]] = defaultdict(list)
    for edge in graph.edges:
        if edge.type == REL_CALLS:
            adj[edge.source_id].append(edge.target_id)
    # de-dup with stable-ish ordering
    return {k: sorted(set(v)) for k, v in adj.items()}


def _imports_adjacency(graph: CodeGraph) -> Dict[str, List[str]]:
    adj: Dict[str, List[str]] = defaultdict(list)
    for edge in graph.edges:
        if edge.type == REL_IMPORTS and edge.target_id:
            adj[edge.source_id].append(edge.target_id)
    return {k: sorted(set(v)) for k, v in adj.items()}


def _most_called(graph: CodeGraph, limit: int = 25) -> List[Tuple[str, int]]:
    counts: Counter[str] = Counter()
    for edge in graph.edges:
        if edge.type == REL_CALLS:
            counts[edge.target_id] += 1
    return counts.most_common(limit)


def _top_orchestrators(graph: CodeGraph, limit: int = 25) -> List[Tuple[str, int]]:
    counts: Counter[str] = Counter()
    for edge in graph.edges:
        if edge.type == REL_CALLS:
            counts[edge.source_id] += 1
    return counts.most_common(limit)


def _coupling_by_module(graph: CodeGraph, limit: int = 25) -> List[Tuple[str, int]]:
    counts: Counter[str] = Counter()
    for edge in graph.edges:
        if edge.type == REL_IMPORTS and edge.target_id:
            counts[edge.source_id] += 1
    return counts.most_common(limit)


def _entrypoints(graph: CodeGraph) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    for ent in graph.nodes.values():
        if ent.type in {"function", "method"}:
            name = (ent.name or "").lower()
            if name in {"main", "run", "cli", "app"} or name.startswith("main_"):
                candidates.append(ent.to_dict())
    candidates.sort(key=lambda e: (e.get("file_path", ""), e.get("line_number", 0), e.get("name", "")))
    return candidates


@dataclass
class BusinessRuleCandidate:
    id: str
    title: str
    file_path: str
    line_number: int
    evidence: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "evidence": self.evidence,
        }


def _extract_business_rules_from_source(file_path: str, module_id: str) -> List[BusinessRuleCandidate]:
    source = _safe_read_text(file_path)
    if not source:
        return []

    rules: List[BusinessRuleCandidate] = []
    try:
        tree = ast.parse(source, filename=file_path)
    except Exception:
        return []

    keywords = (
        "must",
        "should",
        "shall",
        "rule",
        "validate",
        "validation",
        "policy",
        "require",
        "required",
        "forbid",
        "forbidden",
        "ensure",
        "guarantee",
        "only if",
        "unless",
    )

    def add_rule(node: ast.AST, title: str, evidence: str) -> None:
        lineno = getattr(node, "lineno", 0) or 0
        rid = f"{module_id}:{lineno}:{title}".replace(" ", "_")
        rules.append(
            BusinessRuleCandidate(
                id=rid,
                title=title,
                file_path=file_path,
                line_number=lineno,
                evidence=_shorten(evidence, 320),
            )
        )

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            ds = ast.get_docstring(node) or ""
            ds_l = ds.lower()
            if any(k in ds_l for k in keywords):
                title = f"Docstring rule in {getattr(node, 'name', 'module')}"
                add_rule(node, title, ds)

        if isinstance(node, ast.Raise):
            # Common pattern: raise ValueError("...") or raise Exception("...")
            try:
                evidence = ast.get_source_segment(source, node) or "raise …"
            except Exception:
                evidence = "raise …"
            title = "Exception-based validation"
            add_rule(node, title, evidence)

        if isinstance(node, ast.Assert):
            try:
                evidence = ast.get_source_segment(source, node) or "assert …"
            except Exception:
                evidence = "assert …"
            title = "Assertion-based invariant"
            add_rule(node, title, evidence)

    # De-dup by (file,line,title)
    uniq: Dict[Tuple[str, int, str], BusinessRuleCandidate] = {}
    for r in rules:
        uniq[(r.file_path, r.line_number, r.title)] = r
    return sorted(uniq.values(), key=lambda r: (r.file_path, r.line_number, r.title))


class ArtifactWriter:
    def __init__(self, graph: CodeGraph, source_root: str):
        self.graph = graph
        self.source_root = os.path.abspath(source_root)

    def write_all(self, output_dir: str) -> None:
        os.makedirs(output_dir, exist_ok=True)

        self._write_domain_overview(os.path.join(output_dir, "domain_overview.md"))
        self._write_entity_map(os.path.join(output_dir, "entity_map.json"))
        self._write_call_graph(output_dir)
        self._write_dependency_report(os.path.join(output_dir, "dependency_report.md"))
        self._write_business_rules(output_dir)
        self._write_ai_context(os.path.join(output_dir, "ai_context.json"))

    def _write_domain_overview(self, path: str) -> None:
        by_file = _group_by_file(self.graph)

        lines: List[str] = ["# Domain Overview", ""]
        lines.append(f"- Source root: {self.source_root}")
        lines.append(f"- Modules analyzed: {len({e.id for e in self.graph.nodes.values() if e.type == 'module'})}")
        lines.append(f"- Total entities: {len(self.graph.nodes)}")
        lines.append("")

        # Summarize modules by file
        for file_path in sorted(by_file.keys()):
            rel = os.path.relpath(file_path, self.source_root)
            source = _safe_read_text(file_path)
            doc = _first_module_docstring(source)

            entities = by_file[file_path]
            counts = Counter(e["type"] for e in entities)

            lines.append(f"## {rel}")
            if doc:
                lines.append(_shorten(doc, 400))
            lines.append("")
            lines.append("- Entities: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))

            # Very small heuristic about responsibility
            filename = os.path.basename(file_path).lower()
            if any(tok in filename for tok in ["util", "helper"]):
                lines.append("- Likely role: utilities/helpers")
            elif any(tok in filename for tok in ["model", "entity", "schema"]):
                lines.append("- Likely role: domain models")
            elif any(tok in filename for tok in ["service", "client", "api"]):
                lines.append("- Likely role: service/integration")
            elif any(tok in filename for tok in ["main", "app", "cli", "run"]):
                lines.append("- Likely role: entrypoint")

            lines.append("")

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _write_entity_map(self, path: str) -> None:
        by_file = _group_by_file(self.graph)

        # Build class -> methods map from DEFINES edges
        class_methods: Dict[str, List[str]] = defaultdict(list)
        for edge in self.graph.edges:
            if edge.type == REL_DEFINES:
                class_methods[edge.source_id].append(edge.target_id)
        class_methods = {k: sorted(set(v)) for k, v in class_methods.items()}

        entity_map = {
            "source_root": self.source_root,
            "by_file": by_file,
            "class_methods": class_methods,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entity_map, f, indent=2)

    def _write_call_graph(self, output_dir: str) -> None:
        call_graph = {
            "source_root": self.source_root,
            "edges": [e.to_dict() for e in self.graph.edges if e.type == REL_CALLS],
            "adjacency": _calls_adjacency(self.graph),
        }
        with open(os.path.join(output_dir, "call_graph.json"), "w", encoding="utf-8") as f:
            json.dump(call_graph, f, indent=2)

        # Optional GEXF export (nice for Gephi)
        try:
            import networkx as nx  # type: ignore

            g = nx.DiGraph()
            for ent in self.graph.nodes.values():
                g.add_node(ent.id, **{"type": ent.type, "name": ent.name, "file": ent.file_path})
            for edge in self.graph.edges:
                if edge.type == REL_CALLS:
                    g.add_edge(edge.source_id, edge.target_id, **{"type": edge.type})
            nx.write_gexf(g, os.path.join(output_dir, "call_graph.gexf"))
        except Exception:
            # If networkx is missing or export fails, keep JSON only.
            pass

    def _write_dependency_report(self, path: str) -> None:
        imports_adj = _imports_adjacency(self.graph)

        # fan-out and fan-in
        fan_out = {m: len(deps) for m, deps in imports_adj.items()}
        fan_in: Counter[str] = Counter()
        for src, deps in imports_adj.items():
            for dep in deps:
                fan_in[dep] += 1

        lines: List[str] = ["# Dependency Report", ""]
        lines.append(f"- Source root: {self.source_root}")
        lines.append("")

        lines.append("## Top Fan-out (modules importing many others)")
        for mod, count in sorted(fan_out.items(), key=lambda kv: kv[1], reverse=True)[:20]:
            lines.append(f"- {mod}: {count}")
        lines.append("")

        lines.append("## Top Fan-in (modules imported by many others)")
        for mod, count in fan_in.most_common(20):
            lines.append(f"- {mod}: {count}")
        lines.append("")

        lines.append("## Adjacency (imports)")
        for mod in sorted(imports_adj.keys()):
            deps = imports_adj[mod]
            if not deps:
                continue
            lines.append(f"- {mod} -> {', '.join(deps[:12])}{'…' if len(deps) > 12 else ''}")

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _write_business_rules(self, output_dir: str) -> None:
        # Best-effort: scan module files we saw
        module_entities = [e for e in self.graph.nodes.values() if e.type == "module"]
        candidates: List[BusinessRuleCandidate] = []
        for mod in module_entities:
            candidates.extend(_extract_business_rules_from_source(mod.file_path, mod.id))

        payload = {
            "source_root": self.source_root,
            "count": len(candidates),
            "candidates": [c.to_dict() for c in candidates],
        }
        with open(os.path.join(output_dir, "business_rules.json"), "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        # Also write a readable markdown
        lines: List[str] = ["# Business Rules (Heuristic)", ""]
        lines.append("This file is generated via static heuristics (docstrings, raises, asserts).")
        lines.append("")
        for c in candidates[:200]:
            rel = os.path.relpath(c.file_path, self.source_root)
            lines.append(f"- {c.title} ({rel}:{c.line_number})")
            lines.append(f"  - {c.evidence}")
        with open(os.path.join(output_dir, "business_rules.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _write_ai_context(self, path: str) -> None:
        context: Dict[str, Any] = {
            "source_root": self.source_root,
            "stats": {
                "total_nodes": len(self.graph.nodes),
                "total_edges": len(self.graph.edges),
            },
            "hotspots": {
                "most_called": _most_called(self.graph, 25),
                "top_orchestrators": _top_orchestrators(self.graph, 25),
                "highest_coupling_modules": _coupling_by_module(self.graph, 25),
            },
            "entrypoints": _entrypoints(self.graph),
            "imports": _imports_adjacency(self.graph),
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(context, f, indent=2)
