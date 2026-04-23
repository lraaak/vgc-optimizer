import pandas as pd
import numpy as np
import os
import json
import random

ABILITY_MODIFIERS = {
    'Swift Swim':  {'stat': 'speed', 'mult': 2.0, 'weather': 'Rain'},
    'Chlorophyll': {'stat': 'speed', 'mult': 2.0, 'weather': 'Sun'},
    'Sand Rush':   {'stat': 'speed', 'mult': 2.0, 'weather': 'Sandstorm'},
    'Slush Rush':  {'stat': 'speed', 'mult': 2.0, 'weather': 'Snow'},
    'Protosynthesis': {'stat': 'highest', 'mult': 1.3, 'weather': 'Sun'},
    'Quark Drive':    {'stat': 'highest', 'mult': 1.3, 'terrain': 'Electric'},
    'Guts':        {'stat': 'attack', 'mult': 1.5, 'statused': True}
}

class BattlePokemon:
    # ITEM_MODIFIERS: maps item name -> which stat to multiply and by how much
    ITEM_STAT_MODIFIERS = {
        'Choice Band':   {'stat': 'attack',  'mult': 1.5},
        'Choice Specs':  {'stat': 'sp_atk',  'mult': 1.5},
        'Choice Scarf':  {'stat': 'speed',   'mult': 1.5},
        'Assault Vest':  {'stat': 'sp_def',  'mult': 1.5},
        'Eviolite':      {'stat': 'defense', 'mult': 1.5},  # also sp_def but simplified
    }

    def __init__(self, name, pokemon_row, moves, ability, item=None):
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
        self.item = item  # Held Item (e.g. 'Choice Scarf', 'Life Orb')
        self.status = None  # e.g., 'BRN', 'PAR', 'SLP'
        self.stat_stages = {
            'attack': 0, 'defense': 0, 'sp_atk': 0, 
            'sp_def': 0, 'speed': 0
        }
        self.is_fainted = False
        self.protect_counter = 0
        self.ability_activated = False
        self.choice_lock = None  # Tracks the move name if holding a Choice item
        self.last_move = None    # Tracks the last move used for Encore
        self.encore_turns = 0    # Remaining turns of Encore lock
        self.needs_pivot = False 

    def reset(self):
        self.current_hp = self.max_hp
        self.status = None
        self.stat_stages = {
            'attack': 0, 'defense': 0, 'sp_atk': 0, 
            'sp_def': 0, 'speed': 0
        }
        self.is_fainted = False
        self.protect_counter = 0
        self.ability_activated = False
        self.choice_lock = None  # Reset Choice Lock on switch-out/reset
        self.last_move = None
        self.encore_turns = 0
        # Note: item is NOT consumed on reset for MVP (single-use items not tracked)

    def calculate_max_hp(self):
        # VGC Level 50 formula (assuming generic 252 HP EVs for MVP bulk)
        return int((2 * self.base_stats['hp'] + 31 + (252/4)) * 50 / 100) + 50 + 10

    def get_stat(self, stat_name, state=None):
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
            
        # Apply Centralized Ability Logic
        if state and self.ability in ABILITY_MODIFIERS:
            mod = ABILITY_MODIFIERS[self.ability]
            condition_met = False
            
            if 'weather' in mod and state.weather == mod['weather']: condition_met = True
            if 'terrain' in mod and state.terrain == mod['terrain']: condition_met = True
            if 'statused' in mod and self.status is not None: condition_met = True
            
            if condition_met:
                target_stat = mod['stat']
                if target_stat == 'highest':
                    stats = {s: self.base_stats[s] for s in ['attack', 'defense', 'sp_atk', 'sp_def', 'speed']}
                    target_stat = max(stats, key=stats.get)
                
                if target_stat == stat_name:
                    mult = 1.5 if target_stat == 'speed' and mod['stat'] == 'highest' else mod['mult']
                    actual_stat = int(actual_stat * mult)

        # Apply Item Stat Modifiers (Choice Band/Specs/Scarf, Assault Vest)
        if self.item and self.item in BattlePokemon.ITEM_STAT_MODIFIERS:
            item_mod = BattlePokemon.ITEM_STAT_MODIFIERS[self.item]
            if item_mod['stat'] == stat_name:
                actual_stat = int(actual_stat * item_mod['mult'])
            
        return actual_stat

    def change_stage(self, stat_name, amount):
        current = self.stat_stages[stat_name]
        self.stat_stages[stat_name] = max(-6, min(6, current + amount))

        # White Herb: restores lowered stats once
        if self.item == 'White Herb' and amount < 0:
            # Check if any stat is still negative after applying the drop
            if any(v < 0 for v in self.stat_stages.values()):
                self.stat_stages = {k: max(0, v) for k, v in self.stat_stages.items()}
                self.consume_item()
                # Caller is responsible for logging this - we return a signal
                return 'white_herb'
        return None
    def consume_item(self):
        """Consume a single-use item, clearing the slot."""
        self.item = None

    def apply_damage(self, amount):
        # Focus Sash: survive a KO at full HP
        if self.item == 'Focus Sash' and self.current_hp == self.max_hp:
            if int(amount) >= self.current_hp:
                self.current_hp = 1
                self.consume_item()
                return  # Sash triggered, skip normal damage
        
        self.current_hp = max(0, self.current_hp - int(amount))
        if self.current_hp == 0:
            self.is_fainted = True

    def check_reactive_items(self):
        """Check and trigger single-use items that react to HP/status. Returns a log message or None."""
        if not self.item or self.is_fainted:
            return None
        
        # Sitrus Berry: heal 25% max HP when below 50%
        if self.item == 'Sitrus Berry' and self.current_hp <= self.max_hp * 0.5:
            heal = max(1, int(self.max_hp * 0.25))
            self.current_hp = min(self.max_hp, self.current_hp + heal)
            self.consume_item()
            return f"{self.name} ate its Sitrus Berry! Restored {heal} HP. ({self.current_hp}/{self.max_hp} HP)"
        
        # Lum Berry: cures any status condition
        if self.item == 'Lum Berry' and self.status is not None:
            old_status = self.status
            self.status = None
            self.consume_item()
            return f"{self.name} ate its Lum Berry and cured its {old_status}!"
        
        return None


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
        
        # Redirection State (reset every turn)
        self.redirection_target_a = None
        self.redirection_target_b = None
    def get_turn_order(self):
        # Gathers all active pokemon and sorts them by their actual state-calculated speed
        all_active = []
        for p in self.team_a_active:
            if not p.is_fainted: all_active.append((p, 'A'))
        for p in self.team_b_active:
            if not p.is_fainted: all_active.append((p, 'B'))
            
        # If Trick Room is active, reverse the speed sorting
        reverse_sort = self.trick_room_turns == 0
        
        all_active.sort(key=lambda x: x[0].get_stat('speed', self), reverse=reverse_sort)
        return all_active

