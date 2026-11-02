import unittest
from rules_engine import (
    Card, build_deck, check_all_letters, check_odd_even_polarity,
    check_strict_alternating_straight, check_under_or_equal_48,
    check_matching_pair, evaluate_hand
)

class TestRulesEngine(unittest.TestCase):
    def test_deck_count(self):
        deck = build_deck()
        self.assertEqual(len(deck), 60) # 56 cards + 4 Sabotage Jokers
        letters = [c for c in deck if c.is_letter]
        self.assertEqual(len(letters), 20) # A, J, Q, K, S in 4 suits = 20
        jokers = [c for c in deck if c.is_joker]
        self.assertEqual(len(jokers), 4)

    def test_all_letters(self):
        # Royal Five Letters: 5 combined letters, at least 2 from player
        p = [Card('A', '♠'), Card('K', '♥'), Card('Q', '♦')] # 3 letters
        d = [Card('J', '♠'), Card('S', '♥'), Card('2', '♦'), Card('4', '♣'), Card('6', '♠')] # 2 letters, total 5
        self.assertTrue(check_all_letters(p, d))

        p_fail = [Card('10', '♠'), Card('8', '♥'), Card('Q', '♦')] # only 1 letter from player
        self.assertFalse(check_all_letters(p_fail, d))

    def test_odd_even(self):
        # Harmony: Both player and dealer pure even, OR both pure odd
        p_odd = [Card('A', '♠'), Card('3', '♥'), Card('K', '♦')]
        d_odd = [Card('5', '♠'), Card('7', '♥'), Card('9', '♦'), Card('J', '♣'), Card('K', '♠')]
        self.assertTrue(check_odd_even_polarity(p_odd, d_odd))

        p_even = [Card('2', '♠'), Card('4', '♥'), Card('S', '♦')]
        d_even = [Card('6', '♠'), Card('8', '♥'), Card('10', '♦'), Card('Q', '♣'), Card('S', '♠')]
        self.assertTrue(check_odd_even_polarity(p_even, d_even))

        # Mixed
        p_mix = [Card('2', '♠'), Card('3', '♥'), Card('4', '♦')]
        self.assertFalse(check_odd_even_polarity(p_mix, d_even))

    def test_strict_alternating_straight(self):
        # Example from doc: Dealer has (3, 5, 7), Player has (4, 6)
        # Sequence: 3 -> 4 -> 5 -> 6 -> 7
        d = [Card('3', '♠'), Card('5', '♥'), Card('7', '♦'), Card('K', '♣'), Card('S', '♠')]
        p = [Card('4', '♠'), Card('6', '♥'), Card('2', '♦')]
        self.assertTrue(check_strict_alternating_straight(p, d))

        # Another sequence: 10 -> 11(J) -> 12(Q) -> 13(K) -> 14(S)
        # D: 10, 12, 14 | P: 11, 13
        d2 = [Card('10', '♠'), Card('Q', '♥'), Card('S', '♦'), Card('2', '♣'), Card('3', '♠')]
        p2 = [Card('J', '♠'), Card('K', '♥'), Card('4', '♦')]
        self.assertTrue(check_strict_alternating_straight(p2, d2))

        # Fail sequence
        p_fail = [Card('4', '♠'), Card('8', '♥'), Card('2', '♦')]
        self.assertFalse(check_strict_alternating_straight(p_fail, d))

    def test_under_48(self):
        p = [Card('A', '♠'), Card('2', '♥'), Card('3', '♦')] # sum = 1+2+3 = 6
        d = [Card('4', '♠'), Card('5', '♥'), Card('6', '♦'), Card('7', '♣'), Card('8', '♠')] # sum = 30
        # total = 36 <= 48
        self.assertTrue(check_under_or_equal_48(p, d))

        d_high = [Card('K', '♠'), Card('S', '♥'), Card('Q', '♦'), Card('J', '♣'), Card('10', '♠')] # 13+14+12+11+10=60
        self.assertFalse(check_under_or_equal_48(p, d_high))

    def test_matching_pair(self):
        # P has pair of 8s, D has pair of 8s. Under updated rules, +-1 neighbor restriction is removed!
        p = [Card('8', '♠'), Card('8', '♥'), Card('2', '♦')]
        d = [Card('8', '♦'), Card('8', '♣'), Card('2', '♠'), Card('4', '♥'), Card('K', '♦')]
        self.assertTrue(check_matching_pair(p, d))

        # Even if D has 9 or 7, matching pair now succeeds!
        d_with_neighbor = [Card('8', '♦'), Card('8', '♣'), Card('9', '♠'), Card('4', '♥'), Card('K', '♦')]
        self.assertTrue(check_matching_pair(p, d_with_neighbor))

        # Fails only if no matching pair
        d_no_pair = [Card('8', '♦'), Card('5', '♣'), Card('9', '♠'), Card('4', '♥'), Card('K', '♦')]
        self.assertFalse(check_matching_pair(p, d_no_pair))

    def test_dealer_royal_exception(self):
        # All dealer cards strictly > 10 (J=11, Q=12, K=13, S=14)
        d = [Card('J', '♠'), Card('Q', '♥'), Card('K', '♦'), Card('S', '♣'), Card('J', '♥')]
        # Player has cards < min(dealer)
        p = [Card('A', '♠'), Card('2', '♥'), Card('3', '♦')]
        rank, score, desc = evaluate_hand(p, d)
        # Should be qualified because of royal exception!
        # Hand sum = 1+2+3 + (11+12+13+14+11) = 6 + 61 = 67
        self.assertEqual(rank, 6)
        self.assertIn("استثناء الموزع الملكي", desc)

if __name__ == '__main__':
    unittest.main()
