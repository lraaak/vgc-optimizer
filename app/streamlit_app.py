import streamlit as st
import pandas as pd
import sys
import os

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
    scorer = TeamSynergyScorer(data_path=data_path)
    simulator = MonteCarloSimulator(data_path=data_path)
    recommender = CounterRecommender(data_path=data_path)
    return scorer, simulator, recommender

try:
    scorer, simulator, recommender = load_models()
    pokemon_list = sorted(scorer.df['name'].tolist())
except Exception as e:
    st.error(f"Error loading models or data: {e}")
    st.stop()

# Layout
st.sidebar.header("Input Team Core")
team = []
# Ensure default selections don't overlap if possible
default_indices = [pokemon_list.index(p) if p in pokemon_list else i for i, p in enumerate(['charizard', 'venusaur', 'blastoise', 'pikachu'])]

for i in range(4):
    idx = default_indices[i] if i < len(default_indices) else 0
    p = st.sidebar.selectbox(f"Pokémon {i+1}", pokemon_list, index=idx)
    team.append(p)

if st.sidebar.button("Analyze Team", type="primary"):
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
    st.write("Consider adding these Pokémon to shore up your weaknesses against the meta threats.")
    with st.spinner("Finding optimal counters..."):
        recs = recommender.recommend_team_counters(team, top_n=5, weaknesses=weaknesses)
        if recs:
            rec_df = pd.DataFrame(recs)
            rec_df['name'] = rec_df['name'].str.capitalize()
            rec_df['targets'] = rec_df['targets'].str.capitalize()
            rec_df = rec_df.rename(columns={
                'name': 'Pokémon',
                'role': 'Assigned Role',
                'counter_score': 'Similarity Score',
                'targets': 'Primary Target'
            })
            st.dataframe(rec_df, width='stretch', hide_index=True)
        else:
            st.info("No clear counters found. Your team might already cover the main threats!")
