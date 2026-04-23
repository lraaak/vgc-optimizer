import os
import requests
import pandas as pd

class PokemonDataLoader:
    def __init__(self, raw_data_dir="../data/raw"):
        self.raw_data_dir = raw_data_dir
        self.base_url = "https://pokeapi.co/api/v2"

    def fetch_pokemon_list(self, limit=150, offset=0):
        url = f"{self.base_url}/pokemon?limit={limit}&offset={offset}"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()['results']

    def fetch_pokemon_details(self, url):
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        return None

    def parse_pokemon_data(self, data):
        if not data:
            return None
        
        stats = {stat['stat']['name']: stat['base_stat'] for stat in data['stats']}
        types = sorted([t['type']['name'] for t in data['types']])
        abilities = [a['ability']['name'] for a in data['abilities']]
        
        # Create a unique key for stat/type combo to filter cosmetic duplicates
        stat_key = (
            stats.get('hp', 0), stats.get('attack', 0), stats.get('defense', 0),
            stats.get('special-attack', 0), stats.get('special-defense', 0), stats.get('speed', 0),
            tuple(types)
        )
        
        parsed = {
            'id': data['id'],
            'name': data['name'],
            'type_1': types[0],
            'type_2': types[1] if len(types) > 1 else None,
            'ability_1': abilities[0] if len(abilities) > 0 else None,
            'ability_2': abilities[1] if len(abilities) > 1 else None,
            'hidden_ability': abilities[2] if len(abilities) > 2 else None,
            'hp': stats.get('hp', 0),
            'attack': stats.get('attack', 0),
            'defense': stats.get('defense', 0),
            'sp_atk': stats.get('special-attack', 0),
            'sp_def': stats.get('special-defense', 0),
            'speed': stats.get('speed', 0),
            'weight_kg': data['weight'] / 10,
            'height_m': data['height'] / 10,
            'stat_key': stat_key
        }
        return parsed

    def build_base_dataset(self, limit=1500, filename="base_pokemon_data.csv"):
        print(f"Fetching total list of Pokémon (including varieties)...")
        # PokeAPI currently has ~1350 entries including all forms
        pokemon_list = self.fetch_pokemon_list(limit)
        
        parsed_data = []
        seen_stat_keys = set()
        
        total = len(pokemon_list)
        for i, p in enumerate(pokemon_list):
            if i % 50 == 0:
                print(f"Processing {i}/{total}...")
            
            details = self.fetch_pokemon_details(p['url'])
            parsed = self.parse_pokemon_data(details)
            
            if parsed:
                # Only include if it has unique stats/types or is a base form (ID <= 1025)
                # This excludes 50+ identical Alcremie/Vivillon/Pikachu forms
                if parsed['stat_key'] not in seen_stat_keys or parsed['id'] <= 1025:
                    seen_stat_keys.add(parsed['stat_key'])
                    # Remove the temp key before saving
                    del parsed['stat_key']
                    parsed_data.append(parsed)
                
        df = pd.DataFrame(parsed_data)
        filepath = os.path.join(self.raw_data_dir, filename)
        df.to_csv(filepath, index=False)
        print(f"Dataset saved to {filepath}. Total unique forms: {len(df)}")
        return df