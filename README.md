# Code Intelligence Engine

A powerful, modular static analysis tool for Python that transforms codebases into queryable graphs.

The **Code Intelligence Engine** goes beyond simple text search by parsing Python source code into Abstract Syntax Trees (AST). It extracts semantic entities (Functions, Classes, Methods) and maps their relationships (Calls, Inheritance, Imports) to provide deep architectural insights.

## Table of Contents
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Outputs](#outputs)

## Features

- **Deep Semantic Analysis**: Parses code to understand *what* it is, not just what it says.
- **Entity Extraction**: Automatically identifies and indexes:
  - Modules
  - Classes
  - Methods
  - Standalone Functions
- **Relationship Mapping**:
  - `CALLS`: Function-to-function invocation graphs.
  - `INHERITS`: Class inheritance hierarchies.
  - `DEFINES`: Class method definitions.
  - `IMPORTS`: Module-level dependencies.
- **Metric Reporting**: Generates insights on coupling, complexity, and usage frequency.
- **Zero Dependencies**: Built entirely with the Python Standard Library for maximum portability and ease of use.

## Installation

### Prerequisites
- Python 3.8 or higher.

### Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/ayanfarooque/code_analyzer.git
   cd code_analyzer
   ```
2. No external libraries are required (no `pip install` needed).

## Quick Start

To analyze a codebase, run the `analyze.py` script from the root directory.

**Syntax:**
```bash
python code_intel/analyze.py <path_to_source_code> --output <path_to_output_folder>
```

**Example:**
Run the tool on the included sample project:
```bash
python code_intel/analyze.py tests/sample_project --output results
```

## Architecture

The project follows a strict modular design:

| Module | Description |
|--------|-------------|
| **`analyze.py`** | The CLI entry point. Orchestrates the scanning, graph building, and reporting phases. |
| **`scanner.py`** | The analysis engine. Walks the directory tree and uses AST visitors to extract entities (Pass 1) and link relationships (Pass 2). |
| **`graph.py`** | The core data structure. Maintains an in-memory directed graph of nodes (Entities) and edges (Relationships). |
| **`entities.py`** | Data models defining the schema for functions, classes, and modules. |
| **`relations.py`** | Data models defining the schema for connections (Calls, Inherits, Imports). |
| **`report.py`** | The analytics layer. Queries the graph to compute metrics and generate human-readable summaries. |

## Outputs

The tool generates the following artifacts in your specified output folder:

### 1. `summary.md`
A high-level health report of the project, including:
- **Top Called Functions**: Identifying potential hotspots.
- **Top Orchestrators**: Functions with high logic density.
- **Largest Classes**: Entities with the most defined methods.
- **Coupling Metrics**: Modules with the highest number of external dependencies.

### 2. `entities.json`
A complete structured list of all discovered code entities, suitable for machine processing or search indexing.

### 3. `relationships.json`
A list of all detected edges in the code graph, representing the flow of execution and dependency.

### 4. `graph.json`
A full dump of the graph (nodes + edges), ideal for visualization tools.

---
*Built with precision and discipline.*