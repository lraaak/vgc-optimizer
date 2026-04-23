import pandas as pd
import numpy as np
import os
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler
from win_predictor import MonteCarloSimulator
from synergy_scorer import TeamSynergyScorer

class CounterRecommender:
    def __init__(self, data_path="../data/processed/clustered_pokemon_data.csv"):
        self.data_path = data_path
        if not os.path.exists(self.data_path):
            # Fallback pathing logic
            alt_path = data_path.replace("../", "")
            if os.path.exists(alt_path):
                self.data_path = alt_path
            else:
                raise FileNotFoundError(f"Data not found: {self.data_path}")
            
        self.df = pd.read_csv(self.data_path).set_index('name')
        self.simulator = MonteCarloSimulator(data_path=self.data_path)
        self.scorer = TeamSynergyScorer(data_path=self.data_path)
        
        self.features = ['hp', 'attack', 'defense', 'sp_atk', 'sp_def', 'speed']
        self.scaler = MinMaxScaler()
        self.scaled_stats = pd.DataFrame(
            self.scaler.fit_transform(self.df[self.features]), 
            index=self.df.index, 
            columns=self.features
        )

        self.meta_threats = [
            'incineroar', 'flutter-mane', 'urshifu', 
            'landorus-therian', 'amoonguss', 'rillaboom', 
            'chi-yu', 'tornadus', 'pelipper'
        ]
        self.meta_threats = [p for p in self.meta_threats if p in self.df.index]

    def identify_weaknesses(self, team_names):
        threat_scores = {}
        for threat in self.meta_threats:
            if threat in team_names:
                continue
            other_meta = [p for p in self.meta_threats if p != threat and p not in team_names]
            if len(other_meta) >= 3:
                threat_team = [threat] + list(np.random.choice(other_meta, 3, replace=False))
            else:
                threat_team = [threat] + other_meta
            
            win_rate = self.simulator.simulate_matchup(team_names, threat_team, n_simulations=50, return_prob=True)
            threat_scores[threat] = 1 - (win_rate if win_rate is not None else 0.5)
            
        sorted_threats = sorted(threat_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_threats[:2] 

    def recommend_team_counters(self, team_names, top_n=5, weaknesses=None):
        if weaknesses is None:
            weaknesses = self.identify_weaknesses(team_names)
        if not weaknesses:
            return []
            
        results = []
        
        for threat_name, _ in weaknesses:
            threat = self.df.loc[threat_name]
            
            ideal_hp = 1.0 
            ideal_def = 1.0 if threat['attack'] > threat['sp_atk'] else 0.2
            ideal_spdef = 1.0 if threat['sp_atk'] >= threat['attack'] else 0.2
            ideal_atk = 1.0 if threat['defense'] < threat['sp_def'] else 0.2
            ideal_spatk = 1.0 if threat['sp_def'] <= threat['defense'] else 0.2
            ideal_speed = min(1.0, (threat['speed'] + 10) / self.df['speed'].max())
            
            ideal_vector = np.array([[ideal_hp, ideal_atk, ideal_def, ideal_spatk, ideal_spdef, ideal_speed]])
            similarities = cosine_similarity(ideal_vector, self.scaled_stats)[0]
            self.df['base_similarity'] = similarities
            
            candidates = self.df[~self.df.index.isin(team_names)].copy()
            
            for name, row in candidates.iterrows():
                off_eff_1 = self.scorer.calculate_effectiveness(row['type_1'], threat)
                off_eff_2 = self.scorer.calculate_effectiveness(row['type_2'], threat) if pd.notna(row['type_2']) else 0.0
                def_eff = self.scorer.calculate_effectiveness(threat['type_1'], row)
                
                offense_mult = max(off_eff_1, off_eff_2)
                defense_mult = 1.0 / def_eff if def_eff > 0 else 4.0
                
                # Combine stat similarity with type advantages
                score = row['base_similarity'] * (offense_mult * 0.6 + defense_mult * 0.4)
                candidates.loc[name, 'counter_score'] = score
            
            # Only recommend Pokemon that have at least some type advantage
            candidates = candidates[(candidates['counter_score'] > candidates['base_similarity'])]
                
            # Take top 3 for EACH weakness to ensure diversity
            top_counters = candidates.sort_values(by='counter_score', ascending=False).head(3)
            
            for name, row in top_counters.iterrows():
                # Avoid duplicates across threats
                if name not in [r['name'] for r in results]:
                    results.append({
                        'name': name,
                        'role': row['assigned_role'],
                        'counter_score': round(row['counter_score'], 3),
                        'targets': threat_name
                    })
            
        # Return sorted by score overall
        results = sorted(results, key=lambda x: x['counter_score'], reverse=True)
        return results[:top_n] if top_n > 0 else results

if __name__ == "__main__":
    recommender = CounterRecommender()
    sample_team = ['charizard', 'venusaur', 'blastoise']
    
    print(f"Analyzing team: {sample_team}")
    weaknesses = recommender.identify_weaknesses(sample_team)
    print(f"Struggles against: {[w[0] for w in weaknesses]}")
    
    recs = recommender.recommend_team_counters(sample_team)
    print("\nRecommended 4th Slot:")
    for r in recs:
        print(f"- {r['name'].capitalize()} ({r['role']}) | Similarity Score: {r['counter_score']}")