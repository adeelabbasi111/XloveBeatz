import os
import ast

def analyze_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    tree = ast.parse(content)
    functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
    classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    return functions, classes

py_files = []
for root, dirs, files in os.walk('.'):
    if '.venv' in root or '__pycache__' in root or '.git' in root:
        continue
    for file in files:
        if file.endswith('.py'):
            py_files.append(os.path.join(root, file))

for py_file in py_files:
    try:
        functions, classes = analyze_file(py_file)
        print(f"File: {py_file}")
        print(f"  Classes: {classes}")
        print(f"  Functions: {len(functions)} functions")
    except Exception as e:
        print(f"Error parsing {py_file}: {e}")
