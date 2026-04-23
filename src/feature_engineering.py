import pandas as pd
import os
import numpy as np

class PokemonFeatureEngineer:
    def __init__(self, raw_dir="../data/raw", processed_dir="../data/processed"):
        self.raw_dir = raw_dir
        self.processed_dir = processed_dir
        os.makedirs(self.processed_dir, exist_ok=True)

    def load_data(self):
        return pd.read_csv(os.path.join(self.raw_dir, "base_pokemon_data.csv"))

    def engineer_features(self, df):
        df['bst'] = df[['hp', 'attack', 'defense', 'sp_atk', 'sp_def', 'speed']].sum(axis=1)
        
        df['physical_bulk'] = df['hp'] * df['defense']
        df['special_bulk'] = df['hp'] * df['sp_def']
        
        df['atk_spatk_ratio'] = df['attack'] / (df['sp_atk'] + 1e-5)
        
        df['offensive_stat_sum'] = df['attack'] + df['sp_atk'] + df['speed']
        df['defensive_stat_sum'] = df['hp'] + df['defense'] + df['sp_def']
        
        # FIX: Calculate Min-Max Efficiency
        df['effective_bst'] = df['bst'] - df[['attack', 'sp_atk']].min(axis=1)
        df['bst_efficiency'] = df['effective_bst'] / df['bst']
        
        conditions = [
            (df['speed'] < 50),
            (df['speed'] >= 50) & (df['speed'] < 80),
            (df['speed'] >= 80) & (df['speed'] < 100),
            (df['speed'] >= 100) & (df['speed'] < 120),
            (df['speed'] >= 120)
        ]
        choices = [0, 1, 2, 3, 4] 
        df['speed_tier'] = np.select(conditions, choices, default=0)
        
        return df

    def run_pipeline(self):
        print("Loading base data...")
        df = self.load_data()
        
        print("Engineering ML features...")
        df_engineered = self.engineer_features(df)
        
        output_path = os.path.join(self.processed_dir, "engineered_pokemon_data.csv")
        df_engineered.to_csv(output_path, index=False)
        print(f"Pipeline complete. Saved to {output_path}")
        
        return df_engineered