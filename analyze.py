import ast
import sys
import os

# Minimal code analyzer: lists all functions and classes in Python files
def analyze_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        code = f.read()
    try:
        tree = ast.parse(code, filename=filepath)
    except Exception as e:
        print(f"Could not parse {filepath}: {e}")
        return [], []
    functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
    classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    return functions, classes

def analyze_path(path):
    all_functions = []
    all_classes = []
    if os.path.isfile(path) and path.endswith('.py'):
        functions, classes = analyze_file(path)
        all_functions.extend(functions)
        all_classes.extend(classes)
    else:
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith('.py'):
                    f, c = analyze_file(os.path.join(root, file))
                    all_functions.extend(f)
                    all_classes.extend(c)
    return all_functions, all_classes

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze.py <file-or-directory>")
        sys.exit(1)
    path = sys.argv[1]
    functions, classes = analyze_path(path)
    print("Functions found:")
    for fn in sorted(set(functions)):
        print(f"  - {fn}")
    print("\nClasses found:")
    for cl in sorted(set(classes)):
        print(f"  - {cl}")
