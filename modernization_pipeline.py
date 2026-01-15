import os
import networkx as nx
import time
from pathlib import Path
# Import modules from code_analyzer/code_intel or local directory as needed

# Always use code_intel modules for migrated system
from code_intel.scanner import LocalScanner
from code_intel.graph_builder import CodeGraphPipeline
from code_intel.embedder import BGEEmbedder
from code_intel.chunker import HybridChunker
from code_intel.logger import PipelineLogger
from code_intel.storage import VectorStore
from code_intel.chat import ModernizationChat

def run_modernization_pipeline(repo_path: str, target_subfolder_str: str):
    # --- Initialization ---
    scanner = LocalScanner(repo_path)
    builder = CodeGraphPipeline()
    embedder = BGEEmbedder()
    store = VectorStore()
    chunker = HybridChunker()
    logger = PipelineLogger()
    
    root = Path(repo_path).resolve()
    target_path = Path(target_subfolder_str).resolve()
    entity_name = target_path.name.replace("_", " ").title().replace(" ", "")

    print(f"🚀 Scanning repository: {root}")
    all_files = scanner.get_files()
    
    # --- PASS 1: Global Symbols ---
    for f_path in all_files:
        try:
            with open(f_path, 'rb') as f:
                builder.pass_1_symbols(f_path, f.read())
        except Exception:
            continue

    # --- PASS 2: Target File Analysis ---
    target_files = [f for f in all_files if Path(f).resolve().is_relative_to(target_path)]
    print(f"🔗 Found {len(target_files)} files in target. Building relationships...")
    
    target_chunks = []
    for f_path in target_files:
        try:
            with open(f_path, 'rb') as f:
                content_bytes = f.read()
                builder.pass_2_calls(f_path, content_bytes)
                
                content_str = content_bytes.decode('utf-8', errors='ignore')
                file_chunks = chunker.split_text(content_str)
                for c in file_chunks:
                    target_chunks.append({
                        "content": c, "file_path": f_path, "name": os.path.basename(f_path)
                    })
        except Exception as e:
            print(f"⚠️ Error processing {f_path}: {e}")

    # --- PASS 3: Vector Indexing ---

    graph_filename = f"{target_path.name}_graph.gexf"
    if builder.G is not None and hasattr(builder.G, 'number_of_nodes') and builder.G.number_of_nodes() > 0:
        nx.write_gexf(builder.G, graph_filename)
        print(f"Graph written to {graph_filename}")
    else:
        print("[Warning] No graph was built (empty or None). Skipping graph export.")

    # Embedding and storing chunks
    print(f"🔎 Embedding {len(target_chunks)} code chunks...")
    for chunk in target_chunks:
        embedding = embedder.embed(chunk["content"])
        store.add_embedding(chunk["content"], embedding, chunk["file_path"], chunk["name"])

    print("✅ Modernization pipeline complete.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python modernization_pipeline.py <repo_path> <target_subfolder>")
        sys.exit(1)
    run_modernization_pipeline(sys.argv[1], sys.argv[2])
