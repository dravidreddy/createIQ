"""
DEVTOOLS - Fix Indexes
DO NOT import in production code.
"""
import glob
import re

for filepath in glob.glob('app/models/**/*.py', recursive=True):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # We want to replace lines like: indexes = ["user_id", "status"]
    # With: indexes = []
    # But ONLY if it contains strings (doesn't contain IndexModel)
    
    new_content = re.sub(
        r'indexes\s*=\s*\[\s*(?:"[^"]*"\s*(?:,\s*"[^"]*"\s*)*|)\s*\]',
        'indexes = []',
        content
    )
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Fixed {filepath}")
