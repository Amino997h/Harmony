import random
from typing import List, Tuple, Optional, Dict
from collections import Counter

SUITS = ['♠', '♥', '♦', '♣'] # سبيت, هاس, ديناري, كبة
RANK_VALUES = {
    'A': 1,
    '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10,
    'J': 11,
    'Q': 12,
    'K': 13,
    'S': 14,
    'JK': 25 # Penalty value at showdown if unplayed
}
LETTERS = {'A', 'J', 'Q', 'K', 'S'}

class Card:
    def __init__(self, rank: str, suit: str):
        self.rank = rank
        self.suit = suit
        self.is_joker = (rank == 'JK')
        self.value = RANK_VALUES[rank]
        self.is_letter = (rank in LETTERS)
        self.is_even = (self.value % 2 == 0) if not self.is_joker else False

    def display_name(self) -> str:
        if self.is_joker:
            return "🃏 جوكر"
        return f"{self.rank}{self.suit}"

    def __repr__(self):
        return self.display_name()

    def __eq__(self, other):
        if not isinstance(other, Card):
            return False
        return self.rank == other.rank and self.suit == other.suit

    def __hash__(self):
        return hash((self.rank, self.suit))

def build_deck(include_jokers: bool = True) -> List[Card]:
    """
    Builds the 60-card deck:
    - 56 standard cards (4 suits x 14 ranks)
    - 4 Sabotage Jokers (🃏)
    """
    deck = []
    for s in SUITS:
        for r in ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'S']:
            deck.append(Card(r, s))
    if include_jokers:
        for j_id in range(1, 5):
            deck.append(Card('JK', f'🃏{j_id}'))
    return deck

def is_consecutive_3(cards: List[Card]) -> bool:
    if len(cards) != 3:
        return False
    vals = sorted([c.value for c in cards])
    return (vals[0] + 1 == vals[1]) and (vals[1] + 1 == vals[2])



# Updated conditions according to Official Rules Guide:
# Rank 1: Odd/Even Harmony (التطابق والانسجام الزوجي / الفردي)
# Rank 2: Alternating Straight (السلسلة المتناوبة المرنة - 5 كروت متناوبة، 2 منها على الأقل للاعب)
# Rank 3: Royal Five Letters (شرط الحروف الخمسة المشتركة - 5 كروت حروف مجتمعة، 2 منها على الأقل للاعب)
# Rank 4: Under or Exactly 48 (شرط الـ 48 الذهبية <= 48)
# Rank 5: Matching Pair (شرط التطابق مع الموزع زوجين وخلو الموزع من +-1)

def check_odd_even_harmony(player_cards: List[Card], dealer_cards: List[Card]) -> bool:
    """Rank 1: All player cards and all dealer cards are pure even, OR pure odd."""
    if len(dealer_cards) != 5:
        return False
    if len(player_cards) not in (1, 3):
        return False

    p_even = all(c.is_even for c in player_cards)
    p_odd = all(not c.is_even for c in player_cards)
    d_even = all(c.is_even for c in dealer_cards)
    d_odd = all(not c.is_even for c in dealer_cards)

    # Harmony: Both player AND dealer are pure even, or both are pure odd
    return (p_even and d_even) or (p_odd and d_odd)

def check_alternating_straight(player_cards: List[Card], dealer_cards: List[Card]) -> bool:
    """
    Rank 2: 5 consecutive cards alternating between player and dealer.
    At least 2 cards must come from the player.
    Patterns of 5 consecutive values [v, v+1, v+2, v+3, v+4]:
    Pattern A: D -> P -> D -> P -> D (3 from dealer, 2 from player)
    Pattern B: P -> D -> P -> D -> P (3 from player, 2 from dealer - possible if player has 3 cards)
    """
    if len(player_cards) < 2 or len(dealer_cards) < 2:
        return False

    p_vals = [c.value for c in player_cards]
    d_vals = [c.value for c in dealer_cards]

    for start_v in range(1, 11): # straight of length 5: start_v .. start_v+4 (max 10..14)
        v = [start_v + i for i in range(5)]

        # Check Pattern A: D -> P -> D -> P -> D
        if len(dealer_cards) >= 3 and len(player_cards) >= 2:
            d_req = [v[0], v[2], v[4]]
            p_req = [v[1], v[3]]
            d_c = list(d_vals)
            p_c = list(p_vals)
            ok = True
            for req in d_req:
                if req in d_c:
                    d_c.remove(req)
                else:
                    ok = False
                    break
            if ok:
                for req in p_req:
                    if req in p_c:
                        p_c.remove(req)
                    else:
                        ok = False
                        break
                if ok:
                    return True

        # Check Pattern B: P -> D -> P -> D -> P (3 from player, 2 from dealer)
        if len(player_cards) >= 3 and len(dealer_cards) >= 2:
            p_req = [v[0], v[2], v[4]]
            d_req = [v[1], v[3]]
            p_c = list(p_vals)
            d_c = list(d_vals)
            ok = True
            for req in p_req:
                if req in p_c:
                    p_c.remove(req)
                else:
                    ok = False
                    break
            if ok:
                for req in d_req:
                    if req in d_c:
                        d_c.remove(req)
                    else:
                        ok = False
                        break
                if ok:
                    return True

    return False

