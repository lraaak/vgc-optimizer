import pandas as pd
import numpy as np
import os

class TeamSynergyScorer:
    def __init__(self, data_path="../data/processed/clustered_pokemon_data.csv"):
        self.data_path = data_path
        if not os.path.exists(self.data_path):
            raise FileNotFoundError(f"Data file not found at {self.data_path}")
            
        self.df = pd.read_csv(self.data_path)
        
        self.weaknesses = {
            'normal': ['fighting'],
            'fire': ['water', 'ground', 'rock'],
            'water': ['electric', 'grass'],
            'electric': ['ground'],
            'grass': ['fire', 'ice', 'poison', 'flying', 'bug'],
            'ice': ['fire', 'fighting', 'rock', 'steel'],
            'fighting': ['flying', 'psychic', 'fairy'],
            'poison': ['ground', 'psychic'],
            'ground': ['water', 'grass', 'ice'],
            'flying': ['electric', 'ice', 'rock'],
            'psychic': ['bug', 'ghost', 'dark'],
            'bug': ['fire', 'flying', 'rock'],
            'rock': ['water', 'grass', 'fighting', 'ground', 'steel'],
            'ghost': ['ghost', 'dark'],
            'dragon': ['ice', 'dragon', 'fairy'],
            'dark': ['fighting', 'bug', 'fairy'],
            'steel': ['fire', 'fighting', 'ground'],
            'fairy': ['poison', 'steel']
        }

    def get_team_data(self, team_names):
        team = self.df[self.df['name'].isin(team_names)]
        if len(team) != len(team_names):
            found = team['name'].tolist()
            missing = set(team_names) - set(found)
            print(f"Warning: Could not find data for {missing}")
        return team

    def calculate_weakness_overlap(self, team_data):
        team_weaknesses = []
        for _, row in team_data.iterrows():
            types = [row['type_1']]
            if pd.notna(row['type_2']):
                types.append(row['type_2'])
            
            for t in types:
                team_weaknesses.extend(self.weaknesses.get(t, []))
        
        overlap_counts = pd.Series(team_weaknesses).value_counts()
        severe_overlaps = overlap_counts[overlap_counts >= 3].count()
        return int(severe_overlaps)

    def calculate_role_balance(self, team_data):
        unique_roles = team_data['assigned_role'].nunique()
        return unique_roles / len(team_data) if len(team_data) > 0 else 0

    def calculate_speed_distribution(self, team_data):
        tiers = team_data['speed_tier'].values
        return float(np.std(tiers)) if len(tiers) > 0 else 0.0

    def score_team(self, team_names):
        team_data = self.get_team_data(team_names)
        
        return {
            'team': team_names,
            'severe_weakness_overlaps': self.calculate_weakness_overlap(team_data),
            'role_balance_score': self.calculate_role_balance(team_data),
            'speed_variance': self.calculate_speed_distribution(team_data),
            'average_bst_efficiency': float(team_data['bst_efficiency'].mean())
        }