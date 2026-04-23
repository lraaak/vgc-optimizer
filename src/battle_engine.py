import pandas as pd
import numpy as np
import os
import json
import random

class BattlePokemon:
    def __init__(self, name, pokemon_row, moves, ability):
        self.name = name
        self.base_stats = pokemon_row[['hp', 'attack', 'defense', 'sp_atk', 'sp_def', 'speed']].to_dict()
        
        self.types = [pokemon_row['type_1']]
        if pd.notna(pokemon_row['type_2']):
            self.types.append(pokemon_row['type_2'])

        # State Variables
        self.current_hp = self.calculate_max_hp()
        self.max_hp = self.current_hp
        self.moves = moves  # List of Showdown move dicts
        self.ability = ability
        self.status = None  # e.g., 'BRN', 'PAR', 'SLP'
        self.stat_stages = {
            'attack': 0, 'defense': 0, 'sp_atk': 0, 
            'sp_def': 0, 'speed': 0
        }
        self.is_fainted = False
        self.protect_counter = 0
        self.ability_activated = False

    def calculate_max_hp(self):
        # VGC Level 50 formula (assuming generic 252 HP EVs for MVP bulk)
        return int((2 * self.base_stats['hp'] + 31 + (252/4)) * 50 / 100) + 50 + 10

    def get_stat(self, stat_name):
        if stat_name == 'hp': 
            return self.current_hp
            
        # VGC Level 50 standard stat formula
        base = int((2 * self.base_stats[stat_name] + 31 + (252/4)) * 50 / 100) + 5
        
        # Apply stat stages (-6 to +6)
        stage = self.stat_stages[stat_name]
        multiplier = max(2, 2 + stage) / max(2, 2 - stage)
        
        actual_stat = int(base * multiplier)
        
        # Apply status penalties (e.g., Burn cuts physical attack)
        if self.status == 'BRN' and stat_name == 'attack':
            actual_stat = int(actual_stat * 0.5)
        if self.status == 'PAR' and stat_name == 'speed':
            actual_stat = int(actual_stat * 0.5)
            
        return actual_stat

    def change_stage(self, stat_name, amount):
        current = self.stat_stages[stat_name]
        self.stat_stages[stat_name] = max(-6, min(6, current + amount))

    def apply_damage(self, amount):
        self.current_hp = max(0, self.current_hp - int(amount))
        if self.current_hp == 0:
            self.is_fainted = True


class BattleState:
    def __init__(self):
        # Field Mechanics
        self.weather = 'none' 
        self.weather_turns = 0
        self.terrain = 'none'
        self.terrain_turns = 0
        self.trick_room_turns = 0
        
        # Team Modifiers
        self.team_a_tailwind = 0
        self.team_b_tailwind = 0
        self.team_a_reflect = 0
        self.team_b_reflect = 0
        
        # Rosters (Doubles: 2 active, 2 benched)
        self.team_a_active = []
        self.team_b_active = []
        self.team_a_bench = []
        self.team_b_bench = []

    def get_turn_order(self):
        # Gathers all active pokemon and sorts them by their actual state-calculated speed
        all_active = []
        for p in self.team_a_active:
            if not p.is_fainted: all_active.append((p, 'A'))
        for p in self.team_b_active:
            if not p.is_fainted: all_active.append((p, 'B'))
            
        # If Trick Room is active, reverse the speed sorting
        reverse_sort = self.trick_room_turns == 0
        
        all_active.sort(key=lambda x: x[0].get_stat('speed'), reverse=reverse_sort)
        return all_active