def check_royal_five_letters(player_cards: List[Card], dealer_cards: List[Card]) -> bool:
    """
    Rank 3: 5 letters combined between player hand and dealer cards.
    Must have at least 2 letters from player hand.
    """
    if len(dealer_cards) != 5:
        return False
    p_letters = sum(1 for c in player_cards if c.is_letter)
    if p_letters < 2:
        return False
    d_letters = sum(1 for c in dealer_cards if c.is_letter)
    return (p_letters + d_letters) >= 5

def check_under_or_equal_48(player_cards: List[Card], dealer_cards: List[Card]) -> bool:
    """Rank 4: Total sum of player cards (or single card x3) + dealer 5 cards <= 48."""
    if len(dealer_cards) != 5:
        return False
    if len(player_cards) == 3:
        p_sum = sum(c.value for c in player_cards)
    elif len(player_cards) == 1:
        p_sum = player_cards[0].value * 3
    else:
        return False
    total = p_sum + sum(c.value for c in dealer_cards)
    return total <= 48

def check_matching_pair(player_cards: List[Card], dealer_cards: List[Card]) -> bool:
    """
    Rank 5: Player has pair (>= 2 cards of value V), Dealer has pair (>= 2 cards of value V).
    Updated rule: Neighboring cards (+-1) restriction has been REMOVED!
    """
    if len(dealer_cards) != 5:
        return False
    # Jokers cannot form standard matching pair
    p_valid = [c for c in player_cards if not c.is_joker]
    d_valid = [c for c in dealer_cards if not c.is_joker]
    p_counts = Counter(c.value for c in p_valid)
    d_counts = Counter(c.value for c in d_valid)

    for val, p_cnt in p_counts.items():
        if p_cnt >= 2 and d_counts.get(val, 0) >= 2:
            return True
    return False

# Backward-compatible aliases
check_all_letters = check_royal_five_letters
check_odd_even_polarity = check_odd_even_harmony
check_strict_alternating_straight = check_alternating_straight

