import pandas as pd
import numpy as np
import os

class TeamSynergyScorer:
    def __init__(self, data_path="../data/processed/clustered_pokemon_data.csv"):
        self.data_path = data_path
        if not os.path.exists(self.data_path):
            raise FileNotFoundError(f"Data file not found at {self.data_path}")
            
        self.df = pd.read_csv(self.data_path)
        
        # Comprehensive Type Chart (Attacker: {DefenderType: Multiplier})
        # 2.0 = Weakness, 0.5 = Resistance, 0.0 = Immunity
        self.type_chart = {
            'normal': {'rock': 0.5, 'ghost': 0.0, 'steel': 0.5},
            'fire': {'fire': 0.5, 'water': 0.5, 'grass': 2.0, 'ice': 2.0, 'bug': 2.0, 'rock': 0.5, 'dragon': 0.5, 'steel': 2.0},
            'water': {'fire': 2.0, 'water': 0.5, 'grass': 0.5, 'ground': 2.0, 'rock': 2.0, 'dragon': 0.5},
            'electric': {'water': 2.0, 'electric': 0.5, 'grass': 0.5, 'ground': 0.0, 'flying': 2.0, 'dragon': 0.5},
            'grass': {'fire': 0.5, 'water': 2.0, 'grass': 0.5, 'poison': 0.5, 'ground': 2.0, 'flying': 0.5, 'bug': 0.5, 'rock': 2.0, 'dragon': 0.5, 'steel': 0.5},
            'ice': {'fire': 0.5, 'water': 0.5, 'grass': 2.0, 'ice': 0.5, 'ground': 2.0, 'flying': 2.0, 'dragon': 2.0, 'steel': 0.5},
            'fighting': {'normal': 2.0, 'ice': 2.0, 'poison': 0.5, 'flying': 0.5, 'psychic': 0.5, 'bug': 0.5, 'rock': 2.0, 'ghost': 0.0, 'dark': 2.0, 'steel': 2.0, 'fairy': 0.5},
            'poison': {'grass': 2.0, 'poison': 0.5, 'ground': 0.5, 'rock': 0.5, 'ghost': 0.5, 'steel': 0.0, 'fairy': 2.0},
            'ground': {'fire': 2.0, 'electric': 2.0, 'grass': 0.5, 'poison': 2.0, 'flying': 0.0, 'bug': 0.5, 'rock': 2.0, 'steel': 2.0},
            'flying': {'electric': 0.5, 'grass': 2.0, 'fighting': 2.0, 'bug': 2.0, 'rock': 0.5, 'steel': 0.5},
            'psychic': {'fighting': 2.0, 'poison': 2.0, 'psychic': 0.5, 'dark': 0.0, 'steel': 0.5},
            'bug': {'fire': 0.5, 'grass': 2.0, 'fighting': 0.5, 'poison': 0.5, 'flying': 0.5, 'psychic': 2.0, 'ghost': 0.5, 'dark': 2.0, 'fairy': 0.5, 'steel': 0.5},
            'rock': {'fire': 2.0, 'ice': 2.0, 'fighting': 0.5, 'ground': 0.5, 'flying': 2.0, 'bug': 2.0, 'steel': 0.5},
            'ghost': {'normal': 0.0, 'psychic': 2.0, 'ghost': 2.0, 'dark': 0.5},
            'dragon': {'dragon': 2.0, 'steel': 0.5, 'fairy': 0.0},
            'dark': {'fighting': 0.5, 'psychic': 2.0, 'ghost': 2.0, 'dark': 0.5, 'fairy': 0.5},
            'steel': {'fire': 0.5, 'water': 0.5, 'electric': 0.5, 'ice': 2.0, 'rock': 2.0, 'steel': 0.5, 'fairy': 2.0},
            'fairy': {'fire': 0.5, 'fighting': 2.0, 'poison': 0.5, 'dragon': 2.0, 'dark': 2.0, 'steel': 0.5}
        }
        self.types = list(self.type_chart.keys())

    def get_team_data(self, team_names):
        team = self.df[self.df['name'].isin(team_names)]
        return team

    def calculate_effectiveness(self, attacker_type, defender_row):
        mult = 1.0
        # Check Type 1
        mult *= self.type_chart.get(attacker_type, {}).get(defender_row['type_1'], 1.0)
        # Check Type 2
        if pd.notna(defender_row['type_2']):
            mult *= self.type_chart.get(attacker_type, {}).get(defender_row['type_2'], 1.0)
        return mult

    def calculate_weakness_overlap(self, team_data):
        severe_weaknesses = 0
        for t in self.types:
            weak_count = 0
            for _, row in team_data.iterrows():
                if self.calculate_effectiveness(t, row) > 1.0:
                    weak_count += 1
            if weak_count >= 3:
                severe_weaknesses += 1
        return severe_weaknesses

    def calculate_resistance_coverage(self, team_data):
        # How many types does the team have at least one resistance/immunity for?
        covered_types = 0
        for t in self.types:
            for _, row in team_data.iterrows():
                if self.calculate_effectiveness(t, row) < 1.0:
                    covered_types += 1
                    break
        return covered_types / len(self.types)

    def calculate_role_balance(self, team_data):
        if len(team_data) == 0: return 0
        return team_data['assigned_role'].nunique() / len(team_data)

    def calculate_speed_distribution(self, team_data):
        if len(team_data) == 0: return 0
        return float(np.std(team_data['speed_tier'].values))

    def score_team(self, team_names):
        team_data = self.get_team_data(team_names)
        
        return {
            'team': team_names,
            'severe_weakness_overlaps': self.calculate_weakness_overlap(team_data),
            'resistance_coverage_score': self.calculate_resistance_coverage(team_data),
            'role_balance_score': self.calculate_role_balance(team_data),
            'speed_variance': self.calculate_speed_distribution(team_data),
            'average_bst_efficiency': float(team_data['bst_efficiency'].mean()) if not team_data.empty else 0.0
        }