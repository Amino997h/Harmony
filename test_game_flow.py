import unittest
from game_state import GameState, Player
from rules_engine import Card

class TestGameFlow(unittest.TestCase):
    def test_pregame_bankrupt_ante(self):
        gs = GameState()
        # Set player 4 chips to 50 (< 100)
        gs.players[4].chips = 50
        gs.start_new_round()
        self.assertTrue(gs.players[4].is_eliminated)
        self.assertEqual(len(gs.active_players()), 4)

    def test_deal_and_rounds(self):
        gs = GameState()
        gs.start_new_round()
        gs.deal_cards_after_betting()
        self.assertEqual(gs.current_round, 1)
        self.assertEqual(len(gs.current_visible_dealer_cards()), 1)
        for p in gs.active_players():
            self.assertEqual(len(p.cards), 3)

    def test_discard_limit(self):
        gs = GameState()
        gs.start_new_round()
        gs.deal_cards_after_betting()
        p = gs.players[0]
        # First discard
        self.assertTrue(gs.player_discard_and_draw(p, 0))
        self.assertEqual(p.swaps_left, 1)
        # Cannot discard twice in same turn
        self.assertFalse(gs.player_discard_and_draw(p, 0))
        # Reset turn
        p.swapped_this_turn = False
        # Second discard
        self.assertTrue(gs.player_discard_and_draw(p, 1))
        self.assertEqual(p.swaps_left, 0)
        # Third discard fails
        p.swapped_this_turn = False
        self.assertFalse(gs.player_discard_and_draw(p, 0))

    def test_all_in_steal_failure_elimination(self):
        gs = GameState()
        gs.start_new_round()
        gs.deal_cards_after_betting()
        p0 = gs.players[0]
        p1 = gs.players[1]
        
        # Rig cards to not win
        p1.cards = [Card('2', '♠'), Card('3', '♥'), Card('10', '♦')]
        gs.dealer_cards = [Card('K', '♠'), Card('Q', '♥'), Card('J', '♦'), Card('9', '♣'), Card('7', '♠')]
        
        initial_dealer_round1_card = gs.dealer_cards[0]
        won, msg = gs.player_all_in_steal(p0, p1)
        self.assertFalse(won)
        self.assertTrue(p0.is_eliminated)
        # First card of dealer must remain untouched
        self.assertEqual(gs.dealer_cards[0], initial_dealer_round1_card)
        self.assertEqual(len(gs.dealer_cards), 5)

    def test_blind_swap_gambit(self):
        gs = GameState()
        gs.start_new_round()
        gs.deal_cards_after_betting()
        p0 = gs.players[0]
        p1 = gs.players[1]
        
        success, msg = gs.player_blind_swap(p0, p1)
        self.assertTrue(success)
        self.assertEqual(len(p0.cards), 1)
        self.assertTrue(p0.is_single_card_gambit)
        self.assertEqual(p0.swaps_left, 0)

    def test_fold_and_refund(self):
        gs = GameState()
        gs.start_new_round() # everyone put 100, pot = 500
        p0 = gs.players[0]
        initial_chips = p0.chips # 900
        refund = gs.player_fold(p0)
        self.assertEqual(refund, 50)
        self.assertEqual(p0.chips, initial_chips + 50)
        self.assertEqual(gs.pot, 450)
        self.assertTrue(p0.is_folded)

if __name__ == '__main__':
    unittest.main()
