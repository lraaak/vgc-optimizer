from full_simulator import FullGameSimulator
from ai_agent import SmartVGCAgent
from battle_engine import BattleState, TurnEngine

class MonteCarloSimulator:
    def __init__(self, type_chart):
        self.type_chart = type_chart
        self.sim = FullGameSimulator(type_chart)

    def run_simulations(self, team_a, team_b, num_simulations=100):
        team_a_wins = 0
        team_b_wins = 0
        timeouts = 0

        for i in range(num_simulations):
            # 1. Reset all Pokemon to max HP, clear stats/status
            for p in team_a + team_b:
                p.reset()

            # 2. Re-initialize the Battle State with fresh active/bench splits
            # Assuming team structure is 4 Pokemon: first 2 are active, last 2 are bench
            state = BattleState()
            state.team_a_active = team_a[:2]
            state.team_a_bench = team_a[2:]
            state.team_b_active = team_b[:2]
            state.team_b_bench = team_b[2:]

            # 3. Initialize Agents
            agent_a = SmartVGCAgent(None)
            agent_b = SmartVGCAgent(None)
            
            # The simulator creates the TurnEngine internally, but the agents need it too.
            # play_match creates it, so we must inject it.
            engine = TurnEngine(state, self.type_chart)
            agent_a.engine = engine
            agent_b.engine = engine

            # 4. Play the match (silently)
            winner = self.sim.play_match(state, agent_a, agent_b, verbose=False)

            # 5. Tally results
            if winner == 1:
                team_a_wins += 1
            elif winner == 0:
                team_b_wins += 1
            else:
                timeouts += 1

        win_rate = (team_a_wins / num_simulations) * 100
        
        return {
            "team_a_wins": team_a_wins,
            "team_b_wins": team_b_wins,
            "timeouts": timeouts,
            "team_a_win_rate": win_rate,
            "total_matches": num_simulations
        }
