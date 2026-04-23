import streamlit as st
import pandas as pd
import sys
import os
import json

# Add src to path so we can import our modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from synergy_scorer import TeamSynergyScorer
from win_predictor import MonteCarloSimulator
from counter_recommender import CounterRecommender

# Set up page config
st.set_page_config(page_title="VGC Mega-Meta Architect", layout="wide", initial_sidebar_state="expanded")

st.title("VGC Mega-Meta Architect")
st.markdown("Evaluate your 4-Pokémon core, predict matchup momentum, and find counter recommendations.")

# Initialize models
@st.cache_resource
def load_models():
    data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/processed/clustered_pokemon_data.csv'))
    moves_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/raw/showdown_moves.csv'))
    type_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/raw/type_chart.json'))
    
    scorer = TeamSynergyScorer(data_path=data_path)
    recommender = CounterRecommender(data_path=data_path)
    
    df_moves = pd.read_csv(moves_path).set_index('name', drop=False)
    with open(type_path, 'r') as f:
        type_chart = json.load(f)
        
    return scorer, recommender, df_moves, type_chart

try:
    scorer, recommender, df_moves, type_chart = load_models()
    pokemon_list = sorted(scorer.df['name'].tolist())
except Exception as e:
    st.error(f"Error loading models or data: {e}")
    st.stop()

def get_suggested_moves(poke_name):
    # Heuristic for dropdown suggestions: STAB + common utility
    poke_data = scorer.df.set_index('name').loc[poke_name]
    p_types = [poke_data['type_1'], poke_data['type_2']]
    
    # Priority 1: STAB moves
    stab = df_moves[df_moves['type'].isin(p_types)].sort_values(by='base_power', ascending=False)
    # Priority 2: Protect and common utility
    utility = df_moves[df_moves['name'].isin(['Protect', 'Fake Out', 'Tailwind', 'Rage Powder', 'Spore', 'Follow Me', 'Encore'])]
    
    suggested = pd.concat([utility, stab]).drop_duplicates().head(12)
    return suggested['name'].tolist()

# Layout with Tabs
tab1, tab2 = st.tabs(["📊 Team Builder & Analysis", "⚔️ Battle Simulator"])

with tab1:
    # ... (Team Analysis code remains the same)
    st.sidebar.header("Input Team Core")
    team = []
    default_indices = [pokemon_list.index(p) if p in pokemon_list else i for i, p in enumerate(['charizard', 'venusaur', 'blastoise', 'pikachu'])]
    for i in range(4):
        idx = default_indices[i] if i < len(default_indices) else 0
        p = st.sidebar.selectbox(f"Pokémon {i+1}", pokemon_list, index=idx)
        team.append(p)
    
    if st.button("Analyze Team", type="primary"):
        # (Synergy scoring logic...)
        st.header("Team Analysis")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Synergy Scores")
            scores = scorer.score_team(team)
            st.metric("Severe Weakness Overlaps", scores['severe_weakness_overlaps'])
            st.metric("Resistance Coverage", f"{scores['resistance_coverage_score']:.2%}")
            st.metric("Role Balance", f"{scores['role_balance_score']:.2f}")
            st.metric("Speed Variance", f"{scores['speed_variance']:.2f}")
            st.metric("Average BST Efficiency", f"{scores['average_bst_efficiency']:.2f}")
        with col2:
            st.subheader("Meta Threat Matchups")
            with st.spinner("Simulating matchups against meta threats..."):
                weaknesses = recommender.identify_weaknesses(team)
                st.write("Predicted struggles against top threats:")
                for threat, loss_prob in weaknesses:
                    win_rate = 1 - loss_prob
                    st.warning(f"**{threat.capitalize()}** (Predicted Win Rate: {win_rate:.2%})")
        st.divider()
        st.subheader("Counter Recommendations")
        with st.spinner("Finding optimal counters..."):
            recs = recommender.recommend_team_counters(team, top_n=5, weaknesses=weaknesses)
            if recs:
                rec_df = pd.DataFrame(recs)
                rec_df['name'] = rec_df['name'].str.capitalize()
                rec_df['targets'] = rec_df['targets'].str.capitalize()
                st.dataframe(rec_df.rename(columns={'name':'Pokémon','role':'Role','counter_score':'Score','targets':'Target'}), hide_index=True)

