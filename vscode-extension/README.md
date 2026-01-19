# Code Analyzer Runner (VS Code Extension)

Runs the local Python analyzer (`code_intel`) on the current workspace and writes AI-ready artifacts.

## Command

- **Code Analyzer: Run Analysis** (`codeAnalyzer.runAnalysis`)

You can run it without Command Palette:
- Click the **Run Code Analyzer** status bar button
- Or right-click a folder in Explorer and choose **Code Analyzer: Run Analysis**

## What it does

- Locates `code_intel/analyze.py` inside your workspace
- Runs:
  - `python -m code_intel.analyze <target> --output <out> --extra-artifacts`
- Writes an additional `ANALYSIS_README.md` into the output folder with links to generated artifacts

## Settings

- `codeAnalyzer.pythonPath` (default: `python`)
- `codeAnalyzer.defaultOutputFolder` (default: `results`)

## Dev (run locally)

1. Open this folder in VS Code: `code_analyzer/vscode-extension`
2. Run `npm install`
3. Press `F5` to launch the Extension Development Host

In the new VS Code window, open your analyzer workspace and run **Code Analyzer: Run Analysis**.