def evaluate_hand(player_cards: List[Card], dealer_cards: List[Card]) -> Tuple[int, int, str]:
    """
    Evaluates player's hand against the 5 dealer cards according to the updated hierarchy:
    - Rule 5.ج (Joker Curse): If player still holds a Joker in hand, they CANNOT WIN under any condition,
      and the Joker imposes a 25-point penalty in tie-breaking!
    Rank 1: Odd/Even Harmony (التطابق الزوجي / الفردي)
    Rank 2: Alternating Straight (السلسلة المتناوبة)
    Rank 3: Royal Five Letters (الحروف الخمسة المشتركة)
    Rank 4: Golden 48 (شرط الـ 48 الذهبية <= 48)
    Rank 5: Matching Pair (التطابق المزدوج مع الموزع - دون قيد الجوار)
    Rank 6: Default Qualified Lowest Sum (أدنى مجموع مؤهل)
    Rank 99: Disqualified / No condition met
    """
    has_joker = any(c.is_joker for c in player_cards)

    # If player holds a Joker, they cannot win any exceptional condition!
    if not has_joker:
        if check_odd_even_harmony(player_cards, dealer_cards):
            return (1, 0, "🥇 الانسجام والتطابق الزوجي / الفردي (Odd/Even Harmony)")
        if check_alternating_straight(player_cards, dealer_cards):
            return (2, 0, "🥈 السلسلة المتناوبة المرنة (Alternating Straight)")
        if check_royal_five_letters(player_cards, dealer_cards):
            return (3, 0, "🥉 الحروف الخمسة المشتركة (Royal Five Letters)")
        if check_under_or_equal_48(player_cards, dealer_cards):
            return (4, 0, "🏅 شرط الـ 48 الذهبية (<= 48)")
        if check_matching_pair(player_cards, dealer_cards):
            return (5, 0, "🎖️ التطابق المزدوج مع الموزع (Matching Pair)")

    royal_dealer = all(c.value > 10 for c in dealer_cards)
    min_dealer = min(c.value for c in dealer_cards) if dealer_cards else 0
    
    if len(player_cards) == 3:
        p_min = min(c.value for c in player_cards)
        p_sum = sum(c.value for c in player_cards)
    elif len(player_cards) == 1:
        p_min = player_cards[0].value
        p_sum = player_cards[0].value * 3
    else:
        return (99, 9999, "غير مؤهل")

    total_sum = p_sum + sum(c.value for c in dealer_cards)
    is_qualified = royal_dealer or (p_min >= min_dealer)
    if is_qualified:
        if has_joker:
            return (6, total_sum, f"أدنى مجموع (عقوبة الجوكر +25 نقطة! المجموع: {total_sum})")
        reason = "أدنى مجموع مؤهل (استثناء الموزع الملكي)" if royal_dealer else "أدنى مجموع مؤهل"
        return (6, total_sum, f"{reason} (المجموع: {total_sum})")
    else:
        joker_tag = " [يحمل جوكر]" if has_joker else ""
        return (99, total_sum, f"غير مؤهل لكسر التعادل (أصغر كرت {p_min} < كرت الموزع {min_dealer}){joker_tag}")

