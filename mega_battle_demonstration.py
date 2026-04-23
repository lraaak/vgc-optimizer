import pandas as pd
import json
import random
import sys
import os

# Ensure src is in the path for imports
sys.path.append(os.path.abspath('src'))

from battle_engine import BattlePokemon, BattleState, TurnEngine
from ai_agent import SmartVGCAgent
from full_simulator import FullGameSimulator

def run_mega_battle():
    # 1. LOAD DATA
    df_pokemon = pd.read_csv('data/processed/clustered_pokemon_data.csv').set_index('name', drop=False)
    df_moves = pd.read_csv('data/raw/showdown_moves.csv').set_index('name', drop=False)
    with open('data/raw/type_chart.json', 'r') as f:
        type_chart = json.load(f)

    def get_moves(*names):
        return [df_moves.loc[n].to_dict() for n in names]

    # 2. SETUP TEAMS
    # Team A: Hyper Offense
    urshifu = BattlePokemon('Urshifu-RS', df_pokemon.loc['urshifu-rapid-strike'], 
                            get_moves('Surging Strikes', 'Close Combat'), 
                            'Unseen Fist', item='Choice Band')
    tornadus = BattlePokemon('Tornadus', df_pokemon.loc['tornadus-incarnate'], 
                             get_moves('Tailwind', 'Bleakwind Storm', 'Encore'), 
                             'Prankster', item='Mental Herb')
    incineroar = BattlePokemon('Incineroar', df_pokemon.loc['incineroar'], 
                               get_moves('Fake Out', 'Flare Blitz', 'Knock Off'), 
                               'Intimidate', item='Sitrus Berry')
    flutter_mane = BattlePokemon('Flutter Mane', df_pokemon.loc['flutter-mane'], 
                                 get_moves('Moonblast', 'Shadow Ball'), 
                                 'Protosynthesis', item='Focus Sash')

    # Team B: Rain Core
    pelipper = BattlePokemon('Pelipper', df_pokemon.loc['pelipper'], 
                             get_moves('Hurricane', 'Weather Ball', 'Protect'), 
                             'Drizzle', item='Focus Sash')
    basculegion = BattlePokemon('Basculegion', df_pokemon.loc['basculegion-female'], 
                                get_moves('Wave Crash', 'Last Respects'), 
                                'Swift Swim', item='Life Orb')
    amoonguss = BattlePokemon('Amoonguss', df_pokemon.loc['amoonguss'], 
                              get_moves('Spore', 'Pollen Puff', 'Rage Powder'), 
                              'Regenerator', item='Rocky Helmet')
    archaludon = BattlePokemon('Archaludon', df_pokemon.loc['archaludon'], 
                               get_moves('Electro Shot', 'Flash Cannon'), 
                               'Stamina', item='Assault Vest')

    # 3. INITIALIZE STATE
    state = BattleState()
    state.team_a_active = [urshifu, tornadus]
    state.team_a_bench = [incineroar, flutter_mane]

    state.team_b_active = [pelipper, basculegion]
    state.team_b_bench = [amoonguss, archaludon]

    # 4. RUN SIMULATOR
    sim = FullGameSimulator(type_chart)
    agent_a = SmartVGCAgent(None) 
    agent_b = SmartVGCAgent(None)

    print("\n" + "="*50)
    print("      VGC MEGA-META ARCHITECT: BATTLE DEMO")
    print("="*50)
    print("TEAM A: Urshifu, Tornadus, Incineroar, Flutter Mane")
    print("TEAM B: Pelipper, Basculegion, Amoonguss, Archaludon")
    print("-" * 50)

    winner = sim.play_match(state, agent_a, agent_b, verbose=True)

    print("\n" + "="*50)
    print(f"BATTLE OVER! Winner: TEAM {winner}")
    print("="*50)

if __name__ == "__main__":
    run_mega_battle()
