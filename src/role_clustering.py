import pandas as pd
import os
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import pickle

class PokemonRoleClusterer:
    def __init__(self, processed_dir="../data/processed", model_dir="../models"):
        self.processed_dir = processed_dir
        self.model_dir = model_dir
        os.makedirs(self.model_dir, exist_ok=True)
        self.features = [
            'physical_bulk', 'special_bulk', 'atk_spatk_ratio', 
            'offensive_stat_sum', 'defensive_stat_sum', 'speed_tier'
        ]

    def load_data(self):
        return pd.read_csv(os.path.join(self.processed_dir, "engineered_pokemon_data.csv"))

    def cluster_roles(self, df, n_clusters=8):
        df_clean = df.replace([np.inf, -np.inf], np.nan).dropna(subset=self.features).copy()
        
        scaler = StandardScaler()
        scaled_features = scaler.fit_transform(df_clean[self.features])
        
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        df_clean['cluster_id'] = kmeans.fit_predict(scaled_features)
        
        overall_means = df_clean[self.features].mean()
        overall_bulk_ratio = overall_means['defensive_stat_sum'] / overall_means['offensive_stat_sum']

        def get_individual_role(row):
            is_fast = row['speed_tier'] > overall_means['speed_tier']
            is_bulky = row['defensive_stat_sum'] > overall_means['defensive_stat_sum']
            
            # Use individual ratios
            bulk_ratio = row['defensive_stat_sum'] / row['offensive_stat_sum'] if row['offensive_stat_sum'] > 0 else 0
            is_tank_wall = is_bulky and (bulk_ratio > overall_bulk_ratio * 1.20)
            
            is_physical = row['atk_spatk_ratio'] > 1.15
            is_special = row['atk_spatk_ratio'] < 0.85
            
            if is_fast:
                if is_physical:
                    return "Physical Sweeper"
                elif is_special:
                    return "Special Sweeper"
                else:
                    return "Hybrid Offense"
            elif is_tank_wall:
                return "Tank/Wall"
            elif is_bulky:
                return "Bulky Offense"
            else:
                return "Support"

        df_clean['assigned_role'] = df_clean.apply(get_individual_role, axis=1)
        
        with open(os.path.join(self.model_dir, 'kmeans_role_model.pkl'), 'wb') as f:
            pickle.dump(kmeans, f)
        with open(os.path.join(self.model_dir, 'role_scaler.pkl'), 'wb') as f:
            pickle.dump(scaler, f)
            
        return df_clean

    def run_pipeline(self):
        print("Loading engineered data...")
        df = self.load_data()
        
        print("Clustering Pokémon into roles...")
        df_clustered = self.cluster_roles(df)
        
        output_path = os.path.join(self.processed_dir, "clustered_pokemon_data.csv")
        df_clustered.to_csv(output_path, index=False)
        print("Clustering complete.")
        
        return df_clustered