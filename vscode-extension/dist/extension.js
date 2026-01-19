"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const cp = __importStar(require("child_process"));
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const OUTPUT_CHANNEL_NAME = 'Code Analyzer';
function activate(context) {
    const output = vscode.window.createOutputChannel(OUTPUT_CHANNEL_NAME);
    output.appendLine('[info] Code Analyzer Runner activated (this is our extension).');
    // Make the channel discoverable without running any command.
    output.show(true);
    console.log('[code-analyzer-runner] activated');
    const status = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    status.text = '$(beaker) Run Code Analyzer';
    status.tooltip = 'Run Code Analyzer on the current workspace';
    status.command = 'codeAnalyzer.runAnalysis';
    status.show();
    const disposable = vscode.commands.registerCommand('codeAnalyzer.runAnalysis', async () => {
        output.show(true);
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        if (!workspaceFolder) {
            vscode.window.showErrorMessage('Open a folder/workspace first.');
            return;
        }
        const config = vscode.workspace.getConfiguration('codeAnalyzer');
        const pythonPath = (config.get('pythonPath') || 'python').trim();
        const defaultOutputFolder = (config.get('defaultOutputFolder') || 'results').trim();
        output.appendLine(`[info] Workspace: ${workspaceFolder.uri.fsPath}`);
        // Try to locate the analyzer root by finding code_intel/analyze.py
        const analyzerEntrypoints = await vscode.workspace.findFiles('**/code_intel/analyze.py', '**/node_modules/**', 5);
        if (analyzerEntrypoints.length === 0) {
            vscode.window.showErrorMessage('Could not find code_intel/analyze.py in this workspace.');
            return;
        }
        // Pick the closest analyzer entrypoint (prefer one under a folder named "code_analyzer")
        const preferred = analyzerEntrypoints.find((u) => u.fsPath.toLowerCase().includes(`${path.sep}code_analyzer${path.sep}`));
        const entrypointUri = preferred ?? analyzerEntrypoints[0];
        const analyzerRoot = path.dirname(path.dirname(entrypointUri.fsPath)); // .../code_analyzer
        output.appendLine(`[info] Analyzer entrypoint: ${entrypointUri.fsPath}`);
        output.appendLine(`[info] Analyzer root: ${analyzerRoot}`);
        const targetPath = workspaceFolder.uri.fsPath;
        const outputFolderInput = await vscode.window.showInputBox({
            title: 'Code Analyzer Output Folder',
            prompt: 'Relative to analyzer root',
            value: defaultOutputFolder,
            validateInput: (v) => (v.trim().length === 0 ? 'Output folder cannot be empty' : undefined)
        });
        if (!outputFolderInput) {
            output.appendLine('[info] Cancelled.');
            return;
        }
        const outputDir = path.resolve(analyzerRoot, outputFolderInput.trim());
        fs.mkdirSync(outputDir, { recursive: true });
        const command = pythonPath;
        const args = ['-m', 'code_intel.analyze', targetPath, '--output', outputDir, '--extra-artifacts'];
        output.appendLine(`[run] ${command} ${args.map(a => JSON.stringify(a)).join(' ')}`);
        await runProcess(command, args, analyzerRoot, output);
        // Generate analysis README
        const readmePath = path.join(outputDir, 'ANALYSIS_README.md');
        const readmeText = generateAnalysisReadme(outputDir, analyzerRoot, targetPath);
        fs.writeFileSync(readmePath, readmeText, { encoding: 'utf-8' });
        output.appendLine(`[ok] Wrote ${readmePath}`);
        const doc = await vscode.workspace.openTextDocument(vscode.Uri.file(readmePath));
        await vscode.window.showTextDocument(doc, { preview: false });
        vscode.window.showInformationMessage(`Analysis complete. Output: ${outputDir}`);
    });
    context.subscriptions.push(disposable, output);
    context.subscriptions.push(status);
}
function deactivate() { }
function runProcess(command, args, cwd, output) {
    return new Promise((resolve, reject) => {
        const child = cp.spawn(command, args, {
            cwd,
            env: process.env,
            shell: false,
            windowsHide: true
        });
        child.stdout?.on('data', (d) => output.append(d.toString()));
        child.stderr?.on('data', (d) => output.append(d.toString()));
        child.on('error', (err) => {
            output.appendLine(`\n[error] Failed to start process: ${String(err)}`);
            vscode.window.showErrorMessage(`Failed to start analyzer: ${String(err)}`);
            reject(err);
        });
        child.on('close', (code) => {
            if (code === 0) {
                output.appendLine(`\n[ok] Analyzer exited with code 0`);
                resolve();
            }
            else {
                output.appendLine(`\n[error] Analyzer exited with code ${code}`);
                vscode.window.showErrorMessage(`Analyzer failed (exit code ${code}). See Output -> ${OUTPUT_CHANNEL_NAME}`);
                reject(new Error(`Analyzer exited with code ${code}`));
            }
        });
    });
}
function generateAnalysisReadme(outputDir, analyzerRoot, targetPath) {
    const files = [
        'domain_overview.md',
        'dependency_report.md',
        'business_rules.md',
        'business_rules.json',
        'entity_map.json',
        'call_graph.json',
        'call_graph.gexf',
        'ai_context.json',
        'summary.md',
        'entities.json',
        'relationships.json',
        'graph.json'
    ];
    const existing = files.filter(f => fs.existsSync(path.join(outputDir, f)));
    const timestamp = new Date().toISOString();
    const lines = [];
    lines.push('# Code Analyzer - Analysis Output');
    lines.push('');
    lines.push(`- Generated: ${timestamp}`);
    lines.push(`- Target: ${targetPath}`);
    lines.push(`- Output folder: ${outputDir}`);
    lines.push('');
    lines.push('## Artifacts');
    if (existing.length === 0) {
        lines.push('- (No artifacts found)');
    }
    else {
        for (const f of existing) {
            lines.push(`- [${f}](./${encodeURI(f)})`);
        }
    }
    lines.push('');
    lines.push('## Notes');
    lines.push('- `call_graph.gexf` is optional (requires `networkx`).');
    lines.push('- `business_rules.*` are heuristic (best-effort static analysis).');
    lines.push('');
    return lines.join('\n');
}
//# sourceMappingURL=extension.js.map