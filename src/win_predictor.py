import pandas as pd
import numpy as np
import os
import pickle
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
from synergy_scorer import TeamSynergyScorer

class MonteCarloSimulator:
    def __init__(self, data_path="../data/processed/clustered_pokemon_data.csv"):
        self.data_path = data_path
        if not os.path.exists(self.data_path):
            # Fallback to engineered data if clustered isn't available
            alt_path = data_path.replace("clustered", "engineered")
            if os.path.exists(alt_path):
                self.data_path = alt_path
            else:
                raise FileNotFoundError(f"Data not found: {self.data_path}")
        self.df = pd.read_csv(self.data_path).set_index('name')
        # Use TeamSynergyScorer for type effectiveness logic
        self.scorer = TeamSynergyScorer(data_path=self.data_path)

    def get_leads(self, team_names):
        # Ensure we only pick names that actually exist in the dataframe
        valid_names = [n for n in team_names if n in self.df.index]
        if len(valid_names) < 2:
            raise KeyError("Not enough valid Pokemon names found")
        
        team_data = self.df.loc[valid_names].copy()
        team_data = team_data.sort_values(by='speed', ascending=False)
        return team_data.iloc[:2] 

    def calculate_damage_score(self, attacker, defender, rng_roll):
        # Determine best type effectiveness
        # Attacker uses their own types (Type 1 or Type 2) for STAB
        type1_eff = self.scorer.calculate_effectiveness(attacker['type_1'], defender)
        type2_eff = 1.0
        if pd.notna(attacker['type_2']):
            type2_eff = self.scorer.calculate_effectiveness(attacker['type_2'], defender)
        
        # Max effectiveness including 1.5x STAB multiplier
        type_mult = max(type1_eff, type2_eff) * 1.5
        
        # Basic damage formula: (Atk/Def) * BasePower * RNG * TypeMult
        phys_dmg = (attacker['attack'] / (defender['defense'] + 1)) 
        spec_dmg = (attacker['sp_atk'] / (defender['sp_def'] + 1))
        
        # VGC moves are roughly 80-100 base power
        base_dmg = max(phys_dmg, spec_dmg) * 50 
        
        # Final damage percentage of HP dealt (capped at 1.0 to prevent overkill skewing momentum)
        total_dmg = (base_dmg / defender['hp']) * rng_roll * type_mult
        return min(1.0, total_dmg)

    def simulate_matchup(self, team_a_names, team_b_names, n_simulations=100, return_prob=False):
        # Filter valid pokemon
        valid_a = [n for n in team_a_names if n in self.df.index]
        valid_b = [n for n in team_b_names if n in self.df.index]
        
        if len(valid_a) < 2 or len(valid_b) < 2:
            return None 

        team_a_wins = 0

        for _ in range(n_simulations):
            team_a_momentum = 0
            team_b_momentum = 0
            
            # Lead Diversity: Randomly select 2 leads for each simulation
            leads_a_indices = np.random.choice(len(valid_a), 2, replace=False)
            leads_b_indices = np.random.choice(len(valid_b), 2, replace=False)
            
            for i in range(2):
                p_a = self.df.loc[valid_a[leads_a_indices[i]]]
                p_b = self.df.loc[valid_b[leads_b_indices[i]]]
                
                roll_a = np.random.uniform(0.85, 1.0)
                roll_b = np.random.uniform(0.85, 1.0)
                
                dmg_to_b = self.calculate_damage_score(p_a, p_b, roll_a)
                dmg_to_a = self.calculate_damage_score(p_b, p_a, roll_b)
                
                # If a Pokemon is faster, it has a chance to reduce opponent damage (representing a KO or flinch)
                if p_a['speed'] > p_b['speed']:
                    dmg_to_a *= 0.85
                elif p_b['speed'] > p_a['speed']:
                    dmg_to_b *= 0.85

                team_a_momentum += dmg_to_b
                team_b_momentum += dmg_to_a

            if team_a_momentum > team_b_momentum:
                team_a_wins += 1

        # Calculate and return the exact probability if requested
        win_prob = team_a_wins / n_simulations
        if return_prob:
            return win_prob
        
        return 1 if win_prob > 0.5 else 0


class WinProbabilityModel:
    def __init__(self, models_dir="../models", synthetic_dir="../data/synthetic"):
        self.models_dir = models_dir
        self.synthetic_dir = synthetic_dir
        os.makedirs(self.models_dir, exist_ok=True)
        os.makedirs(self.synthetic_dir, exist_ok=True)
        
        self.scorer = TeamSynergyScorer()
        # Initialize simulator with the same data source as the scorer
        self.simulator = MonteCarloSimulator(data_path=self.scorer.data_path)
        self.model = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=5)

    def generate_synthetic_matches(self, num_matches=500):
        all_pokemon = self.scorer.df['name'].tolist()
        dataset = []

        print(f"Generating {num_matches} synthetic matchups...")
        
        for i in range(num_matches):
            if i % 100 == 0:
                print(f"Simulating match {i}/{num_matches}...")
                
            team_a = np.random.choice(all_pokemon, 4, replace=False).tolist()
            team_b = np.random.choice(all_pokemon, 4, replace=False).tolist()
            
            label = self.simulator.simulate_matchup(team_a, team_b, n_simulations=50)
            if label is None:
                continue

            score_a = self.scorer.score_team(team_a)
            score_b = self.scorer.score_team(team_b)
            
            match_data = {
                'a_weakness_overlap': score_a['severe_weakness_overlaps'],
                'a_resistance_coverage': score_a['resistance_coverage_score'],
                'a_role_balance': score_a['role_balance_score'],
                'a_speed_variance': score_a['speed_variance'],
                'a_bst_efficiency': score_a['average_bst_efficiency'],
                'b_weakness_overlap': score_b['severe_weakness_overlaps'],
                'b_resistance_coverage': score_b['resistance_coverage_score'],
                'b_role_balance': score_b['role_balance_score'],
                'b_speed_variance': score_b['speed_variance'],
                'b_bst_efficiency': score_b['average_bst_efficiency'],
                'team_a_wins': label
            }
            dataset.append(match_data)
            
        df = pd.DataFrame(dataset)
        # DROP NaNs to ensure the model can train
        df = df.dropna()
        
        filepath = os.path.join(self.synthetic_dir, "simulated_matchups.csv")
        df.to_csv(filepath, index=False)
        return df

    def train_model(self, df):
        if len(df) < 10:
            print("Error: Not enough data to train.")
            return None

        print("Training Random Forest Win Predictor...")
        X = df.drop('team_a_wins', axis=1)
        y = df['team_a_wins']
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        self.model.fit(X_train, y_train)
        preds = self.model.predict(X_test)
        
        print("\n--- Model Performance ---")
        print(f"ROC-AUC Score: {roc_auc_score(y_test, self.model.predict_proba(X_test)[:, 1]):.3f}")
        print(classification_report(y_test, preds))
        
        with open(os.path.join(self.models_dir, 'win_predictor_rf.pkl'), 'wb') as f:
            pickle.dump(self.model, f)
            
        print(f"Model saved to {self.models_dir}/win_predictor_rf.pkl")
        return X_train