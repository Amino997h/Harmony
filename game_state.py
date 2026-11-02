import random
from typing import List, Dict, Optional, Tuple
from collections import Counter
from rules_engine import (
    Card, build_deck, is_consecutive_3, evaluate_hand,
    check_all_letters, check_odd_even_polarity,
    check_strict_alternating_straight, check_under_or_equal_48,
    check_matching_pair
)

class Player:
    def __init__(self, player_id: int, name: str, chips: int = 1000, is_human: bool = False):
        self.player_id = player_id
        self.name = name
        self.chips = chips
        self.is_human = is_human

        # State per round
        self.cards: List[Card] = []
        self.bet: int = 0
        self.swaps_left: int = 2
        self.swapped_this_turn: bool = False
        self.is_eliminated: bool = False
        self.is_folded: bool = False
        self.is_single_card_gambit: bool = False
        self.last_discarded: Optional[Card] = None

        # Turn order determination
        self.preliminary_card: Optional[Card] = None
        self.turn_order_rank: int = 0 # 1st, 2nd, etc.

    def reset_for_round(self):
        self.cards = []
        self.bet = 0
        self.swaps_left = 2
        self.swapped_this_turn = False
        self.is_eliminated = False
        self.is_folded = False
        self.is_single_card_gambit = False
        self.last_discarded = None
        self.preliminary_card = None

