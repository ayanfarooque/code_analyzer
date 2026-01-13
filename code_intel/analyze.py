"""
analyze.py

CLI entry point for the Code Intelligence Engine.
Usage: python analyze.py <source_path> --output <output_folder>
"""

import argparse
import os
import json
import time
from code_intel.scanner import ProjectScanner
from code_intel.graph import CodeGraph
from code_intel.report import CodeReporter

def main():
    parser = argparse.ArgumentParser(description="Code Intelligence Engine")
    parser.add_argument("path", help="Path to the Python codebase to analyze")
    parser.add_argument("--output", help="Folder to write output files to", required=True)
    
    args = parser.parse_args()
    
    source_path = args.path
    if not os.path.exists(source_path):
        print(f"Error: Source path '{source_path}' does not exist.")
        return

    output_dir = args.output
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"Starting analysis on: {source_path}")
    start_time = time.time()

    # 1. Initialize Graph
    graph = CodeGraph()

    # 2. Run Scanner
    scanner = ProjectScanner(source_path, graph)
    scanner.scan()

    scan_time = time.time()
    print(f"Scanning complete in {scan_time - start_time:.2f}s")
    print(f"Graph stats: {len(graph.nodes)} nodes, {len(graph.edges)} edges")

    # 3. Generate Report
    reporter = CodeReporter(graph)
    markdown_report = reporter.generate_markdown()

    # 4. Write Outputs
    print(f"Writing results to {output_dir}...")
    
    # entities.json
    entities_data = [e.to_dict() for e in graph.nodes.values()]
    with open(os.path.join(output_dir, "entities.json"), "w", encoding="utf-8") as f:
        json.dump(entities_data, f, indent=2)

    # relationships.json
    relations_data = [r.to_dict() for r in graph.edges]
    with open(os.path.join(output_dir, "relationships.json"), "w", encoding="utf-8") as f:
        json.dump(relations_data, f, indent=2)

    # summary.md
    with open(os.path.join(output_dir, "summary.md"), "w", encoding="utf-8") as f:
        f.write(markdown_report)

    # graph.json (Full Dump)
    with open(os.path.join(output_dir, "graph.json"), "w", encoding="utf-8") as f:
        json.dump(graph.to_json(), f, indent=2)

    print("Success!")

if __name__ == "__main__":
    main()