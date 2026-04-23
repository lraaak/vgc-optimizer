class SmartVGCAgent:
    def __init__(self, engine):
        self.engine = engine

    def get_best_action(self, user, opponents):
        best_score = -1
        best_action = None

        if not user.moves:
            return None

        valid_opponents = [p for p in opponents if not p.is_fainted]
        if not valid_opponents:
            return None

        for move in user.moves:
            if move.get('category') == 'Status':
                if move.get('name') == 'Protect':
                    score = self._evaluate_protect(user, valid_opponents)
                    if score > best_score:
                        best_score = score
                        best_action = {'user': user, 'targets': [], 'move': move}
                continue

            if move.get('target') in ['allAdjacentFoes', 'allAdjacent']:
                score = sum([self._evaluate(user, t, move) for t in valid_opponents])
                if len(valid_opponents) > 1:
                    score *= 0.75 
                
                if score > best_score:
                    best_score = score
                    best_action = {'user': user, 'targets': valid_opponents, 'move': move}
            else:
                for target in valid_opponents:
                    score = self._evaluate(user, target, move)
                    if score > best_score:
                        best_score = score
                        best_action = {'user': user, 'targets': [target], 'move': move}

        return best_action

    def _get_max_incoming_damage(self, target, user):
        max_dmg = 0
        for move in target.moves:
            if move.get('category') != 'Status':
                dmg = self.engine.calculate_vgc_damage(target, user, move)
                if dmg > max_dmg:
                    max_dmg = dmg
        return max_dmg

    def _evaluate(self, user, target, move):
        est_dmg = self.engine.calculate_vgc_damage(user, target, move)
        ko_bonus = 2.0 if est_dmg >= target.current_hp else 1.0
        base_score = (est_dmg / max(1, target.current_hp)) * ko_bonus

        user_speed = user.get_stat('speed')
        target_speed = target.get_stat('speed')
        move_priority = move.get('priority', 0)

        if move_priority <= 0 and target_speed > user_speed:
            max_incoming = self._get_max_incoming_damage(target, user)
            
            if max_incoming >= user.current_hp:
                return 0.01 

        return base_score

    def _evaluate_protect(self, user, opponents):
        # 1/3 decay chance for consecutive protects
        success_rate = 1.0 / (3 ** user.protect_counter)
        max_incoming = 0
        
        for opp in opponents:
            if opp.get_stat('speed') > user.get_stat('speed'):
                incoming = self._get_max_incoming_damage(opp, user)
                if incoming > max_incoming:
                    max_incoming = incoming
        
        # If a faster opponent threatens a KO, Protect has immense value
        if max_incoming >= user.current_hp:
            return 5.0 * success_rate
            
        # Default low score if no immediate fast threat
        return 0.5 * success_rate