import os
import requests
import pandas as pd

class PokemonDataLoader:
    def __init__(self, raw_data_dir="../data/raw"):
        self.raw_data_dir = raw_data_dir
        self.base_url = "https://pokeapi.co/api/v2"

    def fetch_pokemon_list(self, limit=150):
        url = f"{self.base_url}/pokemon?limit={limit}"
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
        types = [t['type']['name'] for t in data['types']]
        abilities = [a['ability']['name'] for a in data['abilities']]
        
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
            'height_m': data['height'] / 10
        }
        return parsed

    def build_base_dataset(self, limit=150, filename="base_pokemon_data.csv"):
        print(f"Fetching list of {limit} Pokémon...")
        pokemon_list = self.fetch_pokemon_list(limit)
        
        parsed_data = []
        for i, p in enumerate(pokemon_list):
            if i % 50 == 0:
                print(f"Processing {i}/{limit}...")
            details = self.fetch_pokemon_details(p['url'])
            parsed = self.parse_pokemon_data(details)
            if parsed:
                parsed_data.append(parsed)
                
        df = pd.DataFrame(parsed_data)
        filepath = os.path.join(self.raw_data_dir, filename)
        df.to_csv(filepath, index=False)
        print(f"Dataset saved to {filepath}")
        return df