class TurnEngine:
    def __init__(self, state, type_chart):
        self.state = state
        self.type_chart = type_chart

    def calculate_vgc_damage(self, attacker, defender, move):
        if move['category'] == 'Physical':
            a = attacker.get_stat('attack')
            d = defender.get_stat('defense')
        elif move['category'] == 'Special':
            a = attacker.get_stat('sp_atk')
            d = defender.get_stat('sp_def')
        else:
            return 0 

        base_dmg = ((22 * move['base_power'] * a / d) / 50) + 2

        stab = 1.5 if move['type'] in attacker.types else 1.0

        type_mod = 1.0
        type_mod *= self.type_chart.get(move['type'], {}).get(defender.types[0], 1.0)
        if len(defender.types) > 1:
            type_mod *= self.type_chart.get(move['type'], {}).get(defender.types[1], 1.0)

        rng = random.uniform(0.85, 1.0)
        return int(base_dmg * stab * type_mod * rng)

    def execute_turn(self, actions):
        actions.sort(
            key=lambda x: (x['move'].get('priority', 0), x['user'].get_stat('speed')), 
            reverse=True
        )

        turn_log = []
        protected_targets = set()

        # Step 1: Process Protects First
        for action in actions:
            user = action['user']
            move = action['move']
            if move.get('name') == 'Protect':
                success_rate = 1.0 / (3 ** user.protect_counter)
                if random.random() < success_rate:
                    protected_targets.add(user)
                    user.protect_counter += 1
                    turn_log.append(f"{user.name} protected itself!")
                else:
                    turn_log.append(f"{user.name}'s Protect failed!")
            else:
                user.protect_counter = 0 # Reset if they used a different move

        # Step 2: Process Attacks
        for action in actions:
            user = action['user']
            targets = action.get('targets', []) 
            move = action['move']

            if user.is_fainted or move.get('name') == 'Protect':
                continue

            if move.get('category') != 'Status':
                spread_mod = 0.75 if len(targets) > 1 else 1.0
                
                for target in targets:
                    if target.is_fainted:
                        continue
                        
                    if target in protected_targets:
                        turn_log.append(f"{user.name} used {move.get('name')}... but {target.name} protected itself!")
                        continue
                        
                    dmg = self.calculate_vgc_damage(user, target, move)
                    dmg = int(dmg * spread_mod) 
                    target.apply_damage(dmg)
                    
                    turn_log.append(f"{user.name} used {move.get('name', 'a move')}! Dealt {dmg} to {target.name}. ({target.current_hp}/{target.max_hp} HP)")
                    
                    if not target.is_fainted:
                        move_name = move.get('name', '')
                        if move_name in ['Icy Wind', 'Electroweb']:
                            target.change_stage('speed', -1)
                            turn_log.append(f"{target.name}'s Speed fell!")
                        elif move_name == 'Snarl':
                            target.change_stage('sp_atk', -1)
                            turn_log.append(f"{target.name}'s Sp. Atk fell!")

        return turn_log
    
    # ADD THIS NEW METHOD to TurnEngine
    def trigger_entry_abilities(self):
        all_active = self.state.team_a_active + self.state.team_b_active
        # Sort by speed descending so fastest triggers first
        all_active.sort(key=lambda p: p.get_stat('speed'), reverse=True)
        
        for p in all_active:
            if p.is_fainted or p.ability_activated: continue
            
            p.ability_activated = True
            # Weather / Terrain Setters
            if p.ability == 'Drought':
                self.state.weather = 'Sun'
                print(f"[Ability] {p.name}'s Drought whipped up the sunlight!")
            elif p.ability == 'Drizzle':
                self.state.weather = 'Rain'
                print(f"[Ability] {p.name}'s Drizzle made it rain!")
            elif p.ability == 'Grassy Surge':
                self.state.terrain = 'Grassy'
                print(f"[Ability] {p.name}'s Grassy Surge turned the ground to grass!")
                
            # Stat Modifiers
            elif p.ability == 'Intimidate':
                opponents = self.state.team_b_active if p in self.state.team_a_active else self.state.team_a_active
                print(f"[Ability] {p.name}'s Intimidate cuts opposing attack!")
                for opp in opponents:
                    if not opp.is_fainted:
                        opp.change_stage('attack', -1)

    # UPDATE your existing calculate_vgc_damage method to include Weather
    def calculate_vgc_damage(self, attacker, defender, move):
        if move.get('category') == 'Physical':
            a = attacker.get_stat('attack')
            d = defender.get_stat('defense')
        elif move.get('category') == 'Special':
            a = attacker.get_stat('sp_atk')
            d = defender.get_stat('sp_def')
        else:
            return 0 

        base_dmg = ((22 * move.get('base_power', 0) * a / d) / 50) + 2

        stab = 1.5 if move.get('type') in attacker.types else 1.0

        type_mod = 1.0
        type_mod *= self.type_chart.get(move.get('type'), {}).get(defender.types[0], 1.0)
        if len(defender.types) > 1:
            type_mod *= self.type_chart.get(move.get('type'), {}).get(defender.types[1], 1.0)

        # NEW: Weather Modifiers
        weather_mod = 1.0
        if self.state.weather == 'Sun':
            if move.get('type') == 'fire': weather_mod = 1.5
            elif move.get('type') == 'water': weather_mod = 0.5
        elif self.state.weather == 'Rain':
            if move.get('type') == 'water': weather_mod = 1.5
            elif move.get('type') == 'fire': weather_mod = 0.5

        rng = random.uniform(0.85, 1.0)
        return int(base_dmg * stab * type_mod * weather_mod * rng)