# Real-time Possibility / Chance Analyzer
# Given player's current cards and dealer's current VISIBLE cards (1 to 5)
def analyze_winning_chances(player_cards: List[Card], visible_dealer_cards: List[Card]) -> List[Dict]:
    """
    Returns status for each of the 6 conditions according to updated hierarchy:
    Rank 1: Odd/Even Harmony (الانسجام الزوجي / الفردي)
    Rank 2: Alternating Straight (السلسلة المتناوبة المرنة)
    Rank 3: Royal Five Letters (الحروف الخمسة المشتركة)
    Rank 4: Under or Exactly 48 (شرط الـ 48 الذهبية)
    Rank 5: Matching Pair (التطابق الخالي من الجوار)
    Rank 6: Default Qualified Lowest Sum (أدنى مجموع مؤهل)
    """
    results = []
    num_p = len(player_cards)
    num_d = len(visible_dealer_cards)
    unrevealed_d = 5 - num_d

    # 1. Odd / Even Harmony (الانسجام والتطابق الزوجي / الفردي)
    p_all_even = (num_p in (1, 3)) and all(c.is_even for c in player_cards)
    p_all_odd = (num_p in (1, 3)) and all(not c.is_even for c in player_cards)
    
    d_has_even = any(c.is_even for c in visible_dealer_cards)
    d_has_odd = any(not c.is_even for c in visible_dealer_cards)

    if not p_all_even and not p_all_odd:
        results.append({
            "id": 1,
            "name": "1. الانسجام الزوجي/الفردي",
            "status": "IMPOSSIBLE",
            "badge": "❌ يدك مختلطة",
            "reason": "يدك تحوي زوجي وفردي معاً"
        })
    else:
        target_mode = "زوجي" if p_all_even else "فردي"
        # If player even, dealer must be pure even. If dealer has any odd -> IMPOSSIBLE
        if p_all_even and d_has_odd:
            results.append({
                "id": 1,
                "name": "1. الانسجام الزوجي/الفردي",
                "status": "IMPOSSIBLE",
                "badge": "❌ انكسر الانسجام",
                "reason": "يدك زوجية والموزع كشف كرت فردي"
            })
        elif p_all_odd and d_has_even:
            results.append({
                "id": 1,
                "name": "1. الانسجام الزوجي/الفردي",
                "status": "IMPOSSIBLE",
                "badge": "❌ انكسر الانسجام",
                "reason": "يدك فردية والموزع كشف كرت زوجي"
            })
        else:
            if num_d == 5:
                results.append({
                    "id": 1,
                    "name": "1. الانسجام الزوجي/الفردي",
                    "status": "ACHIEVED",
                    "badge": "🔥 محقق الآن!",
                    "reason": f"انسجام تام: كروتك وكروت الموزع {target_mode}ة بالكامل!"
                })
            else:
                results.append({
                    "id": 1,
                    "name": "1. الانسجام الزوجي/الفردي",
                    "status": "POSSIBLE",
                    "badge": "⏳ فرصة قائمة",
                    "reason": f"يدك متطابقة ومطلوب كروت الموزع القادمة {target_mode}ة (باقي {unrevealed_d})"
                })

    # 2. Alternating Straight (السلسلة المتناوبة المرنة - 5 متتالية، 2 على الأقل بيدك)
    if num_p < 2:
        results.append({
            "id": 2,
            "name": "2. السلسلة المتناوبة",
            "status": "IMPOSSIBLE",
            "badge": "❌ محال",
            "reason": "تتطلب كرتين على الأقل باليد"
        })
    else:
        if num_d == 5 and check_alternating_straight(player_cards, visible_dealer_cards):
            results.append({
                "id": 2,
                "name": "2. السلسلة المتناوبة",
                "status": "ACHIEVED",
                "badge": "🔥 محقق الآن!",
                "reason": "سلسلة متناوبة كاملة من 5 أوراق متتالية!"
            })
        else:
            # Check potential
            p_vals = set(c.value for c in player_cards)
            d_vals = [c.value for c in visible_dealer_cards]
            has_potential = False
            for start_v in range(1, 11):
                v = [start_v + i for i in range(5)]
                # Pattern A: D:0,2,4 & P:1,3
                if v[1] in p_vals and v[3] in p_vals:
                    needed_d = [v[0], v[2], v[4]]
                    missing = sum(1 for req in needed_d if req not in d_vals)
                    if missing <= unrevealed_d:
                        has_potential = True
                        break
                # Pattern B: P:0,2,4 & D:1,3
                if len(player_cards) >= 3 and (v[0] in p_vals and v[2] in p_vals and v[4] in p_vals):
                    needed_d = [v[1], v[3]]
                    missing = sum(1 for req in needed_d if req not in d_vals)
                    if missing <= unrevealed_d:
                        has_potential = True
                        break
            if has_potential:
                results.append({
                    "id": 2,
                    "name": "2. السلسلة المتناوبة",
                    "status": "POSSIBLE",
                    "badge": "⏳ فرصة قائمة",
                    "reason": "لديك مكونات سلسلة وبانتظار تناوب الموزع"
                })
            else:
                results.append({
                    "id": 2,
                    "name": "2. السلسلة المتناوبة",
                    "status": "IMPOSSIBLE",
                    "badge": "❌ غير متوفرة بيدك",
                    "reason": "أوراق يدك لا تؤلف تناوباً مع المتاح"
                })

    # 3. Royal Five Letters (الحروف الخمسة المشتركة: 5 حروف مجتمعة، 2 على الأقل بيدك)
    p_letters = sum(1 for c in player_cards if c.is_letter)
    d_letters = sum(1 for c in visible_dealer_cards if c.is_letter)
    if p_letters < 2:
        results.append({
            "id": 3,
            "name": "3. الحروف الخمسة المشتركة",
            "status": "IMPOSSIBLE",
            "badge": "❌ كروت يدك غير كافية",
            "reason": f"لديك {p_letters} حروف فقط (المطلوب 2 على الأقل بيدك)"
        })
    else:
        total_curr_letters = p_letters + d_letters
        max_possible_letters = total_curr_letters + unrevealed_d
        if max_possible_letters < 5:
            results.append({
                "id": 3,
                "name": "3. الحروف الخمسة المشتركة",
                "status": "IMPOSSIBLE",
                "badge": "❌ محال",
                "reason": f"أقصى حروف ممكنة {max_possible_letters} < 5"
            })
        elif num_d == 5 and total_curr_letters >= 5:
            results.append({
                "id": 3,
                "name": "3. الحروف الخمسة المشتركة",
                "status": "ACHIEVED",
                "badge": "🔥 محقق الآن!",
                "reason": f"لديك {p_letters} حروف والموزع {d_letters} (المجموع {total_curr_letters})!"
            })
        else:
            results.append({
                "id": 3,
                "name": "3. الحروف الخمسة المشتركة",
                "status": "POSSIBLE",
                "badge": "⏳ فرصة قائمة",
                "reason": f"الحروف الحالية: {total_curr_letters} من 5 (باقي {5 - total_curr_letters})"
            })

    # 4. Under or Equal 48 (Golden 48)
    p_sum = sum(c.value for c in player_cards) if num_p == 3 else (player_cards[0].value * 3 if num_p == 1 else 99)
    curr_d_sum = sum(c.value for c in visible_dealer_cards)
    curr_total = p_sum + curr_d_sum
    # Min possible remaining cards value: 1 each
    min_possible_future_d = unrevealed_d * 1
    if curr_total + min_possible_future_d > 48:
        results.append({
            "id": 4,
            "name": "4. الـ 48 الذهبية",
            "status": "IMPOSSIBLE",
            "badge": "❌ محال (تجاوز 48)",
            "reason": f"المجموع الحالي مع أدنى كروت سيتجاوز 48"
        })
    else:
        if num_d == 5 and curr_total <= 48:
            results.append({
                "id": 4,
                "name": "4. الـ 48 الذهبية",
                "status": "ACHIEVED",
                "badge": "🔥 محقق الآن!",
                "reason": f"مجموع كروتك والموزع ({curr_total} <= 48)"
            })
        else:
            results.append({
                "id": 4,
                "name": "4. الـ 48 الذهبية",
                "status": "POSSIBLE",
                "badge": "⏳ فرصة قائمة",
                "reason": f"المجموع حتى الآن: {curr_total} (الحد الأقصى 48)"
            })

    # 5. Matching Pair (don't require exclusion of +-1)
    p_valid = [c for c in player_cards if not c.is_joker]
    p_counts = Counter(c.value for c in p_valid)
    pair_vals = [v for v, cnt in p_counts.items() if cnt >= 2]

    if not pair_vals:
        results.append({
            "id": 5,
            "name": "5. التطابق مع الموزع",
            "status": "IMPOSSIBLE",
            "badge": "❌ لا يوجد زوج بيدك",
            "reason": "تحتاج ورقتين من نفس الرقم بيدك أولاً"
        })
    else:
        v = pair_vals[0]
        d_pair_cnt = sum(1 for c in visible_dealer_cards if c.value == v)
        if d_pair_cnt >= 2 and num_d == 5:
            results.append({
                "id": 5,
                "name": "5. التطابق مع الموزع",
                "status": "ACHIEVED",
                "badge": "🔥 محقق الآن!",
                "reason": f"تطابق زوج {v} مع زوج الموزع بالكامل!"
            })
        elif (2 - d_pair_cnt) <= unrevealed_d:
            results.append({
                "id": 5,
                "name": "5. التطابق مع الموزع",
                "status": "POSSIBLE",
                "badge": "⏳ فرصة قائمة",
                "reason": f"لديك زوج {v}، مطلوب زوج مطابق لدى الموزع"
            })
        else:
            results.append({
                "id": 5,
                "name": "5. التطابق مع الموزع",
                "status": "IMPOSSIBLE",
                "badge": "❌ محال",
                "reason": "لا توجد كروت كافية متبقية للموزع"
            })

    # 6. Default Lowest Sum (Tie Breaker)
    royal_dealer = (num_d == 5) and all(c.value > 10 for c in visible_dealer_cards)
    min_d = min(c.value for c in visible_dealer_cards) if visible_dealer_cards else 1
    min_p = min(c.value for c in player_cards) if player_cards else 99
    
    if royal_dealer:
        results.append({
            "id": 6,
            "name": "كسر التعادل (أدنى مجموع)",
            "status": "ACHIEVED",
            "badge": "⭐ استثناء الموزع الملكي!",
            "reason": "سقط شرط الأهلية عن الجميع!"
        })
    elif min_p < min_d:
        results.append({
            "id": 6,
            "name": "كسر التعادل (أدنى مجموع)",
            "status": "IMPOSSIBLE",
            "badge": "⚠️ غير مؤهل حالياً",
            "reason": f"كرتك {min_p} < أدنى كرت للموزع {min_d}"
        })
    else:
        results.append({
            "id": 6,
            "name": "كسر التعادل (أدنى مجموع)",
            "status": "POSSIBLE",
            "badge": "✅ مؤهل حالياً",
            "reason": f"كرتك الأصغر {min_p} >= كرت الموزع {min_d}"
        })

    return results
