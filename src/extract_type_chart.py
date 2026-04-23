import chompjs
import json
import os

# Path to the Showdown file we cloned
ts_path = 'references/pokemon-showdown/data/typechart.ts'

with open(ts_path, 'r') as f:
    content = f.read()
    # chompjs is great at extracting JS objects from TS/JS files
    # We skip the "export const TypeChart = " part
    data = chompjs.parse_js_object(content[content.find('{'):])

# Showdown uses: 0=normal, 1=super, 2=resist, 3=immune
# We want to convert this to multipliers for our engine
# Actually, our engine expects a dict: type_chart[attack_type][defender_type] = mult

multiplier_chart = {}

# Map Showdown's numbers to multipliers
val_map = {0: 1.0, 1: 2.0, 2: 0.5, 3: 0.0}

# Showdown's chart is [defender_type][attack_type]
# We want [attack_type][defender_type]
for def_type, info in data.items():
    if 'damageTaken' not in info: continue
    
    for atk_type, val in info['damageTaken'].items():
        # Skip special flags like 'prankster' or 'sandstorm'
        if not atk_type[0].isupper(): continue
        
        atk_type_lower = atk_type.lower()
        if atk_type_lower not in multiplier_chart:
            multiplier_chart[atk_type_lower] = {}
        
        multiplier_chart[atk_type_lower][def_type] = val_map.get(val, 1.0)

# Save to data/raw
os.makedirs('data/raw', exist_ok=True)
with open('data/raw/type_chart.json', 'w') as f:
    json.dump(multiplier_chart, f, indent=4)

print("Successfully converted Showdown Type Chart to data/raw/type_chart.json!")
