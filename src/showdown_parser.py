import os
import requests
import json
import chompjs
import pandas as pd

class ShowdownDataParser:
    def __init__(self, raw_dir="../data/raw"):
        self.raw_dir = raw_dir
        os.makedirs(self.raw_dir, exist_ok=True)
        # We target Showdown's live compiled data endpoints
        self.base_url = "https://play.pokemonshowdown.com/data"

    def fetch_and_parse(self, filename):
        url = f"{self.base_url}/{filename}"
        response = requests.get(url)
        response.raise_for_status()
        
        # Showdown prepends "exports.Battle[X] = " to their JS files.
        # chompjs automatically finds and extracts the core object.
        parsed_dict = chompjs.parse_js_object(response.text)
        return parsed_dict

    def build_move_database(self):
        print("Downloading mechanical move data from Pokémon Showdown...")
        moves_data = self.fetch_and_parse("moves.js")
        
        structured_moves = []
        for move_id, data in moves_data.items():
            # Skip placeholders and glitch moves
            if 'num' not in data or data['num'] <= 0:
                continue
                
            structured_moves.append({
                'id': move_id,
                'name': data.get('name'),
                'type': data.get('type', '').lower(),
                'category': data.get('category'), 
                'base_power': data.get('basePower', 0),
                'accuracy': data.get('accuracy'), 
                'priority': data.get('priority', 0),
                'target': data.get('target'), 
                'flags': json.dumps(data.get('flags', {})),
                'secondary': json.dumps(data.get('secondary', {})),
                'boosts': json.dumps(data.get('boosts', {})),
                'self': json.dumps(data.get('self', {})),
                'volatileStatus': data.get('volatileStatus', ''),
                'selfSwitch': data.get('selfSwitch', False),
                'recoil': json.dumps(data.get('recoil', [0, 1])),
                'drain': json.dumps(data.get('drain', [0, 1])),
                'multihit': json.dumps(data.get('multihit', 1)),
                'selfdestruct': data.get('selfdestruct', ''),
                'critRatio': data.get('critRatio', 1)
            })
            
        df = pd.DataFrame(structured_moves)
        filepath = os.path.join(self.raw_dir, "showdown_moves.csv")
        df.to_csv(filepath, index=False)
        print(f"Saved {len(df)} moves to {filepath}")
        return df

    def build_ability_database(self):
        print("Downloading mechanical ability data from Pokémon Showdown...")
        ability_data = self.fetch_and_parse("abilities.js")
        
        structured_abilities = []
        for ability_id, data in ability_data.items():
            if 'num' not in data or data['num'] <= 0:
                continue
                
            structured_abilities.append({
                'id': ability_id,
                'name': data.get('name'),
                # In Showdown, complex logic is often stored in 'onStart', 'onModifyAtk', etc.
                # We will map these mechanical hooks later. For now, we grab the text descriptions.
                'short_desc': data.get('shortDesc', ''),
                'rating': data.get('rating', 0)
            })
            
        df = pd.DataFrame(structured_abilities)
        filepath = os.path.join(self.raw_dir, "showdown_abilities.csv")
        df.to_csv(filepath, index=False)
        print(f"Saved {len(df)} abilities to {filepath}")
        return df