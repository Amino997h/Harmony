import unittest
from game_state import GameState, Player
from rules_engine import Card, analyze_winning_chances

class TestNewRules(unittest.TestCase):
    def test_turn_order_determination(self):
        gs = GameState()
        gs.start_new_round()
        gs.determine_turn_order()
        self.assertEqual(len(gs.turn_order_players), 5)
        # Verify sorted ascending by preliminary card value
        for i in range(len(gs.turn_order_players) - 1):
            p1 = gs.turn_order_players[i]
            p2 = gs.turn_order_players[i+1]
            self.assertLessEqual(p1.preliminary_card.value, p2.preliminary_card.value)

    def test_progressive_deal(self):
        gs = GameState()
        gs.start_new_round()
        gs.determine_turn_order()
        # After determine_turn_order, exactly 1 card dealt to each player
        for p in gs.active_players():
            self.assertEqual(len(p.cards), 1)
        self.assertEqual(gs.cards_dealt_to_players, 1)

        # Progressive deal 2nd card
        gs.deal_progressive_card()
        for p in gs.active_players():
            self.assertEqual(len(p.cards), 2)
        self.assertEqual(gs.cards_dealt_to_players, 2)

        # Start main game completes 3 cards
        gs.start_main_game_rounds()
        for p in gs.active_players():
            self.assertEqual(len(p.cards), 3)
        self.assertEqual(gs.current_round, 1)

    def test_analyze_winning_chances(self):
        # Letters test: Royal Five Letters
        p_letters = [Card('A', '♠'), Card('K', '♥'), Card('Q', '♦')] # 3 letters in hand
        d_letters = [Card('J', '♠'), Card('S', '♥')] # 2 letters visible -> 5 letters total!
        chances = analyze_winning_chances(p_letters, d_letters)
        # Condition 3 (Royal Five Letters) should be POSSIBLE (needs all 5 dealer cards revealed to achieve)
        c3 = [c for c in chances if c["id"] == 3][0]
        self.assertEqual(c3["status"], "POSSIBLE")

        # Now test hand with only 1 letter (insufficient for Royal Five letters)
        p_insufficient = [Card('2', '♠'), Card('4', '♥'), Card('Q', '♦')]
        chances2 = analyze_winning_chances(p_insufficient, d_letters)
        c3_fail = [c for c in chances2 if c["id"] == 3][0]
        self.assertEqual(c3_fail["status"], "IMPOSSIBLE")

if __name__ == '__main__':
    unittest.main()
