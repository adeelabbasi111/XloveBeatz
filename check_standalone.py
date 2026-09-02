import os

for root, _, files in os.walk('templates'):
    for file in files:
        if file.endswith('.html'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                if '<head>' in content or '<head ' in content:
                    if 'base.html' not in content:
                        print(f"Standalone HTML with head: {filepath}")
