import re
import os
import pandas as pd
import json

def extract_items_robust():
    ts_path = 'references/pokemon-showdown/data/items.ts'
    if not os.path.exists(ts_path):
        print("Error: Showdown items.ts not found.")
        return

    with open(ts_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    items = []
    current_item = None
    
    # Regex patterns (adjusted for stripped lines)
    item_key_pattern = re.compile(r'^([a-z0-9]+): \{$')
    name_pattern = re.compile(r'name: "(.+)"')
    gen_pattern = re.compile(r'gen: (\d+)')
    is_berry_pattern = re.compile(r'isBerry: true')
    
    # We'll also look for specific VGC modifiers
    modify_atk_pattern = re.compile(r'onModifyAtk\(.+\) \{')
    modify_spa_pattern = re.compile(r'onModifySpA\(.+\) \{')
    modify_spe_pattern = re.compile(r'onModifySpe\(.+\) \{')
    modify_spd_pattern = re.compile(r'onModifySpD\(.+\) \{')

    for line in lines:
        line = line.strip()
        
        # Detect start of a new item
        match = item_key_pattern.match(line)
        if match:
            if current_item:
                items.append(current_item)
            current_item = {
                'id': match.group(1),
                'name': '',
                'gen': 0,
                'is_berry': False,
                'category': 'General',
                'vgc_modifier': None
            }
            continue
            
        if not current_item:
            continue
            
        # Parse fields
        if 'name: "' in line:
            name_match = name_pattern.search(line)
            if name_match: current_item['name'] = name_match.group(1)
            
        if 'gen: ' in line:
            gen_match = gen_pattern.search(line)
            if gen_match: current_item['gen'] = int(gen_match.group(1))
            
        if 'isBerry: true' in line:
            current_item['is_berry'] = True
            current_item['category'] = 'Berry'

        # Detect specific Choice/Stat items based on name or effects
        if 'Choice' in current_item['name']:
            current_item['category'] = 'Choice'
        elif 'Assault Vest' in current_item['name']:
            current_item['category'] = 'Assault Vest'
        elif 'Life Orb' in current_item['name']:
            current_item['category'] = 'Life Orb'

    # Add the last one
    if current_item:
        items.append(current_item)

    df = pd.DataFrame(items)
    # Filter out past-gen stuff to keep it clean
    df = df[df['gen'] >= 0]
    
    os.makedirs('data/raw', exist_ok=True)
    df.to_csv('data/raw/showdown_items.csv', index=False)
    print(f"Successfully extracted {len(df)} items using Robust Regex Parser.")

if __name__ == "__main__":
    extract_items_robust()
