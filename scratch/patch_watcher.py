import os
import re

path = 'agent/watcher.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# On remplace par le test insensible à la casse
new_content = content.replace('if "Casual" in playlist:', 'if "casual" in playlist.lower():')

with open(path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(new_content)

print("Patching successful.")
