import os

path = 'agent/watcher.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if '"won": row.get(\'Won\', \'False\').lower() == \'true\'' in line:
        # On remplace la ligne existante par la version avec les nouvelles colonnes
        new_lines.append(line.replace('"won": row.get(\'Won\', \'False\').lower() == \'true\'', 
                                      '"won": row.get(\'Won\', \'False\').lower() == \'true\',\n' +
                                      '                        "demolishes": int(row.get(\'Demolishes\', 0)) if row.get(\'Demolishes\') else 0,\n' +
                                      '                        "pads": int(row.get(\'Pads\', 0)) if row.get(\'Pads\') else 0,\n' +
                                      '                        "boost_usage": float(row.get(\'BoostUsage\', 0)) if row.get(\'BoostUsage\') else 0.0,\n' +
                                      '                        "possession_time": row.get(\'PossessionTime\', \'0:00\')'))
    else:
        new_lines.append(line)

with open(path, 'w', encoding='utf-8', newline='\n') as f:
    f.writelines(new_lines)

print("Patching CSV extraction successful.")