class TurnEngine:
    def __init__(self, state, type_chart):
        self.state = state
        self.type_chart = type_chart

    def _get_effective_priority(self, action):
        user = action['user']
        move = action['move']
        base_priority = move.get('priority', 0)
        
        # Dynamic Priorities
        if user.ability == 'Prankster' and move.get('category') == 'Status':
            base_priority += 1
        elif user.ability == 'Gale Wings' and move.get('type') == 'flying' and user.current_hp == user.max_hp:
            base_priority += 1
        elif move.get('name') == 'Grassy Glide' and self.state.terrain == 'Grassy':
            base_priority += 1
            
        return base_priority

    def execute_turn(self, actions):
        # 1. Calculate turn order based on Effective Priority -> Speed -> Random Tiebreaker
        # In Trick Room, Speed order is reversed (within the same priority bracket)
        is_tr = self.state.trick_room_turns > 0
        
        actions.sort(
            key=lambda x: (
                self._get_effective_priority(x),
                -x['user'].get_stat('speed', self.state) if is_tr else x['user'].get_stat('speed', self.state),
                random.random() # Ultimate tie-breaker
            ), 
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
            elif move.get('name') in ['Rage Powder', 'Follow Me']:
                if user in self.state.team_a_active:
                    self.state.redirection_target_a = user
                else:
                    self.state.redirection_target_b = user
                turn_log.append(f"{user.name} is directing attention towards itself!")
            else:
                user.protect_counter = 0 # Reset if they used a different move

        # Step 2: Process Attacks
        for action in actions:
            user = action['user']
            targets = action.get('targets', []) 
            move = action['move']

            if user.is_fainted or move.get('name') == 'Protect':
                continue

            # --- STATUS PREVENTION CHECK ---
            if user.status == 'SLP':
                # Simple wake-up check: 33% chance each turn
                if random.random() < 0.33:
                    user.status = None
                    turn_log.append(f"{user.name} woke up!")
                else:
                    turn_log.append(f"{user.name} is fast asleep...")
                    continue
            
            if user.status == 'FRZ':
                # Thaw check: 20% chance
                if random.random() < 0.20:
                    user.status = None
                    turn_log.append(f"{user.name} thawed out!")
                else:
                    turn_log.append(f"{user.name} is frozen solid!")
                    continue
            
            if user.status == 'PAR' and random.random() < 0.25:
                turn_log.append(f"{user.name} is paralyzed! It can't move!")
                continue

            # Encore / Choice Lock Enforcement
            if user.encore_turns > 0 and user.last_move:
                move = user.last_move  # Force last move
                turn_log.append(f"{user.name} is locked by Encore!")

            if user.item in ['Choice Band', 'Choice Specs', 'Choice Scarf'] and user.choice_lock is None:
                user.choice_lock = move.get('name')
            
            # Record last move for future Encores
            user.last_move = move

            # Redirection Check
            if move.get('target') not in ['allAdjacentFoes', 'allAdjacent']:
                # If attacker is Team A, check if Team B has a redirector active
                redirector = self.state.redirection_target_b if user in self.state.team_a_active else self.state.redirection_target_a
                if redirector and not redirector.is_fainted:
                    # Redirect single-target moves to the redirector
                    targets = [redirector]
                    turn_log.append(f"(Redirected to {redirector.name})")

            if move.get('category') != 'Status':
                spread_mod = 0.75 if len(targets) > 1 else 1.0
                
                for target in targets:
                    if target.is_fainted:
                        continue
                        
                    # Check for Priority Blocking (Armor Tail, Psychic Terrain, etc.)
                    if self._get_effective_priority(action) > 0:
                        # 1. Blocking Abilities (Armor Tail / Dazzling)
                        opponents = self.state.team_b_active if action['user'] in self.state.team_a_active else self.state.team_a_active
                        if any(opp.ability in ['Armor Tail', 'Dazzling', 'Queenly Majesty'] for opp in opponents):
                            turn_log.append(f"{user.name} used {move.get('name')}... but it was blocked by Armor Tail!")
                            continue
                            
                        # 2. Psychic Terrain (Blocks priority against grounded targets)
                        if self.state.terrain == 'Psychic':
                            # Simplified grounded check for MVP
                            turn_log.append(f"{user.name} used {move.get('name')}... but Psychic Terrain protected the target!")
                            continue

                    if target in protected_targets:
                        turn_log.append(f"{user.name} used {move.get('name')}... but {target.name} protected itself!")
                        continue
                        
                    dmg = self.calculate_vgc_damage(user, target, move)
                    dmg = int(dmg * spread_mod) 
                    target.apply_damage(dmg)
                    
                    turn_log.append(f"{user.name} used {move.get('name', 'a move')}! Dealt {dmg} to {target.name}. ({target.current_hp}/{target.max_hp} HP)")
                    
                    # Focus Sash: if target survived at 1 HP, log it
                    if not target.is_fainted and target.current_hp == 1:
                        turn_log.append(f"{target.name} held on with its Focus Sash!")

                    # Life Orb recoil: 10% of user's max HP after each hit
                    if user.item == 'Life Orb' and not user.is_fainted:
                        recoil = max(1, int(user.max_hp * 0.10))
                        user.apply_damage(recoil)
                        turn_log.append(f"{user.name} is hurt by its Life Orb! ({user.current_hp}/{user.max_hp} HP)")
                    
                    # Rocky Helmet: contact moves deal 1/6 recoil to the attacker
                    CONTACT_MOVES = {'physical'}  # Simplified: all physical moves are contact
                    if target.item == 'Rocky Helmet' and move.get('category', '').lower() in CONTACT_MOVES and not user.is_fainted:
                        helmet_dmg = max(1, int(user.max_hp / 6))
                        user.apply_damage(helmet_dmg)
                        turn_log.append(f"{user.name} was hurt by {target.name}'s Rocky Helmet! ({user.current_hp}/{user.max_hp} HP)")

                    # --- NEW: AUTOMATED SHOWDOWN FLAGS ---
                    # Handle Recoil (e.g. Flare Blitz)
                    recoil_data = move.get('recoil')
                    if recoil_data and recoil_data != '[0, 1]':
                        try:
                            import json
                            num, den = json.loads(recoil_data) if isinstance(recoil_data, str) else recoil_data
                            if num > 0:
                                rec_dmg = max(1, int(dmg * num / den))
                                user.apply_damage(rec_dmg)
                                turn_log.append(f"{user.name} took recoil damage! ({user.current_hp}/{user.max_hp} HP)")
                        except: pass

                    # Handle Drain (e.g. Giga Drain)
                    drain_data = move.get('drain')
                    if drain_data and drain_data != '[0, 1]':
                        try:
                            import json
                            num, den = json.loads(drain_data) if isinstance(drain_data, str) else drain_data
                            if num > 0:
                                heal = max(1, int(dmg * num / den))
                                user.current_hp = min(user.max_hp, user.current_hp + heal)
                                turn_log.append(f"{user.name} regained health! (+{heal} HP)")
                        except: pass

                    # Trigger reactive items for the target (Sitrus Berry, Lum Berry)
                    berry_log = target.check_reactive_items()
                    if berry_log:
                        turn_log.append(berry_log)

                    if not target.is_fainted:
                        # Process Generic Secondary Effects
                        secondary_str = move.get('secondary')
                        if secondary_str and secondary_str != '{}' and secondary_str != 'null':
                            try:
                                import json
                                secondary = json.loads(secondary_str) if isinstance(secondary_str, str) else secondary_str
                                if 'boosts' in secondary:
                                    chance = secondary.get('chance', 100)
                                    if random.random() * 100 <= chance:
                                        stat_map = {'spe': 'speed', 'spa': 'sp_atk', 'atk': 'attack', 'def': 'defense', 'spd': 'sp_def'}
                                        for stat, amount in secondary['boosts'].items():
                                            stat_name = stat_map.get(stat, stat)
                                            target.change_stage(stat_name, amount)
                                            direction = "fell" if amount < 0 else "rose"
                                            turn_log.append(f"{target.name}'s {stat_name.replace('_', ' ').title()} {direction}!")
                            except Exception:
                                pass
                                
                        # Process Volatile Status
                        if move.get('volatileStatus') == 'flinch':
                            # In MVP, we just log the flinch for damage moves that guarantee it
                            turn_log.append(f"{target.name} flinched!")

                # Process Self-Effects (e.g. Close Combat drops)
                if not user.is_fainted:
                    self_str = move.get('self')
                    if self_str and self_str != '{}' and self_str != 'null':
                        try:
                            import json
                            self_eff = json.loads(self_str) if isinstance(self_str, str) else self_str
                            if 'boosts' in self_eff:
                                stat_map = {'spe': 'speed', 'spa': 'sp_atk', 'atk': 'attack', 'def': 'defense', 'spd': 'sp_def'}
                                for stat, amount in self_eff['boosts'].items():
                                    stat_name = stat_map.get(stat, stat)
                                    user.change_stage(stat_name, amount)
                                    direction = "fell" if amount < 0 else "rose"
                                    turn_log.append(f"{user.name}'s {stat_name.replace('_', ' ').title()} {direction}!")
                        except Exception:
                            pass
                                
                    # Handle Self-Switch (Pivot moves like Parting Shot / U-turn)
                    if move.get('selfSwitch') and not user.is_fainted:
                        turn_log.append(f"{user.name} is pivoting out!")
                        # In the simulator, this will trigger a forced switch call
                        user.needs_pivot = True
            else:
                # --- STATUS MOVE PROCESSING ---
                for target in targets:
                    if target.is_fainted: continue
                    
                    if target in protected_targets:
                        turn_log.append(f"{user.name} used {move.get('name')}... but {target.name} protected itself!")
                        continue
                        
                    # Handle Encore
                    if move.get('name') == 'Encore':
                        if target.last_move:
                            target.encore_turns = 3
                            turn_log.append(f"{target.name} was encored into {target.last_move.get('name')}!")
                        else:
                            turn_log.append(f"But it failed!")
                            
                    # Handle Status Application (e.g., Spore, Thunder Wave)
                    status_to_apply = move.get('status')
                    if status_to_apply and target.status is None:
                        target.status = status_to_apply.upper()
                        turn_log.append(f"{target.name} was {target.status}ed!")

        # End of Turn: Reset redirection and decrement Encore
        self.state.redirection_target_a = None
        self.state.redirection_target_b = None
        
        for p in self.state.team_a_active + self.state.team_b_active:
            if p.encore_turns > 0:
                p.encore_turns -= 1
                
            # Apply Status Damage (Burn / Poison)
            if not p.is_fainted:
                if p.status == 'BRN':
                    dmg = max(1, int(p.max_hp / 16))
                    p.apply_damage(dmg)
                    turn_log.append(f"{p.name} was hurt by its burn! ({p.current_hp}/{p.max_hp} HP)")
                elif p.status in ['PSN', 'TOX']:
                    dmg = max(1, int(p.max_hp / 8)) # Simplified Toxic for MVP
                    p.apply_damage(dmg)
                    turn_log.append(f"{p.name} was hurt by poison! ({p.current_hp}/{p.max_hp} HP)")
        
        return turn_log
    
    # ADD THIS NEW METHOD to TurnEngine
    def trigger_entry_abilities(self, verbose=True):
        all_active = self.state.team_a_active + self.state.team_b_active
        # Sort by speed descending so fastest triggers first
        all_active.sort(key=lambda p: p.get_stat('speed', self.state), reverse=True)
        
        for p in all_active:
            if p.is_fainted or p.ability_activated: continue
            
            p.ability_activated = True
            # Weather / Terrain Setters
            if p.ability == 'Drought':
                self.state.weather = 'Sun'
                if verbose: print(f"[Ability] {p.name}'s Drought whipped up the sunlight!")
            elif p.ability == 'Drizzle':
                self.state.weather = 'Rain'
                if verbose: print(f"[Ability] {p.name}'s Drizzle made it rain!")
            elif p.ability == 'Grassy Surge':
                self.state.terrain = 'Grassy'
                if verbose: print(f"[Ability] {p.name}'s Grassy Surge turned the ground to grass!")
                
            # Stat Modifiers
            elif p.ability == 'Intimidate':
                opponents = self.state.team_b_active if p in self.state.team_a_active else self.state.team_a_active
                if verbose: print(f"[Ability] {p.name}'s Intimidate cuts opposing attack!")
                for opp in opponents:
                    if not opp.is_fainted:
                        opp.change_stage('attack', -1)

    # UPDATE your existing calculate_vgc_damage method to include Weather
    def calculate_vgc_damage(self, attacker, defender, move):
        if move.get('category') == 'Physical':
            a = attacker.get_stat('attack', self.state)
            d = defender.get_stat('defense', self.state)
        elif move.get('category') == 'Special':
            a = attacker.get_stat('sp_atk', self.state)
            d = defender.get_stat('sp_def', self.state)
        else:
            return 0 

        base_dmg = ((22 * move.get('base_power', 0) * a / d) / 50) + 2

        stab = 1.5 if move.get('type') in attacker.types else 1.0

        type_mod = 1.0
        type_mod *= self.type_chart.get(move.get('type'), {}).get(defender.types[0], 1.0)
        if len(defender.types) > 1:
            type_mod *= self.type_chart.get(move.get('type'), {}).get(defender.types[1], 1.0)

        # Weather Modifiers
        weather_mod = 1.0
        if self.state.weather == 'Sun':
            if move.get('type') == 'fire': weather_mod = 1.5
            elif move.get('type') == 'water': weather_mod = 0.5
        elif self.state.weather == 'Rain':
            if move.get('type') == 'water': weather_mod = 1.5
            elif move.get('type') == 'fire': weather_mod = 0.5

        # Item Damage Modifiers
        # Maps held item -> (move type filter or None, multiplier)
        ITEM_DAMAGE_BOOSTS = {
            'Life Orb':      (None,       1.3),
            'Mystic Water':  ('water',    1.2),
            'Charcoal':      ('fire',     1.2),
            'Miracle Seed':  ('grass',    1.2),
            'Magnet':        ('electric', 1.2),
            'Never-Melt Ice':('ice',      1.2),
            'Black Belt':    ('fighting', 1.2),
            'Twisted Spoon': ('psychic',  1.2),
            'Sharp Beak':    ('flying',   1.2),
            'Poison Barb':   ('poison',   1.2),
            'Soft Sand':     ('ground',   1.2),
            'Hard Stone':    ('rock',     1.2),
            'Silver Powder': ('bug',      1.2),
            'Spell Tag':     ('ghost',    1.2),
            'Dragon Fang':   ('dragon',   1.2),
            'Black Glasses': ('dark',     1.2),
            'Metal Coat':    ('steel',    1.2),
        }
        item_dmg_mod = 1.0
        if attacker.item and attacker.item in ITEM_DAMAGE_BOOSTS:
            type_filter, boost = ITEM_DAMAGE_BOOSTS[attacker.item]
            if type_filter is None or move.get('type') == type_filter:
                item_dmg_mod = boost

        rng = random.uniform(0.85, 1.0)
        final_dmg = int(base_dmg * stab * type_mod * weather_mod * item_dmg_mod * rng)
        
        return final_dmg