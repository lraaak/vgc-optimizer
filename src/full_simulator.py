from battle_engine import TurnEngine

class FullGameSimulator:
    def __init__(self, type_chart):
        self.type_chart = type_chart

    def send_out_replacements(self, state, verbose=True):
        # 1. Handle Fainted Replacements
        for i in range(len(state.team_a_active)):
            if state.team_a_active[i].is_fainted and state.team_a_bench:
                state.team_a_active[i] = state.team_a_bench.pop(0)
                if verbose: print(f"[Switch] Team A sent out {state.team_a_active[i].name}!")
            
            # Handle Pivoting (U-turn / Parting Shot)
            elif state.team_a_active[i].needs_pivot and state.team_a_bench:
                pivoted_poke = state.team_a_active[i]
                pivoted_poke.needs_pivot = False # Reset flag
                state.team_a_active[i] = state.team_a_bench.pop(0)
                state.team_a_bench.append(pivoted_poke) # Move to back of bench
                if verbose: print(f"[Pivot] {pivoted_poke.name} switched out for {state.team_a_active[i].name}!")

        state.team_a_active = [p for p in state.team_a_active if not p.is_fainted]

        for i in range(len(state.team_b_active)):
            if state.team_b_active[i].is_fainted and state.team_b_bench:
                state.team_b_active[i] = state.team_b_bench.pop(0)
                if verbose: print(f"[Switch] Team B sent out {state.team_b_active[i].name}!")
            
            # Handle Pivoting
            elif state.team_b_active[i].needs_pivot and state.team_b_bench:
                pivoted_poke = state.team_b_active[i]
                pivoted_poke.needs_pivot = False # Reset flag
                state.team_b_active[i] = state.team_b_bench.pop(0)
                state.team_b_bench.append(pivoted_poke) # Move to back of bench
                if verbose: print(f"[Pivot] {pivoted_poke.name} switched out for {state.team_b_active[i].name}!")
                
        state.team_b_active = [p for p in state.team_b_active if not p.is_fainted]

    def play_match(self, state, agent_a, agent_b, max_turns=15, verbose=True):
        engine = TurnEngine(state, self.type_chart)
        # Link agents to the engine automatically so they can see weather/terrain
        agent_a.engine = engine
        agent_b.engine = engine
        
        engine.trigger_entry_abilities(verbose=verbose)

        for turn in range(1, max_turns + 1):
            if verbose: print(f"\n=== TURN {turn} ===")

            actions = []
            for p in state.team_a_active:
                act = agent_a.get_best_action(p, state.team_b_active)
                if act: actions.append(act)

            for p in state.team_b_active:
                act = agent_b.get_best_action(p, state.team_a_active)
                if act: actions.append(act)

            if not actions:
                break

            logs = engine.execute_turn(actions)
            if verbose:
                for log in logs: 
                    print(log)

            self.send_out_replacements(state, verbose=verbose)
            engine.trigger_entry_abilities(verbose=verbose)

            if not state.team_a_active and not state.team_a_bench:
                if verbose: print("\n*** TEAM B WINS ***")
                return 0 
            elif not state.team_b_active and not state.team_b_bench:
                if verbose: print("\n*** TEAM A WINS ***")
                return 1 

        if verbose: print("\n*** MATCH TIMEOUT ***")
        return 0.5