class GameState:
    def __init__(self, player_names: List[str] = None):
        if player_names is None:
            player_names = ["اللاعب (أنت)", "كريم (AI)", "سارة (AI)", "طارق (AI)", "ليلى (AI)"]
        
        self.players: List[Player] = []
        for i, name in enumerate(player_names):
            self.players.append(Player(player_id=i, name=name, chips=1000, is_human=(i == 0)))

        self.dealer_cards: List[Card] = []
        self.deck: List[Card] = []
        self.pot: int = 0
        self.current_round: int = 0 # 1 to 5
        self.phase: str = "ORDER_DETERMINATION" # ORDER_DETERMINATION, BETTING, PLAYING, SHOWDOWN, ROUND_OVER
        self.default_ante: int = 100
        self.current_bet_target: int = 100
        self.cards_dealt_to_players: int = 0 # Progressive: 1, 2, then 3
        self.turn_order_players: List[Player] = [] # Ordered by preliminary card value
        self.logs: List[str] = []
        self.discarded_pile: List[Card] = []
        self.revealed_cards: set = set() # Set of Card objects that have been publicly revealed

    def log(self, message: str):
        self.logs.append(message)
        try:
            print(f"[LOG] {message}")
        except Exception:
            pass

    def active_players(self) -> List[Player]:
        return [p for p in self.players if not p.is_eliminated and not p.is_folded]

    def start_new_round(self):
        self.pot = 0
        # Build 60-card deck (56 cards + 4 Jokers)
        self.deck = build_deck(include_jokers=True)
        random.shuffle(self.deck)
        self.dealer_cards = []
        self.discarded_pile = []
        self.revealed_cards = set()
        self.current_round = 0
        self.current_bet_target = self.default_ante
        self.cards_dealt_to_players = 0
        self.phase = "ORDER_DETERMINATION"

        for p in self.players:
            p.reset_for_round()

        # Check pre-game bankrupt (Rule 3.ج)
        for p in self.players:
            if p.chips < self.default_ante:
                p.is_eliminated = True
                self.log(f"عجز مالي مسبق: {p.name} رصيده لا يكفي للدخول وتم استبعاده!")

        # Put default ante 100
        for p in self.players:
            if not p.is_eliminated:
                p.chips -= self.default_ante
                p.bet = self.default_ante
                self.pot += self.default_ante

        self.log(f"بدأت جولة جديدة! رهان الدخول {self.default_ante}. الوعاء: {self.pot}")

    def determine_turn_order(self):
        """Rule 2: Draw preliminary card for each player, sort ascending by card value."""
        active = self.active_players()
        # Draw 1 card for each
        for p in active:
            p.preliminary_card = self.deck.pop()

        # Handle ties: re-draw for tied players until unique values
        while True:
            val_counts = Counter(p.preliminary_card.value for p in active)
            tied_vals = [v for v, c in val_counts.items() if c > 1]
            if not tied_vals:
                break
            for p in active:
                if p.preliminary_card.value in tied_vals:
                    # Re-draw
                    self.discarded_pile.append(p.preliminary_card)
                    p.preliminary_card = self.deck.pop()

        # Sort ascending (smallest card value plays first!)
        active.sort(key=lambda p: p.preliminary_card.value)
        self.turn_order_players = active
        for rank, p in enumerate(self.turn_order_players, 1):
            p.turn_order_rank = rank
            self.log(f"ترتيب الأسبقية #{rank}: {p.name} (كرت الأسبقية: {p.preliminary_card.display_name()})")

        # Return preliminary cards to deck and shuffle before deal (Rule 2.4)
        for p in active:
            self.deck.append(p.preliminary_card)
        self.deck.extend(self.discarded_pile)
        self.discarded_pile = []
        random.shuffle(self.deck)

        # Distribute 5 dealer cards face down (Dealer cards CANNOT be Jokers per Rule 1 & 5.ج)
        self.dealer_cards = []
        temp_drawn = []
        while len(self.dealer_cards) < 5:
            c = self.deck.pop()
            if c.is_joker:
                temp_drawn.append(c)
            else:
                self.dealer_cards.append(c)
        # Return any jokers drawn for dealer back to deck and reshuffle
        if temp_drawn:
            self.deck.extend(temp_drawn)
            random.shuffle(self.deck)

        # Move to Progressive Deal Phase 1: Deal 1st card to each player
        self.deal_progressive_card()
        self.phase = "BETTING"

    def deal_progressive_card(self):
        """Deals next card (1st, 2nd, or 3rd) to all active players."""
        if self.cards_dealt_to_players >= 3:
            return
        self.cards_dealt_to_players += 1
        for p in self.active_players():
            p.cards.append(self.deck.pop())
        self.log(f"تم توزيع الكرت رقم {self.cards_dealt_to_players} لكل لاعب في يده!")

    def start_main_game_rounds(self):
        """Ensure players have all 3 cards and transition to Round 1."""
        while self.cards_dealt_to_players < 3:
            self.deal_progressive_card()
        self.current_round = 1
        self.phase = "PLAYING"
        self.log(f"اكتمل توزيع 3 كروت لجميع اللاعبين وبدأت الجولة 1 الرسمية!")

    def deal_cards_after_betting(self):
        """Backward-compatible helper: sets up dealer cards, gives 3 cards to each player, and starts round 1."""
        if not self.dealer_cards:
            self.dealer_cards = [self.deck.pop() for _ in range(5)]
        self.start_main_game_rounds()

    def current_visible_dealer_cards(self) -> List[Card]:
        if self.phase == "BETTING" or self.phase == "ORDER_DETERMINATION":
            return []
        return self.dealer_cards[:min(self.current_round, 5)]

    def get_all_known_revealed_cards(self) -> set:
        """Returns all cards that are currently known to players (dealer visible, player's own, discards)."""
        known = set(self.revealed_cards)
        # Also include visible dealer cards
        for c in self.current_visible_dealer_cards():
            known.add(c)
        # Also include human player's cards
        if self.players:
            for c in self.players[0].cards:
                known.add(c)
        # Also include discarded pile
        for c in self.discarded_pile:
            known.add(c)
        return known

    def player_discard_and_draw(self, player: Player, card_index_to_discard: int) -> bool:
        if player.swaps_left <= 0 or player.swapped_this_turn:
            return False
        if not self.deck:
            self.deck = list(self.discarded_pile)
            random.shuffle(self.deck)
            self.discarded_pile = []
            if not self.deck:
                return False

        if card_index_to_discard < 0 or card_index_to_discard >= len(player.cards):
            return False

        discarded = player.cards.pop(card_index_to_discard)
        new_card = self.deck.pop()
        player.cards.append(new_card)
        player.swaps_left -= 1
        player.swapped_this_turn = True
        player.last_discarded = discarded
        self.discarded_pile.append(discarded)
        self.log(f"استبدال: {player.name} كشف واستبعد [{discarded.display_name()}]")
        return True

    def player_all_in_steal(self, player: Player, target_player: Player) -> Tuple[bool, str]:
        if player == target_player or target_player.is_folded or target_player.is_eliminated:
            return False, "هدف غير صالح"

        player.cards, target_player.cards = target_player.cards, player.cards
        revealed_dealer_cards = list(self.dealer_cards)

        is_all_letters = check_all_letters(player.cards, revealed_dealer_cards)
        is_odd_even = check_odd_even_polarity(player.cards, revealed_dealer_cards)
        is_straight = check_strict_alternating_straight(player.cards, revealed_dealer_cards)
        is_under_48 = check_under_or_equal_48(player.cards, revealed_dealer_cards)
        is_matching = check_matching_pair(player.cards, revealed_dealer_cards)

        won = is_all_letters or is_odd_even or is_straight or is_under_48 or is_matching

        if won:
            self.phase = "ROUND_OVER"
            player.chips += self.pot
            self.pot = 0
            return True, f"نجحت السرقة وفاز {player.name} فوراً بالوعاء!"
        else:
            player.is_eliminated = True
            unrevealed_dealer_count = 5 - self.current_round
            stolen_cards = list(player.cards)
            player.cards = []

            self.deck.extend(stolen_cards)
            premature_dealer_cards = self.dealer_cards[self.current_round:]
            self.deck.extend(premature_dealer_cards)
            random.shuffle(self.deck)

            new_dealer_replacements = [self.deck.pop() for _ in range(unrevealed_dealer_count)]
            self.dealer_cards = self.dealer_cards[:self.current_round] + new_dealer_replacements
            return False, f"فشلت السرقة وتم إقصاء {player.name}!"

    def player_play_joker(self, player: Player, card_index_to_replace_dealer: int, dealer_card_index: int) -> Tuple[bool, str]:
        """
        Rule 5.ج (Sabotage Joker Action):
        - Player consumes a Joker in hand to sabotage a visible dealer card.
        - The chosen player card is moved to the dealer table replacing the dealer card.
        - The old dealer card and the Joker are discarded / removed from game.
        - The player draws 2 replacement cards from the deck (one for Joker, one for the given card)
          so they return to having a full 3-card hand!
        """
        # Find joker index in player cards
        joker_idx = -1
        for idx, c in enumerate(player.cards):
            if c.is_joker:
                joker_idx = idx
                break

        if joker_idx == -1:
            return False, "لا تملك كرت جوكر في يدك!"

        if dealer_card_index < 0 or dealer_card_index >= min(self.current_round, 5):
            return False, "اختر كرتاً مكشوفاً من كروت الموزع!"

        if card_index_to_replace_dealer < 0 or card_index_to_replace_dealer >= len(player.cards):
            return False, "اختر كرتاً عادياً من يدك لتبديله مع الموزع!"

        if card_index_to_replace_dealer == joker_idx:
            return False, "لا يمكنك وضع الجوكر للموزع!"

        joker_card = player.cards.pop(joker_idx)
        # Re-index if necessary
        if card_index_to_replace_dealer > joker_idx:
            card_index_to_replace_dealer -= 1

        chosen_card = player.cards.pop(card_index_to_replace_dealer)
        old_dealer_card = self.dealer_cards[dealer_card_index]

        # Replace dealer card with chosen card
        self.dealer_cards[dealer_card_index] = chosen_card

        # Discard old dealer card and consumed joker
        self.discarded_pile.append(old_dealer_card)
        self.discarded_pile.append(joker_card)

        # Player draws 2 new cards from deck
        while len(player.cards) < 3:
            if not self.deck:
                self.deck = [c for c in self.discarded_pile if not c.is_joker]
                random.shuffle(self.deck)
                self.discarded_pile = [c for c in self.discarded_pile if c.is_joker]
            if self.deck:
                player.cards.append(self.deck.pop())
            else:
                break

        self.log(f"مناورة الجوكر: استبدل {player.name} كرت الموزع [{old_dealer_card.display_name()}] بـ [{chosen_card.display_name()}] وسحب كرتين جديدين!")
        return True, f"نجحت مناورة الجوكر! تم تغيير كرت الموزع إلى [{chosen_card.display_name()}] وسحب ورقتين جديدتين!"

    def player_blind_swap(self, player: Player, target_player: Player) -> Tuple[bool, str]:
        if player == target_player or target_player.is_folded or target_player.is_eliminated:
            return False, "هدف غير صالح"
        if len(target_player.cards) == 0:
            return False, "اللاعب المستهدف لا يملك كروت"

        p_card = random.choice(player.cards)
        t_card = random.choice(target_player.cards)

        player.cards.remove(p_card)
        target_player.cards.remove(t_card)
        target_player.cards.append(p_card)

        for c in player.cards:
            self.discarded_pile.append(c)
        player.cards = [t_card]
        player.is_single_card_gambit = True
        player.swaps_left = 0
        return True, "تمت التضحية باليد بنجاح!"

    def player_fold(self, player: Player) -> int:
        player.is_folded = True
        refund = player.bet // 2
        player.chips += refund
        self.pot -= refund
        return refund

    def check_showdown(self) -> Dict:
        active = self.active_players()
        self.phase = "ROUND_OVER"

        results = []
        for p in active:
            rank, score, desc = evaluate_hand(p.cards, self.dealer_cards)
            results.append({
                "player": p,
                "rank": rank,
                "score": score,
                "desc": desc
            })

        results.sort(key=lambda x: (x["rank"], x["score"]))

        if not results:
            return {"winners": [], "tie": True, "results": results}

        best_rank = results[0]["rank"]
        best_score = results[0]["score"]

        if best_rank == 99:
            self._handle_tie()
            return {"winners": [], "tie": True, "reason": "universal_tie", "results": results}

        top_candidates = []
        for r in results:
            if r["rank"] == best_rank:
                if best_rank == 6:
                    if r["score"] == best_score:
                        top_candidates.append(r["player"])
                else:
                    top_candidates.append(r["player"])

        if len(top_candidates) == 1:
            winner = top_candidates[0]
            winner.chips += self.pot
            win_msg = f"🏆 الفائز هو {winner.name} وحصل على كامل الوعاء ({self.pot} عملة)!"
            self.pot = 0
            return {"winners": [winner], "tie": False, "results": results, "msg": win_msg}
        else:
            self._handle_tie()
            return {"winners": top_candidates, "tie": True, "reason": "rank_tie", "results": results}

    def _handle_tie(self):
        """
        Official Tie & Pot Sharing Rule (Section 8.b):
        - If no one was eliminated: each active player receives their fair share / ante back.
        - If someone was eliminated (Dead Money): the eliminated player's bets are shared equally among remaining active players.
        """
        active = self.active_players()
        if not active:
            return

        # Check if there are eliminated players whose money is in the pot
        eliminated_players = [p for p in self.players if p.is_eliminated]
        dead_money = sum(p.bet for p in eliminated_players)

        if dead_money > 0:
            self.log(f"قاعدة أموال المُقصى: تقاسم {dead_money} من أموال اللاعبين المقُصين بالتساوي على الصامدين!")

        share = self.pot // len(active)
        for p in active:
            p.chips += share
        self.pot = 0
