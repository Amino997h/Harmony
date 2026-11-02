import random
from typing import Dict, List, Optional
from rules_engine import Card, evaluate_hand

class GameAI:
    @staticmethod
    def decide_betting_action(player, current_bet: int, max_cap: int) -> str:
        """
        Decides whether to 'HOLD' or 'RAISE' in betting phase.
        Respects chips limit and max_cap.
        """
        if current_bet + 100 > max_cap:
            return "HOLD"
        if player.chips < 100:
            return "HOLD"

        # AI personality / strategic random
        # 60% chance to raise if plenty of chips
        if player.chips >= 300 and random.random() < 0.55:
            return "RAISE"
        return "HOLD"

    @staticmethod
    def decide_play_action(player, game_state) -> Dict:
        """
        Decide AI turn action:
        Returns dict with action type:
        - {"type": "PASS"}
        - {"type": "DISCARD_DRAW", "card_index": int}
        - {"type": "STEAL", "target_id": int}
        - {"type": "BLIND_SWAP", "target_id": int}
        - {"type": "FOLD"}
        """
        visible_dealer = game_state.current_visible_dealer_cards()
        active_others = [p for p in game_state.active_players() if p.player_id != player.player_id]

        # Consider Fold if hand is terrible and round is late (round 4 or 5)
        # But fold loses half bet, so only if chips are precious
        if game_state.current_round >= 4 and player.swaps_left == 0 and len(player.cards) == 3:
            hand_sum = sum(c.value for c in player.cards)
            # If hand sum is very high (> 35) and unlikely to win
            if hand_sum >= 35 and random.random() < 0.25:
                return {"type": "FOLD"}

        # Consider All-In Hand Steal (High risk move)
        # Only in rounds 3, 4, 5 if AI has low chance with current hand
        # and targets a player who hasn't discarded or looks confident
        if game_state.current_round >= 3 and active_others and random.random() < 0.08:
            target = random.choice(active_others)
            return {"type": "STEAL", "target_id": target.player_id}

        # Consider Blind Swap & Single Card Gambit
        # If AI holds 3 high cards and wants a gamble for lowest sum or reset
        if len(player.cards) == 3 and active_others and player.swaps_left > 0:
            avg_val = sum(c.value for c in player.cards) / 3.0
            if avg_val > 10 and random.random() < 0.15:
                target = random.choice(active_others)
                return {"type": "BLIND_SWAP", "target_id": target.player_id}

        # Standard Discard & Draw
        if player.swaps_left > 0 and not player.swapped_this_turn and len(player.cards) == 3:
            # Analyze cards: try to discard the card that hurts odds most
            # E.g. highest card when not forming letters or pairs
            # If 2 cards are same rank, keep the pair! Discard the third
            ranks = [c.rank for c in player.cards]
            if ranks[0] == ranks[1]:
                return {"type": "DISCARD_DRAW", "card_index": 2}
            elif ranks[1] == ranks[2]:
                return {"type": "DISCARD_DRAW", "card_index": 0}
            elif ranks[0] == ranks[2]:
                return {"type": "DISCARD_DRAW", "card_index": 1}

            # If aiming for odd/even, find the outlier
            odds = [i for i, c in enumerate(player.cards) if not c.is_even]
            evens = [i for i, c in enumerate(player.cards) if c.is_even]
            if len(odds) == 1 and random.random() < 0.6:
                return {"type": "DISCARD_DRAW", "card_index": odds[0]}
            if len(evens) == 1 and random.random() < 0.6:
                return {"type": "DISCARD_DRAW", "card_index": evens[0]}

            # Otherwise discard highest card to keep sum low
            highest_idx = max(range(len(player.cards)), key=lambda i: player.cards[i].value)
            if player.cards[highest_idx].value > 8 and random.random() < 0.7:
                return {"type": "DISCARD_DRAW", "card_index": highest_idx}

        return {"type": "PASS"}