with tab2:
    st.header("VGC Engine Simulator")
    st.write("Pick your Pokémon and customize their movesets for the simulation.")
    
    col_a, col_b = st.columns(2)
    team_a_data = []
    team_b_data = []

    with col_a:
        st.subheader("Team A")
        for i in range(4):
            label = "Lead" if i < 2 else "Bench"
            p = st.selectbox(f"Team A {label} {i%2+1}", pokemon_list, index=i, key=f"pa{i}")
            item = st.selectbox(f"Item A{i+1}", ["None", "Choice Band", "Choice Specs", "Choice Scarf", "Assault Vest", "Life Orb", "Focus Sash", "Sitrus Berry", "Rocky Helmet", "Mental Herb"], key=f"ia{i}")
            moves = st.multiselect(f"Moves for A{i+1}", df_moves['name'].tolist(), default=get_suggested_moves(p)[:4], max_selections=4, key=f"ma{i}")
            team_a_data.append({'name': p, 'item': item, 'moves': moves})
    
    with col_b:
        st.subheader("Team B")
        for i in range(4):
            label = "Lead" if i < 2 else "Bench"
            p = st.selectbox(f"Team B {label} {i%2+1}", pokemon_list, index=i+4, key=f"pb{i}")
            item = st.selectbox(f"Item B{i+1}", ["None", "Choice Band", "Choice Specs", "Choice Scarf", "Assault Vest", "Life Orb", "Focus Sash", "Sitrus Berry", "Rocky Helmet", "Mental Herb"], key=f"ib{i}")
            moves = st.multiselect(f"Moves for B{i+1}", df_moves['name'].tolist(), default=get_suggested_moves(p)[:4], max_selections=4, key=f"mb{i}")
            team_b_data.append({'name': p, 'item': item, 'moves': moves})
        
    if st.button("▶ Run Simulation", type="primary", use_container_width=True):
        st.divider()
        from battle_engine import BattlePokemon, BattleState, TurnEngine
        from full_simulator import FullGameSimulator
        from ai_agent import SmartVGCAgent
        
        def build_poke(data):
            # Convert move names to move dicts
            move_dicts = [df_moves.loc[m].to_dict() for m in data['moves']]
            # Ensure at least one move exists
            if not move_dicts:
                move_dicts = [df_moves.loc['Tackle'].to_dict()]
            return BattlePokemon(data['name'], scorer.df.set_index('name').loc[data['name']], move_dicts, 'None', item=None if data['item']=="None" else data['item'])

        with st.spinner("Simulating Battle..."):
            state = BattleState()
            state.team_a_active = [build_poke(team_a_data[0]), build_poke(team_a_data[1])]
            state.team_a_bench = [build_poke(team_a_data[2]), build_poke(team_a_data[3])]
            state.team_b_active = [build_poke(team_b_data[0]), build_poke(team_b_data[1])]
            state.team_b_bench = [build_poke(team_b_data[2]), build_poke(team_b_data[3])]
            
            sim = FullGameSimulator(type_chart)
            import io
            from contextlib import redirect_stdout
            f_out = io.StringIO()
            with redirect_stdout(f_out):
                winner = sim.play_match(state, SmartVGCAgent(None), SmartVGCAgent(None), verbose=True)
            battle_log = f_out.getvalue()
            
        if winner == 0:
            st.success(f"🏆 **Team A Wins!**")
        else:
            st.error(f"🏆 **Team B Wins!**")
            
        with st.expander("Show Detailed Battle Log", expanded=True):
            st.code(battle_log, language="markdown")
