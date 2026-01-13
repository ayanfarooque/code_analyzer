"""
report.py

Computes insights and analytics from the CodeGraph.
Generates the summary report.
"""

from typing import List, Tuple, Dict
from collections import Counter, defaultdict
from code_intel.graph import CodeGraph
from code_intel.relations import REL_CALLS, REL_DEFINES, REL_IMPORTS

class CodeReporter:
    def __init__(self, graph: CodeGraph):
        self.graph = graph

    def get_most_called_functions(self, limit: int = 10) -> List[Tuple[str, int]]:
        """
        Returns functions sorted by in-degree of CALLS relationships.
        Function ID -> Count
        """
        counts = Counter()
        for edge in self.graph.edges:
            if edge.type == REL_CALLS:
                counts[edge.target_id] += 1
        
        # We might want to filter only for entities that are actually Functions in our graph
        # to avoid noise from external libraries if they were added as loose nodes or not added.
        # But looking at scanner, we only add entities we scan. 
        # However, relationship scanner might add calls to external libs if we resolved them roughly (though we tried to avoid it).
        
        # Let's filter to ensure we show our own functions primarily if possible.
        # The scanner only adds relationships to entities if they are resolved.
        return counts.most_common(limit)

    def get_top_orchestrators(self, limit: int = 10) -> List[Tuple[str, int]]:
        """
        Returns functions that call the most OTHER functions (out-degree of CALLS).
        """
        counts = Counter()
        for edge in self.graph.edges:
            if edge.type == REL_CALLS:
                counts[edge.source_id] += 1
        return counts.most_common(limit)

    def get_largest_classes(self, limit: int = 10) -> List[Tuple[str, int]]:
        """
        Returns classes sorted by number of methods they DEFINE.
        """
        counts = Counter()
        for edge in self.graph.edges:
            if edge.type == REL_DEFINES:
                counts[edge.source_id] += 1
        return counts.most_common(limit)

    def get_highest_coupling_files(self, limit: int = 10) -> List[Tuple[str, int]]:
        """
        Returns files (modules) with highest coupling.
        Metric: Outgoing imports + Incoming imports? 
        Or just number of other modules it imports (Fan-out).
        Let's do Fan-out (Dependency count) for now as "Coupling".
        Relationship is Module -> IMPORTS -> Module
        """
        counts = Counter()
        for edge in self.graph.edges:
            if edge.type == REL_IMPORTS:
                counts[edge.source_id] += 1
        return counts.most_common(limit)

    def generate_markdown(self) -> str:
        """Generates the full markdown summary."""
        lines = ["# Code Intelligence Report", ""]
        
        lines.append("## High Level Stats")
        lines.append(f"- Total Nodes: {len(self.graph.nodes)}")
        lines.append(f"- Total Edges: {len(self.graph.edges)}")
        lines.append("")

        lines.append("## Top 10 Most Called Functions")
        for fn, count in self.get_most_called_functions():
             lines.append(f"- `{fn}`: {count} calls")
        lines.append("")

        lines.append("## Top 10 Orchestrators (Functions calling others)")
        for fn, count in self.get_top_orchestrators():
             lines.append(f"- `{fn}`: {count} outgoing calls")
        lines.append("")
        
        lines.append("## Largest Classes (by Method count)")
        for cls, count in self.get_largest_classes():
             lines.append(f"- `{cls}`: {count} methods")
        lines.append("")

        lines.append("## Highest Coupling (Modules with most imports)")
        for mod, count in self.get_highest_coupling_files():
             lines.append(f"- `{mod}`: {count} imports")
        lines.append("")

        return "\n".join(lines)