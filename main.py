import sys
import os
import pygame
import random
import math
from game_state import GameState, Player
from rules_engine import Card, evaluate_hand, analyze_winning_chances
from ai_player import GameAI
from sound_effects import SoundManager
from ui_renderer import (
    draw_card_direct, Button, render_arabic, CardAnimation, CenterAnnouncement,
    ParticleManager, CardFlipAnimation, draw_poker_chips_pot, draw_deck_matrix_modal,
    AmbientMoteManager, draw_turn_spotlight, draw_turn_arrow_beacon,
    BG_DARK, TABLE_FELT_CENTER, TABLE_FELT_EDGE, TABLE_WOOD_RIM, TABLE_GOLD_TRIM,
    GOLD, GOLD_BRIGHT, GOLD_DARK, TEXT_WHITE, TEXT_MUTED,
    BTN_PRIMARY, BTN_SUCCESS, BTN_DANGER, BTN_PURPLE, BTN_SLATE,
    COLOR_ACHIEVED, COLOR_POSSIBLE, COLOR_IMPOSSIBLE,
    FONT_XS, FONT_SM, FONT_MD, FONT_LG, FONT_XL, FONT_HERO
)

class CardGameApp:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("🎴 لعبة الورق الاستراتيجية الملكية (النسخة الاحترافية)")
        self.virtual_width = 1280
        self.virtual_height = 800
        self.virtual_screen = pygame.Surface((self.virtual_width, self.virtual_height))
        self.width = self.virtual_width
        self.height = self.virtual_height

        self.is_fullscreen = False
        self.window_size = (self.virtual_width, self.virtual_height)
        self.screen = pygame.display.set_mode(self.window_size, pygame.RESIZABLE)
        self.render_rect = pygame.Rect(0, 0, self.virtual_width, self.virtual_height)
        self.clock = pygame.time.Clock()

        # Screen shake and impact flash
        self.shake_timer_ms = 0
        self.shake_magnitude = 0
        self.red_flash_timer_ms = 0

        # Turn halo pulse animation timer
        self.halo_pulse_timer = 0.0

        # Ambient Idle Motion & Turn Transition timers
        self.global_anim_time = 0.0
        self.turn_transition_timer_ms = 0
        self.turn_transition_target_player = None
        self.mote_manager = AmbientMoteManager(bounds_rect=(70, 70, self.virtual_width - 140, 580), count=35)

        # Player count mode (2 to 6 players, default 5)
        self.num_players_mode: int = 5
        self.show_player_select_modal: bool = False
        self.btn_select_mode_buttons = []

        self.game = GameState(num_players=self.num_players_mode)
        self.sound = SoundManager()
        self.selected_card_index: int = -1
        self.selected_target_id: int = -1
        self.action_message: str = "مرحباً بك! انقر على زر السحب لبدء تحديد الأسبقية."
        self.show_rules_modal: bool = False
        self.show_chances_drawer: bool = False # Collapsible HUD Drawer for winning chances!
        self.show_card_matrix_modal: bool = False # 56-Cards Visual Matrix!
        self.round_result_data: dict = None

        # Particle Manager and Animations
        self.particles = ParticleManager()
        self.animations = []
        self.announcement = CenterAnnouncement()

        # Step Queue for smooth AI turns
        self.step_queue = []
        self.is_processing_steps = False
        self.step_timer_ms = 0
        self.current_turn_player = None

        # Victory / Defeat Animated State
        self.is_human_winner: bool = False
        self.earned_pot_display: int = 0
        self.target_pot_display: int = 0
        self.victory_confetti_spawned: bool = False

        self.init_natural_table_layout()
        self.init_buttons()
        self.update_render_rect()

        # Launch game lifecycle (Rule 2)
        self.start_game_lifecycle()

    def update_render_rect(self):
        real_w, real_h = self.screen.get_size()
        scale = min(real_w / self.virtual_width, real_h / self.virtual_height)
        scaled_w = int(self.virtual_width * scale)
        scaled_h = int(self.virtual_height * scale)
        offset_x = (real_w - scaled_w) // 2
        offset_y = (real_h - scaled_h) // 2
        self.render_rect = pygame.Rect(offset_x, offset_y, scaled_w, scaled_h)

    def to_virtual_pos(self, real_pos):
        rx, ry = real_pos
        vx = (rx - self.render_rect.x) * (self.virtual_width / self.render_rect.width)
        vy = (ry - self.render_rect.y) * (self.virtual_height / self.render_rect.height)
        return int(vx), int(vy)

    def toggle_fullscreen(self):
        self.sound.play('card_click')
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode(self.window_size, pygame.RESIZABLE)
        self.update_render_rect()

    def trigger_elimination_effects(self, center_pos=None):
        self.shake_timer_ms = 600
        self.shake_magnitude = 14
        self.red_flash_timer_ms = 350
        self.sound.play('elimination')
        cx, cy = center_pos if center_pos else (self.center_x, self.center_y)
        self.particles.spawn_shockwave(cx, cy, color=(239, 68, 68))

    def trigger_screen_shake(self, duration_ms=450, magnitude=10):
        self.shake_timer_ms = duration_ms
        self.shake_magnitude = magnitude

    def init_natural_table_layout(self):
        """
        Dynamic Natural Seating Coordinates based on player count:
        - Human (Player 0) is always Bottom Center.
        - Other players (AIs) are comfortably spread around the oval table:
          * 2 Players (1 vs 1): AI 1 directly opposite at Top Center (North)
          * 3 Players (1 vs 2): AI 1 Top-Left (North-West), AI 2 Top-Right (North-East)
          * 4 Players (1 vs 3): AI 1 Far Left (West), AI 2 Top Center (North), AI 3 Far Right (East)
          * 5 Players (1 vs 4): AI 1 Left, AI 2 Top-Left, AI 3 Top-Right, AI 4 Right
          * 6 Players (1 vs 5): AI 1 Far Left, AI 2 Top-Left, AI 3 Top Center, AI 4 Top-Right, AI 5 Far Right
        """
        self.center_x = self.width // 2
        self.center_y = 350

        # 3D Pot Center
        self.pot_pos = (self.center_x, self.center_y - 85)

        # Deck position (near dealer left)
        self.deck_pos = (self.center_x - 240, self.center_y + 15)

        # 5 Dealer Cards Center (below pot)
        self.dealer_cards_pos = [
            (self.center_x - 170 + i * 85, self.center_y + 15) for i in range(5)
        ]

        # Human Seat at Bottom
        self.human_seat_y = 575

        # Dynamic AI Seating layouts
        n_ai = len(self.game.players) - 1
        self.seat_positions = {}

        if n_ai == 1:
            # 1 vs 1: Direct Head-to-Head at Top Center
            self.seat_positions = {
                1: (self.center_x - 90, 85, 180, 135)
            }
        elif n_ai == 2:
            # 3 Players: Two AIs at Top-Left and Top-Right
            self.seat_positions = {
                1: (230, 95, 160, 135),
                2: (890, 95, 160, 135)
            }
        elif n_ai == 3:
            # 4 Players: Left, Top Center, Right
            self.seat_positions = {
                1: (45, 260, 160, 135),
                2: (self.center_x - 80, 85, 160, 135),
                3: (1075, 260, 160, 135)
            }
        elif n_ai == 4:
            # 5 Players: Left, Top-Left, Top-Right, Right
            self.seat_positions = {
                1: (45, 300, 160, 135),
                2: (260, 95, 160, 135),
                3: (860, 95, 160, 135),
                4: (1075, 300, 160, 135)
            }
        else:
            # 6 Players: Left, Top-Left, Top-Center, Top-Right, Right
            self.seat_positions = {
                1: (45, 300, 160, 135),
                2: (230, 95, 155, 135),
                3: (self.center_x - 75, 85, 150, 135),
                4: (895, 95, 155, 135),
                5: (1075, 300, 160, 135)
            }

    def get_player_coords(self, player_id: int):
        if player_id == 0:
            return (self.center_x, self.human_seat_y)
        if player_id in self.seat_positions:
            bx, by, bw, bh = self.seat_positions[player_id]
            return (bx + bw // 2, by + bh // 2)
        return (self.center_x, self.center_y)

    def trigger_turn_transition(self, player):
        """
        Activates the Premier Turn Transition System:
        - Theatrical spotlight beam on the active player
        - Golden turn transition banner with 750ms readable visual cue
        - Crisp sound chime 'turn_fanfare'
        """
        self.turn_transition_target_player = player
        self.turn_transition_timer_ms = 750
        self.current_turn_player = player
        self.sound.play('turn_fanfare')

    def init_buttons(self):
        # 1. Preliminary Order Button
        self.btn_draw_order = Button(self.center_x - 130, 485, 260, 48, "سحب كروت الأسبقية 🎴", BTN_SUCCESS, self.on_draw_order_clicked)

        # 2. Progressive Betting / Dealing Buttons
        self.btn_hold_play = Button(self.center_x - 220, 718, 200, 46, "بدء اللعب (Hold)", BTN_PRIMARY, self.on_hold_play_clicked, icon="▶")
        self.btn_raise_card = Button(self.center_x + 20, 718, 220, 46, "زيادة وتوزيع كرت (+100)", BTN_SUCCESS, self.on_raise_card_clicked, icon="💰")

        # 3. Main 5 Rounds Buttons (Differentiated styles: Safe vs High Risk)
        # Safe/Routine: Pass
        self.btn_pass = Button(115, 720, 115, 45, "تمرير", BTN_PRIMARY, self.on_pass_clicked, icon="⏩")
        # Standard Swap
        self.btn_discard = Button(240, 720, 155, 45, "استبدال علني", BTN_SUCCESS, self.on_discard_clicked, icon="🔄")
        # High Risk Gambit: Blind Swap
        self.btn_blind = Button(405, 720, 160, 45, "مبادلة الأعمى", BTN_PURPLE, self.on_blind_clicked, icon="🎲")
        # Sabotage Joker Button
        self.btn_joker = Button(575, 720, 180, 45, "مناورة الجوكر", (147, 51, 234), self.on_joker_clicked, icon="🃏")
        # Danger / Elimination Risk: All-In Steal
        self.btn_steal = Button(765, 720, 180, 45, "سرقة انتحارية!", BTN_DANGER, self.on_steal_clicked, icon="⚔️")
        # Fold / Withdraw
        self.btn_fold = Button(955, 720, 120, 45, "انسحاب", BTN_SLATE, self.on_fold_clicked, icon="🏳️")

        # Top Bar Utility Buttons
        self.btn_fullscreen = Button(20, 18, 140, 36, "شاشة كاملة (F11)", (30, 70, 90), self.toggle_fullscreen, icon="🖥️")
        self.btn_rules = Button(170, 18, 125, 36, "دليل القواعد", (40, 50, 70), self.toggle_rules_modal, icon="📜")
        self.btn_card_matrix = Button(305, 18, 150, 36, "خريطة الـ 60", (20, 60, 100), self.toggle_card_matrix_modal, icon="🃏")
        self.btn_player_count = Button(465, 18, 145, 36, "عدد اللاعبين", (79, 70, 229), self.toggle_player_select_modal, icon="👥")
        self.btn_toggle_chances = Button(self.virtual_width - 170, 18, 145, 36, "شروط الفوز", GOLD_DARK, self.toggle_chances_drawer, icon="📊")

        # Player Count Selection Modal Buttons
        self.init_player_mode_buttons()

        # Victory / Defeat Modal Action Button
        self.btn_next_round = Button(self.center_x - 120, 530, 240, 52, "جولة جديدة 🏆", BTN_SUCCESS, self.on_next_round_clicked)

    def init_player_mode_buttons(self):
        self.btn_select_mode_buttons = []
        modes = [
            (2, "1 ضد 1 (مبارزة ثنائية ⚔️)", "مواجهة مباشرة وتحدي سريع بينك وبين الذكاء الاصطناعي"),
            (3, "3 لاعبين (طاولة ثلاثية 🎯)", "منافسة تكتيكية سريعة ومثيرة"),
            (4, "4 لاعبين (طاولة رباعية ♠)", "توازن ممتاز ومساحة استراتيجية واسعة"),
            (5, "5 لاعبين (النظام القياسي الرسمي ⭐)", "التجربة الكلاسيكية الكاملة لـ 5 لاعبين"),
            (6, "6 لاعبين (طاولة ملكية سداسية 👑)", "أقصى درجات الإثارة والرهانات الضخمة والمفاجآت"),
        ]
        start_y = 190
        for i, (count, title, desc) in enumerate(modes):
            btn = Button(
                self.center_x - 240, start_y + i * 65, 480, 50,
                title,
                (37, 99, 235) if count == self.num_players_mode else (30, 41, 59),
                callback=lambda c=count: self.set_player_count_mode(c)
            )
            self.btn_select_mode_buttons.append((btn, count, desc))

    def set_player_count_mode(self, count: int):
        self.sound.play('chip')
        self.num_players_mode = count
        self.show_player_select_modal = False
        self.game = GameState(num_players=self.num_players_mode)
        self.init_natural_table_layout()
        self.init_player_mode_buttons()
        self.start_game_lifecycle()

    def toggle_player_select_modal(self):
        self.sound.play('card_click')
        self.show_player_select_modal = not self.show_player_select_modal
        if self.show_player_select_modal:
            self.show_rules_modal = False
            self.show_card_matrix_modal = False

    def toggle_rules_modal(self):
        self.sound.play('card_click')
        self.show_rules_modal = not self.show_rules_modal
        if self.show_rules_modal:
            self.show_card_matrix_modal = False

    def toggle_card_matrix_modal(self):
        self.sound.play('card_click')
        self.show_card_matrix_modal = not self.show_card_matrix_modal
        if self.show_card_matrix_modal:
            self.show_rules_modal = False

    def toggle_chances_drawer(self):
        self.sound.play('card_click')
        self.show_chances_drawer = not self.show_chances_drawer

    def start_game_lifecycle(self):
        self.game.start_new_round()
        self.is_human_winner = False
        self.earned_pot_display = 0
        self.target_pot_display = 0
        self.victory_confetti_spawned = False
        self.announcement.show(
            "تحديد أسبقية وترتيب الأدوار",
            "يسحب كل لاعب كرتاً عشوائياً: صاحب أصغر كرت يلعب أولاً!",
            2800, GOLD
        )

    def on_draw_order_clicked(self):
        if self.is_processing_steps:
            return
        self.sound.play('card_deal')
        self.game.determine_turn_order()

        # Flying cards animation with arc and rotation
        for p in self.game.active_players():
            tx, ty = self.get_player_coords(p.player_id)
            anim = CardAnimation(
                card=p.preliminary_card,
                start_pos=self.deck_pos,
                target_pos=(tx - 36, ty - 50),
                duration_ms=520,
                is_face_down=False
            )
            self.animations.append(anim)

        first_player = self.game.turn_order_players[0]
        self.trigger_turn_transition(first_player)
        self.announcement.show(
            f"الأسبقية للأصغر: {first_player.name} ({first_player.preliminary_card.display_name()})",
            f"هو الأول في التحرك! وتم توزيع الكرت السري الأول لكل لاعب.",
            3200, (34, 197, 94)
        )

    def on_hold_play_clicked(self):
        if self.is_processing_steps:
            return
        self.sound.play('card_deal')
        self.announcement.show(
            "تم الاتفاق على بدء اللعب!",
            "يوزع الموزع بقية الكروت الثلاثة وتبدأ الجولة الأولى فوراً.",
            2400, (34, 197, 94)
        )
        self.game.start_main_game_rounds()
        self.trigger_dealing_animations()
        if self.game.turn_order_players:
            self.trigger_turn_transition(self.game.turn_order_players[0])

    def on_raise_card_clicked(self):
        if self.is_processing_steps:
            return
        human = self.game.players[0]
        if human.chips < 100:
            self.sound.play('defeat')
            self.announcement.show("عجز مالي!", "رصيدك لا يكفي لإضافة 100 عملة", 1800, COLOR_IMPOSSIBLE)
            return

        if self.game.current_bet_target + 100 > 400:
            self.sound.play('chip')
            self.announcement.show("سقف الرهان الإلزامي 4X!", "وصل الرهان إلى 400 عملة وتبدأ الجولات الآن!", 2200, GOLD)
            self.game.start_main_game_rounds()
            self.trigger_dealing_animations()
            if self.game.turn_order_players:
                self.trigger_turn_transition(self.game.turn_order_players[0])
            return

        self.sound.play('chip')
        human.chips -= 100
        human.bet += 100
        self.game.pot += 100
        self.game.current_bet_target += 100

        # Flying chips from human to pot
        hx, hy = self.get_player_coords(0)
        self.particles.spawn_flying_chips((hx, hy - 40), self.pot_pos, count=5)

        for p in self.game.active_players():
            if not p.is_human:
                if p.chips >= 100:
                    p.chips -= 100
                    p.bet += 100
                    self.game.pot += 100
                    px, py = self.get_player_coords(p.player_id)
                    self.particles.spawn_flying_chips((px, py), self.pot_pos, count=4)
                else:
                    p.is_eliminated = True
                    px, py = self.get_player_coords(p.player_id)
                    self.trigger_elimination_effects((px, py))
                    self.announcement.show(f"عجز مالي: {p.name}", "تم إقصاؤه لعدم قدرته على مجاراة الرفع!", 2000, COLOR_IMPOSSIBLE)

        self.game.deal_progressive_card()
        self.sound.play('card_deal')

        # Animate new card
        for p in self.game.active_players():
            tx, ty = self.get_player_coords(p.player_id)
            new_card = p.cards[-1]
            anim = CardAnimation(
                card=new_card,
                start_pos=self.deck_pos,
                target_pos=(tx - 36, ty - 50),
                duration_ms=900,
                arc_height=100.0,
                is_face_down=(p.player_id != 0)
            )
            self.animations.append(anim)

        if self.game.cards_dealt_to_players >= 3 or self.game.current_bet_target >= 400:
            self.announcement.show(
                f"اكتملت الكروت الـ 3 (الرهان {self.game.current_bet_target})!",
                "انتقلت المباراة فوراً للجولة الأولى الرسمية!",
                2600, GOLD
            )
            self.game.start_main_game_rounds()
            if self.game.turn_order_players:
                self.trigger_turn_transition(self.game.turn_order_players[0])
        else:
            self.announcement.show(
                f"زيادة الرهان إلى {self.game.current_bet_target} عملة!",
                f"استلم الجميع الكرت رقم {self.game.cards_dealt_to_players}. هل تزيد أم تبدأ اللعب؟",
                2500, (34, 197, 94)
            )

    def trigger_dealing_animations(self):
        for p in self.game.active_players():
            tx, ty = self.get_player_coords(p.player_id)
            for card in p.cards:
                anim = CardAnimation(
                    card=card,
                    start_pos=self.deck_pos,
                    target_pos=(tx - 36, ty - 50),
                    duration_ms=900,
                    arc_height=100.0,
                    is_face_down=(p.player_id != 0)
                )
                self.animations.append(anim)

    def on_pass_clicked(self):
        if self.is_processing_steps:
            return
        human = self.game.players[0]
        self.sound.play('card_click')
        self.announcement.show(f"تمرير الدور: {human.name}", "تم إنهاء الدور دون تبديل", 1400)
        self.game.log(f"قام {human.name} بتمرير الدور.")
        self.queue_ai_playing_turns()

    def on_discard_clicked(self):
        if self.is_processing_steps:
            return
        human = self.game.players[0]
        if human.swaps_left <= 0:
            self.sound.play('defeat')
            self.announcement.show("استنفدت التبديل!", "الحد الأقصى هو مرتان طوال اللعبة", 1800, COLOR_IMPOSSIBLE)
            return
        if human.swapped_this_turn:
            self.sound.play('defeat')
            self.announcement.show("تبديل واحد فقط!", "لا يحق التبديل أكثر من مرة في نفس الدور", 1800, COLOR_IMPOSSIBLE)
            return
        if self.selected_card_index < 0 or self.selected_card_index >= len(human.cards):
            self.sound.play('card_click')
            self.announcement.show("اختر كرت أولاً!", "انقر على كرت بيدك بالأسفل لتحديده للاستبدال", 1800, GOLD)
            return

        old_card = human.cards[self.selected_card_index]
        card_start_x = (self.center_x - (len(human.cards) * 88) // 2) + self.selected_card_index * 88
        
        # Discard animation flying to center
        self.sound.play('card_swoosh')
        discard_anim = CardAnimation(
            card=old_card,
            start_pos=(card_start_x, self.human_seat_y),
            target_pos=(self.center_x - 36, self.center_y - 40),
            duration_ms=900,
            arc_height=110.0,
            is_face_down=False
        )
        self.animations.append(discard_anim)

        success = self.game.player_discard_and_draw(human, self.selected_card_index)
        if success:
            new_card = human.cards[-1]
            draw_anim = CardAnimation(
                card=new_card,
                start_pos=self.deck_pos,
                target_pos=(card_start_x, self.human_seat_y),
                duration_ms=900,
                arc_height=100.0,
                is_face_down=False
            )
            self.animations.append(draw_anim)

            self.announcement.show(
                f"استبدال علني من {human.name}!",
                f"كشف واستبعد: [{old_card.display_name()}] وسحب ورقة جديدة",
                2200, (34, 197, 94)
            )
            self.selected_card_index = -1
            self.queue_ai_playing_turns()

    def on_steal_clicked(self):
        if self.is_processing_steps:
            return
        human = self.game.players[0]
        if self.selected_target_id <= 0:
            self.sound.play('card_click')
            self.announcement.show("حدد الهدف أولاً!", "انقر على مربع أحد اللاعبين لاستهدافه بالسرقة الانتحارية", 2000, GOLD)
            return

        target = self.game.players[self.selected_target_id]
        self.queue_steal_sequence(human, target)

    def queue_steal_sequence(self, stealer, victim):
        """5-Stage sequenced steal choreography allowing the player to observe every step cleanly."""
        self.step_queue.clear()
        self.is_processing_steps = True
        self.step_timer_ms = 0
        
        # Stage 1: Target spotlight & dramatic fanfare
        self.step_queue.append({
            "type": "STEAL_STAGE_1_ALERT",
            "stealer": stealer,
            "victim": victim
        })
        # Stage 2: Stealer hand glides to victim
        self.step_queue.append({
            "type": "STEAL_STAGE_2_GIVE_CARDS",
            "stealer": stealer,
            "victim": victim
        })
        # Stage 3: Victim cards glide back to stealer
        self.step_queue.append({
            "type": "STEAL_STAGE_3_TAKE_CARDS",
            "stealer": stealer,
            "victim": victim
        })
        # Stage 4: Dealer cards flip sequentially
        self.step_queue.append({
            "type": "STEAL_STAGE_4_DEALER_FLIP",
            "stealer": stealer,
            "victim": victim
        })
        # Stage 5: Final evaluation and shockwave/fanfare
        self.step_queue.append({
            "type": "STEAL_STAGE_5_EVALUATE",
            "stealer": stealer,
            "victim": victim
        })

    def on_blind_clicked(self):
        if self.is_processing_steps:
            return
        human = self.game.players[0]
        if self.selected_target_id <= 0:
            self.sound.play('card_click')
            self.announcement.show("حدد الهدف أولاً!", "انقر على مربع أحد اللاعبين لاستهدافه بالمبادلة العمياء", 2000, GOLD)
            return

        target = self.game.players[self.selected_target_id]
        hx, hy = self.get_player_coords(0)
        tx, ty = self.get_player_coords(target.player_id)

        # Cross swap card animations with elegant parabolic arcs
        self.sound.play('card_swoosh')
        if human.cards and target.cards:
            self.animations.append(CardAnimation(human.cards[0], (hx - 36, hy), (tx - 36, ty), duration_ms=900, arc_height=110.0, is_face_down=True))
            self.animations.append(CardAnimation(target.cards[0], (tx - 36, ty), (hx - 36, hy), duration_ms=900, arc_height=110.0, is_face_down=False))

        # Sacrificed cards fly to discard pile
        for c in human.cards[1:]:
            self.animations.append(CardAnimation(c, (hx - 36, hy), (self.center_x - 36, self.center_y - 40), duration_ms=900, arc_height=120.0, is_face_down=False))

        success, msg = self.game.player_blind_swap(human, target)
        if success:
            self.sound.play('steal')
            card_kept = human.cards[0]
            self.announcement.show(
                "🎲 مبادلة الكرت الأعمى والتضحية باليد!",
                f"تخلى {human.name} عن يده واحتفظ بـ [{card_kept.display_name()}] فقط (يُحسب x3)!",
                2800, (168, 85, 247)
            )
            self.queue_ai_playing_turns()

    def on_joker_clicked(self):
        if self.is_processing_steps:
            return
        human = self.game.players[0]
        has_joker = any(c.is_joker for c in human.cards)
        if not has_joker:
            self.sound.play('defeat')
            self.announcement.show("لا تملك جوكر!", "مناورة الجوكر تتطلب وجود كرت الجوكر 🃏 بيدك", 1800, COLOR_IMPOSSIBLE)
            return

        # Need human to have selected a regular card to give to dealer
        # and a target dealer card
        if self.selected_card_index < 0 or self.selected_card_index >= len(human.cards):
            self.sound.play('card_click')
            self.announcement.show("اختر كرتك البديل!", "انقر على كرت عادي بيدك لتقديمه للموزع بدلاً من كرته", 2000, GOLD)
            return

        if human.cards[self.selected_card_index].is_joker:
            self.sound.play('defeat')
            self.announcement.show("اختر كرت غير الجوكر!", "عليك تقديم كرت عادي من يدك للموزع", 1800, COLOR_IMPOSSIBLE)
            return

        visible_count = min(self.game.current_round, 5)
        if visible_count == 0:
            self.sound.play('defeat')
            self.announcement.show("لا يوجد كرت مكشوف!", "الموزع لم يكشف أي كرت بعد للتبديل", 1800, COLOR_IMPOSSIBLE)
            return

        # Target the latest revealed dealer card or selected
        target_dealer_idx = getattr(self, 'selected_dealer_card_index', visible_count - 1)
        if target_dealer_idx >= visible_count:
            target_dealer_idx = visible_count - 1

        chosen_card = human.cards[self.selected_card_index]
        old_dealer_card = self.game.dealer_cards[target_dealer_idx]

        # Animate exchange: chosen card flies to dealer slot, old dealer card and joker fly to discard
        hx, hy = self.get_player_coords(0)
        dx, dy = self.dealer_cards_pos[target_dealer_idx]
        self.sound.play('card_swoosh')
        self.animations.append(CardAnimation(chosen_card, (hx - 36, hy), (dx, dy), duration_ms=900, arc_height=110.0, is_face_down=False))
        self.animations.append(CardAnimation(old_dealer_card, (dx, dy), (self.center_x - 36, self.center_y - 40), duration_ms=900, arc_height=100.0, is_face_down=False))

        success, msg = self.game.player_play_joker(human, self.selected_card_index, target_dealer_idx)
        if success:
            self.sound.play('steal')
            self.announcement.show(
                "🃏 مناورة الجوكر التخريبية!",
                f"استبدلت كرت الموزع [{old_dealer_card.display_name()}] بـ [{chosen_card.display_name()}] وسحبت ورقتين!",
                3000, (147, 51, 234)
            )
            self.selected_card_index = -1
            self.queue_ai_playing_turns()

    def on_fold_clicked(self):
        if self.is_processing_steps:
            return
        human = self.game.players[0]
        self.sound.play('defeat')
        refund = self.game.player_fold(human)
        self.announcement.show(
            f"🏳️ انسحاب {human.name}!",
            f"استرداد نصف الرهان ({refund} عملة) وبقاء النصف الآخر في الوعاء",
            2400, (148, 163, 184)
        )
        self.advance_round_after_turns()

    def trigger_steal_dealer_reveal(self):
        """Dramatic sequential 3D flip animation of unrevealed dealer cards on Steal!"""
        for idx in range(self.game.current_round, 5):
            pos = self.dealer_cards_pos[idx]
            card = self.game.dealer_cards[idx]
            flip_anim = CardFlipAnimation(card, pos, duration_ms=500 + (idx - self.game.current_round) * 200, width=68, height=98)
            self.animations.append(flip_anim)

    def queue_ai_playing_turns(self):
        order = [p for p in self.game.turn_order_players if not p.is_human and not p.is_eliminated and not p.is_folded]
        for p in order:
            self.step_queue.append({
                "type": "AI_PLAY_DECISION",
                "player": p
            })
        self.step_queue.append({"type": "ADVANCE_ROUND"})
        self.is_processing_steps = True

    def process_step_queue(self, dt_ms: int):
        if not self.step_queue:
            self.is_processing_steps = False
            self.current_turn_player = None
            return

        # Keep current turn player updated for glowing halo
        if self.step_queue and self.step_queue[0]["type"] == "AI_PLAY_DECISION":
            self.current_turn_player = self.step_queue[0]["player"]

        self.step_timer_ms += dt_ms
        # Responsive pacing: 750ms between AI turns
        if self.step_timer_ms >= 750:
            self.step_timer_ms = 0
            step = self.step_queue.pop(0)
            stype = step["type"]

            if stype == "AI_PLAY_DECISION":
                p = step["player"]
                self.current_turn_player = p
                self.trigger_turn_transition(p)
                action = GameAI.decide_play_action(p, self.game)
                atype = action["type"]
                px, py = self.get_player_coords(p.player_id)

                if atype == "PASS":
                    self.sound.play('card_click')
                    self.announcement.show(f"تمرير الدور: {p.name}", "فضل الاحتفاظ بأوراقه", 1200)
                elif atype == "DISCARD_DRAW":
                    old_c = p.cards[action["card_index"]]
                    anim = CardAnimation(
                        card=old_c,
                        start_pos=(px - 36, py - 50),
                        target_pos=(self.center_x - 36, self.center_y - 40),
                        duration_ms=900,
                        arc_height=110.0,
                        is_face_down=False
                    )
                    self.animations.append(anim)
                    self.sound.play('card_swoosh')
                    self.game.player_discard_and_draw(p, action["card_index"])
                    self.announcement.show(
                        f"استبدال علني من {p.name}!",
                        f"كشف واستبعد [{old_c.display_name()}] وسحب ورقة بديلة",
                        1800, (34, 197, 94)
                    )
                elif atype == "STEAL":
                    target = self.game.players[action["target_id"]]
                    self.queue_steal_sequence(p, target)
                elif atype == "BLIND_SWAP":
                    target = self.game.players[action["target_id"]]
                    tx, ty = self.get_player_coords(target.player_id)

                    # Dynamic cards crossing paths with parabolic arc
                    self.sound.play('card_swoosh')
                    if p.cards and target.cards:
                        self.animations.append(CardAnimation(p.cards[0], (px - 20, py), (tx - 20, ty), duration_ms=900, arc_height=110.0, is_face_down=True))
                        self.animations.append(CardAnimation(target.cards[0], (tx - 20, ty), (px - 20, py), duration_ms=900, arc_height=110.0, is_face_down=True))

                    # Sacrificed cards fly to table center discard
                    for c in p.cards[1:]:
                        self.animations.append(CardAnimation(c, (px - 20, py), (self.center_x - 36, self.center_y - 40), duration_ms=900, arc_height=120.0, is_face_down=False))

                    self.sound.play('steal')
                    self.game.player_blind_swap(p, target)
                    self.announcement.show(
                        f"🎲 تضحية باليد من {p.name}!",
                        f"سحب كرت أعمى من {target.name} وتخلى عن بقية يده (كرت وحيد x3)!",
                        2200, (168, 85, 247)
                    )
                elif atype == "FOLD":
                    self.sound.play('card_click')
                    self.game.player_fold(p)
                    self.announcement.show(f"🏳️ انسحب {p.name}!", "استرد نصف رهانه وبقي النصف في الوعاء", 1600)

            elif stype == "STEAL_STAGE_1_ALERT":
                stealer = step["stealer"]
                victim = step["victim"]
                self.current_turn_player = stealer
                self.trigger_turn_transition(stealer)
                self.sound.play('steal')
                self.announcement.show(
                    f"⚠️ محاولة سرقة انتحارية من {stealer.name}!",
                    f"الهدف: {victim.name} — سيتم تبادل الأوراق بالكامل وكشف كروت الموزع!",
                    1800, COLOR_POSSIBLE
                )

            elif stype == "STEAL_STAGE_2_GIVE_CARDS":
                stealer = step["stealer"]
                victim = step["victim"]
                sx, sy = self.get_player_coords(stealer.player_id)
                vx, vy = self.get_player_coords(victim.player_id)
                self.sound.play('card_swoosh')
                for idx, c in enumerate(stealer.cards):
                    self.animations.append(
                        CardAnimation(
                            card=c,
                            start_pos=(sx - 36 + idx * 24, sy),
                            target_pos=(vx - 36 + idx * 24, vy),
                            duration_ms=950,
                            arc_height=115.0,
                            is_face_down=(stealer.player_id != 0)
                        )
                    )

            elif stype == "STEAL_STAGE_3_TAKE_CARDS":
                stealer = step["stealer"]
                victim = step["victim"]
                sx, sy = self.get_player_coords(stealer.player_id)
                vx, vy = self.get_player_coords(victim.player_id)
                self.sound.play('card_swoosh')
                for idx, c in enumerate(victim.cards):
                    self.animations.append(
                        CardAnimation(
                            card=c,
                            start_pos=(vx - 36 + idx * 24, vy),
                            target_pos=(sx - 36 + idx * 24, sy),
                            duration_ms=950,
                            arc_height=115.0,
                            is_face_down=(stealer.player_id != 0)
                        )
                    )

            elif stype == "STEAL_STAGE_4_DEALER_FLIP":
                self.trigger_steal_dealer_reveal()

            elif stype == "STEAL_STAGE_5_EVALUATE":
                stealer = step["stealer"]
                victim = step["victim"]
                sx, sy = self.get_player_coords(stealer.player_id)
                won, msg = self.game.player_all_in_steal(stealer, victim)
                if won:
                    self.sound.play('victory')
                    if stealer.is_human:
                        self.is_human_winner = True
                    self.target_pot_display = stealer.chips
                    self.announcement.show(
                        f"🔥 نجحت السرقة الانتحارية ({stealer.name})!",
                        f"استولى {stealer.name} على يد {victim.name} وفاز بالوعاء كاملاً!",
                        3600, (34, 197, 94)
                    )
                    self.step_queue.clear()
                else:
                    self.trigger_elimination_effects((sx, sy))
                    self.sound.play('elimination')
                    self.announcement.show(
                        f"❌ فشلت سرقة {stealer.name}!",
                        f"تم إقصاء {stealer.name} فوراً ومصادرة أمواله وإعادة خلط الأوراق!",
                        3200, COLOR_IMPOSSIBLE
                    )
                    if self.game.phase != "ROUND_OVER":
                        self.queue_ai_playing_turns()

            elif stype == "ADVANCE_ROUND":
                self.current_turn_player = None
                self.advance_round_after_turns()

    def advance_round_after_turns(self):
        for p in self.game.players:
            p.swapped_this_turn = False

        if self.game.current_round < 5:
            self.game.current_round += 1
            idx = self.game.current_round - 1
            revealed_card = self.game.dealer_cards[idx]
            pos = self.dealer_cards_pos[idx]

            # 3D Flip animation for dealer card
            flip_anim = CardFlipAnimation(revealed_card, pos, duration_ms=520, width=68, height=98)
            self.animations.append(flip_anim)

            self.sound.play('card_deal')
            self.announcement.show(
                f"🎴 الجولة {self.game.current_round} من 5!",
                f"كشف الموزع الكرت رقم {self.game.current_round}: [{revealed_card.display_name()}]",
                2500, GOLD
            )
            self.game.log(f"--- الجولة {self.game.current_round}: كشف الموزع [{revealed_card.display_name()}] ---")
        else:
            result = self.game.check_showdown()
            self.round_result_data = result
            winners = result.get("winners", [])
            
            # Check if human is among winners
            human = self.game.players[0]
            self.is_human_winner = (human in winners)
            self.target_pot_display = human.chips
            if self.is_human_winner:
                self.sound.play('victory')
            else:
                self.sound.play('defeat')
                self.trigger_screen_shake(12, 450)

    def on_next_round_clicked(self):
        self.sound.play('card_deal')
        self.round_result_data = None
        self.selected_card_index = -1
        self.selected_target_id = -1
        self.particles.particles.clear()
        self.start_game_lifecycle()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # Window resize support
            elif event.type == pygame.VIDEORESIZE:
                if not self.is_fullscreen:
                    self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                    self.update_render_rect()

            # Fullscreen shortcut keys F11 and Alt+Enter
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    self.toggle_fullscreen()
                    continue
                elif event.key == pygame.K_RETURN and (event.mod & pygame.KMOD_ALT):
                    self.toggle_fullscreen()
                    continue

            # Map mouse event positions from window coordinates to virtual canvas (1280x800)
            if hasattr(event, "pos"):
                v_x, v_y = self.to_virtual_pos(event.pos)
                event.pos = (int(v_x), int(v_y))

            # Fullscreen Top Button
            if self.btn_fullscreen.handle_event(event):
                continue

            if self.btn_rules.handle_event(event):
                continue

            if self.btn_card_matrix.handle_event(event):
                continue

            if self.btn_player_count.handle_event(event):
                continue

            if self.btn_toggle_chances.handle_event(event):
                continue

            if self.show_player_select_modal:
                for btn, _, _ in self.btn_select_mode_buttons:
                    if btn.handle_event(event):
                        break
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # Click outside modal closes it
                    mw, mh = 620, 530
                    mx = self.center_x - mw // 2
                    my = self.center_y - mh // 2
                    if not pygame.Rect(mx, my, mw, mh).collidepoint(event.pos):
                        self.show_player_select_modal = False
                continue

            if self.show_rules_modal:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.show_rules_modal = False
                continue

            if self.show_card_matrix_modal:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.show_card_matrix_modal = False
                continue

            # Fast-forward AI steps when clicking anywhere during processing
            if self.is_processing_steps:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # Instantly trigger next queued step
                    self.step_timer_ms = 9999
                continue

            # In Round Over: Only button next round
            if self.game.phase == "ROUND_OVER":
                self.btn_next_round.handle_event(event)
                continue

            if self.game.phase == "ORDER_DETERMINATION":
                self.btn_draw_order.handle_event(event)

            elif self.game.phase == "BETTING":
                if not self.game.players[0].is_eliminated:
                    self.btn_hold_play.handle_event(event)
                    self.btn_raise_card.handle_event(event)

            elif self.game.phase == "PLAYING":
                if not self.game.players[0].is_eliminated and not self.game.players[0].is_folded:
                    self.btn_pass.handle_event(event)
                    self.btn_discard.handle_event(event)
                    self.btn_blind.handle_event(event)
                    self.btn_joker.handle_event(event)
                    self.btn_steal.handle_event(event)
                    self.btn_fold.handle_event(event)

                    # Card click selection for human
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        human = self.game.players[0]
                        start_x = self.center_x - (len(human.cards) * 88) // 2
                        y = self.human_seat_y
                        for idx, _ in enumerate(human.cards):
                            card_rect = pygame.Rect(start_x + idx * 88, y - 20, 72, 120)
                            if card_rect.collidepoint(event.pos):
                                self.selected_card_index = idx
                                self.action_message = f"تم تحديد الكرت رقم {idx + 1}."

                        # Target selection click on AI seats
                        for pid, (bx, by, bw, bh) in self.seat_positions.items():
                            p_box = pygame.Rect(bx, by, bw, bh)
                            if p_box.collidepoint(event.pos):
                                self.selected_target_id = pid
                                self.action_message = f"تم تحديد الهدف: {self.game.players[pid].name}"

    def update(self, dt_ms: int):
        real_mouse = pygame.mouse.get_pos()
        v_mx, v_my = self.to_virtual_pos(real_mouse)
        mouse_pos = (int(v_mx), int(v_my))

        # Update global animation & breathing timers
        self.global_anim_time += dt_ms / 1000.0
        self.halo_pulse_timer += dt_ms / 1000.0

        # Update turn transition banner/spotlight countdown
        if self.turn_transition_timer_ms > 0:
            self.turn_transition_timer_ms = max(0, self.turn_transition_timer_ms - dt_ms)

        # Update screen shake
        if self.shake_timer_ms > 0:
            self.shake_timer_ms = max(0, self.shake_timer_ms - dt_ms)

        # Update red flash timer
        if self.red_flash_timer_ms > 0:
            self.red_flash_timer_ms = max(0, self.red_flash_timer_ms - dt_ms)

        # Update ambient sparkling dust motes
        self.mote_manager.update(dt_ms)

        # Update buttons hover animations
        for b in [self.btn_fullscreen, self.btn_draw_order, self.btn_hold_play, self.btn_raise_card,
                  self.btn_pass, self.btn_discard, self.btn_blind, self.btn_joker, self.btn_steal,
                  self.btn_fold, self.btn_rules, self.btn_card_matrix, self.btn_player_count, self.btn_toggle_chances, self.btn_next_round]:
            b.update(dt_ms, mouse_pos)

        if self.show_player_select_modal:
            for btn, _, _ in self.btn_select_mode_buttons:
                btn.update(dt_ms, mouse_pos)

        # Update announcement
        self.announcement.update(dt_ms)

        # Update particles with dt_ms
        self.particles.update(dt_ms)

        # Update card flying and flip animations
        for anim in list(self.animations):
            anim.update(dt_ms)
            if anim.finished:
                self.animations.remove(anim)

        # Process automated AI turns
        self.process_step_queue(dt_ms)

        # Victory counting animation
        if self.game.phase == "ROUND_OVER" and self.is_human_winner:
            if not self.victory_confetti_spawned:
                self.particles.spawn_confetti(self.center_x, 280, 160)
                self.victory_confetti_spawned = True
            if self.earned_pot_display < self.target_pot_display:
                step = max(5, (self.target_pot_display - self.earned_pot_display) // 10)
                self.earned_pot_display = min(self.target_pot_display, self.earned_pot_display + step)

    def draw(self):
        real_mouse = pygame.mouse.get_pos()
        v_mx, v_my = self.to_virtual_pos(real_mouse)
        mouse_pos = (int(v_mx), int(v_my))

        # Render everything directly onto virtual surface
        self.virtual_screen.fill(BG_DARK)

        # Draw Realistic Oval Poker Table
        self.draw_casino_table()

        # Ambient floating dust motes drifting across table
        self.mote_manager.draw(self.virtual_screen)

        # Header Title
        h_txt = render_arabic("🎴 لعبة الورق الاستراتيجية الملكية | طاولة البوكر الرسمية")
        h_surf = FONT_LG.render(h_txt, True, GOLD)
        self.virtual_screen.blit(h_surf, (self.center_x - h_surf.get_width() // 2, 18))

        # Top Bar Buttons
        self.btn_fullscreen.draw(self.virtual_screen, mouse_pos)
        self.btn_rules.draw(self.virtual_screen, mouse_pos)
        self.btn_card_matrix.draw(self.virtual_screen, mouse_pos)
        self.btn_player_count.draw(self.virtual_screen, mouse_pos)
        self.btn_toggle_chances.draw(self.virtual_screen, mouse_pos)

        # 3D Stacked Chips Pot with Soft Pulsing Radial Aura
        draw_poker_chips_pot(self.virtual_screen, self.pot_pos[0], self.pot_pos[1], self.game.pot, anim_time=self.global_anim_time)

        # Current Phase / Round Sub-Header
        round_str = f"الجولة {self.game.current_round} من 5" if self.game.phase == "PLAYING" else (
            f"الرهان والتوزيع المتدرج ({self.game.cards_dealt_to_players} كروت)" if self.game.phase == "BETTING" else (
                "تحديد أسبقية الأدوار" if self.game.phase == "ORDER_DETERMINATION" else "الحسم النهائي"
            )
        )
        r_surf = FONT_MD.render(render_arabic(round_str), True, TEXT_WHITE)
        self.virtual_screen.blit(r_surf, (self.center_x - r_surf.get_width() // 2, self.center_y - 25))

        # Deck pile representation (Near Dealer)
        deck_x, deck_y = self.deck_pos
        draw_card_direct(self.virtual_screen, deck_x, deck_y, face_down=True, width=64, height=92)
        deck_lbl = FONT_XS.render(render_arabic(f"الرزمة ({len(self.game.deck)})"), True, TEXT_MUTED)
        self.virtual_screen.blit(deck_lbl, (deck_x + 32 - deck_lbl.get_width()//2, deck_y + 96))

        # 5 Dealer Cards Center with gentle prime harmonic bobbing (Skip if card is actively playing flip animation)
        active_flip_cards = [anim.card for anim in self.animations if isinstance(anim, CardFlipAnimation)]
        for i in range(5):
            x, base_y = self.dealer_cards_pos[i]
            # Gentle prime harmonic bobbing: f1=2.3Hz, f2=3.7Hz
            dealer_bob = math.sin(self.global_anim_time * 2.3 + i * 0.7) * 1.8 + math.sin(self.global_anim_time * 3.7 + i * 1.1) * 0.9
            y = int(base_y + dealer_bob)

            if i < len(self.game.dealer_cards):
                card = self.game.dealer_cards[i]
                if card in active_flip_cards:
                    continue  # Rendered dynamically by CardFlipAnimation
                is_revealed = (i < self.game.current_round) or (self.game.phase == "ROUND_OVER")
                draw_card_direct(self.virtual_screen, x, y, card=card, face_down=(not is_revealed), width=68, height=98)
            else:
                draw_card_direct(self.virtual_screen, x, y, face_down=True, width=68, height=98)

        # Draw Theatrical Turn Spotlight onto active player if turn is active
        if self.current_turn_player:
            cpx, cpy = self.get_player_coords(self.current_turn_player.player_id)
            draw_turn_spotlight(self.virtual_screen, cpx, cpy + 20, radius_x=125, radius_y=75, anim_progress=1.0)
            # Bouncing golden chevron beacon above active player
            beacon_y = cpy - 90 if self.current_turn_player.is_human else cpy - 75
            draw_turn_arrow_beacon(self.virtual_screen, cpx, beacon_y, anim_time=self.global_anim_time)

        # Draw AI Players in natural oval positions
        for pid, (bx, by, bw, bh) in self.seat_positions.items():
            self.draw_ai_player_box(self.game.players[pid], bx, by, bw, bh, is_target=(self.selected_target_id == pid))

        # Check Winning Chances for Human
        human = self.game.players[0]
        visible_dealer = self.game.current_visible_dealer_cards()
        chances = analyze_winning_chances(human.cards, visible_dealer)
        has_achieved_condition = any(c["status"] == "ACHIEVED" and c["id"] <= 5 for c in chances)

        # Draw Human Player with Hover Lift Physics
        self.draw_human_player(mouse_pos, glow_green=has_achieved_condition)

        # Action Phase Controls
        self.draw_phase_controls(mouse_pos)

        # Draw Flying Card Animations (and 3D flips)
        for anim in self.animations:
            anim.draw(self.virtual_screen)

        # Draw Particles (Confetti, flying chips, shockwaves)
        self.particles.draw(self.virtual_screen)

        # Theatrical Sweeping Golden Turn Transition Banner (750ms readable cue)
        if self.turn_transition_timer_ms > 0 and self.turn_transition_target_player:
            tt_ratio = self.turn_transition_timer_ms / 750.0
            tt_alpha = int(240 * math.sin(tt_ratio * math.pi))
            tb_w, tb_h = 560, 60
            tb_x = (self.width - tb_w) // 2
            tb_y = 210
            tb_surf = pygame.Surface((tb_w, tb_h), pygame.SRCALPHA)
            pygame.draw.rect(tb_surf, (15, 23, 42, tt_alpha), tb_surf.get_rect(), border_radius=14)
            pygame.draw.rect(tb_surf, (245, 197, 24, tt_alpha), tb_surf.get_rect(), width=2, border_radius=14)
            self.virtual_screen.blit(tb_surf, (tb_x, tb_y))
            p_name = self.turn_transition_target_player.name
            cue_txt = render_arabic(f"⚔️ دور اللاعب: {p_name} ⚔️")
            cue_s = FONT_LG.render(cue_txt, True, GOLD_BRIGHT)
            cue_s.set_alpha(tt_alpha)
            self.virtual_screen.blit(cue_s, (self.center_x - cue_s.get_width() // 2, tb_y + 14))

        # Center Announcement Banner
        self.announcement.draw(self.virtual_screen, self.width, self.height)

        # Collapsible Winning Hands Drawer (HUD)
        if self.show_chances_drawer:
            self.draw_chances_drawer(chances)

        # Victory / Defeat Modal (Professional Showdown Screen)
        if self.game.phase == "ROUND_OVER":
            self.draw_showdown_screen(mouse_pos)

        # Rules Modal Overlay
        if self.show_rules_modal:
            self.draw_rules_modal()

        # 56-Cards Matrix Modal (Faded unknown / Glowing revealed)
        if self.show_card_matrix_modal:
            known_cards = self.game.get_all_known_revealed_cards()
            draw_deck_matrix_modal(self.virtual_screen, self.width, self.height, known_cards, mouse_pos)

        # Player Count Selection Modal
        if self.show_player_select_modal:
            self.draw_player_select_modal(mouse_pos)

        # Red Flash Overlay on elimination/defeat
        if self.red_flash_timer_ms > 0:
            alpha = int((self.red_flash_timer_ms / 350.0) * 110)
            flash_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            flash_surf.fill((220, 38, 38, max(0, min(255, alpha))))
            self.virtual_screen.blit(flash_surf, (0, 0))

        # Screen Shake Offset calculation
        shake_x, shake_y = 0, 0
        if self.shake_timer_ms > 0:
            shake_x = random.randint(-self.shake_magnitude, self.shake_magnitude)
            shake_y = random.randint(-self.shake_magnitude, self.shake_magnitude)

        # Render Virtual Surface to Display Screen with Letterboxing and Shake
        self.screen.fill((10, 14, 23))  # Deep letterbox border color
        scaled_surf = pygame.transform.smoothscale(self.virtual_screen, (self.render_rect.width, self.render_rect.height))
        dest_x = self.render_rect.x + shake_x
        dest_y = self.render_rect.y + shake_y
        self.screen.blit(scaled_surf, (dest_x, dest_y))

        pygame.display.flip()

    def draw_casino_table(self):
        # Felt Table on virtual_screen
        t_rect = pygame.Rect(70, 70, self.width - 140, 580)
        pygame.draw.ellipse(self.virtual_screen, TABLE_WOOD_RIM, t_rect)
        pygame.draw.ellipse(self.virtual_screen, TABLE_GOLD_TRIM, t_rect.inflate(-14, -14), width=3)
        
        # Metallic Specular Gleam traveling along the gold table rim
        t_gleam = self.global_anim_time * 0.45
        gleam_angle = (t_gleam % 1.0) * math.pi * 2.0
        rx = (self.width - 140 - 14) / 2.0
        ry = (580 - 14) / 2.0
        gleam_cx = 70 + 7 + rx + math.cos(gleam_angle) * rx
        gleam_cy = 70 + 7 + ry + math.sin(gleam_angle) * ry
        gleam_surf = pygame.Surface((60, 60), pygame.SRCALPHA)
        pygame.draw.circle(gleam_surf, (255, 255, 255, 120), (30, 30), 18)
        pygame.draw.circle(gleam_surf, (255, 235, 120, 200), (30, 30), 8)
        self.virtual_screen.blit(gleam_surf, (int(gleam_cx - 30), int(gleam_cy - 30)))

        inner_felt = t_rect.inflate(-26, -26)
        pygame.draw.ellipse(self.virtual_screen, TABLE_FELT_EDGE, inner_felt)
        center_felt = inner_felt.inflate(-36, -36)
        pygame.draw.ellipse(self.virtual_screen, TABLE_FELT_CENTER, center_felt)
        pygame.draw.ellipse(self.virtual_screen, (25, 115, 75), center_felt.inflate(-20, -20), width=2)

    def draw_ai_player_box(self, player: Player, x: int, y: int, w: int, h: int, is_target: bool = False):
        bg_col = (20, 30, 48) if not is_target else (120, 53, 15)
        border_col = GOLD if is_target else (55, 65, 81)

        # Pulsing turn halo ring if currently active turn
        is_turn = (self.current_turn_player == player)
        if is_turn:
            pulse_val = 0.5 + 0.5 * math.sin(self.halo_pulse_timer * 6.0)
            glow_thickness = int(3 + pulse_val * 4)
            glow_color = (250, 204, 21)  # Vivid yellow-gold
            glow_rect = pygame.Rect(x - glow_thickness, y - glow_thickness, w + glow_thickness * 2, h + glow_thickness * 2)
            pygame.draw.rect(self.virtual_screen, glow_color, glow_rect, width=glow_thickness, border_radius=12)

        # Drop shadow
        pygame.draw.rect(self.virtual_screen, (0, 0, 0, 90), (x + 3, y + 4, w, h), border_radius=10)
        # Main box
        pygame.draw.rect(self.virtual_screen, bg_col, (x, y, w, h), border_radius=10)
        pygame.draw.rect(self.virtual_screen, border_col, (x, y, w, h), width=2 if is_target else 1, border_radius=10)

        # Name and Turn Order
        status = " (مُقصى ❌)" if player.is_eliminated else (" (منسحب 🏳️)" if player.is_folded else "")
        order_tag = f"#{player.turn_order_rank} " if player.turn_order_rank > 0 else ""
        n_surf = FONT_SM.render(render_arabic(order_tag + player.name + status), True, TEXT_WHITE)
        self.virtual_screen.blit(n_surf, (x + w//2 - n_surf.get_width()//2, y + 8))

        # Chips & Bet
        c_surf = FONT_XS.render(render_arabic(f"الرصيد: {player.chips} 💰"), True, GOLD)
        self.virtual_screen.blit(c_surf, (x + w//2 - c_surf.get_width()//2, y + 28))

        b_surf = FONT_XS.render(render_arabic(f"الرهان: {player.bet}"), True, TEXT_MUTED)
        self.virtual_screen.blit(b_surf, (x + w//2 - b_surf.get_width()//2, y + 45))

        # Cards
        card_start = x + (w - (len(player.cards) * 40)) // 2
        card_y = y + 68
        show_all = (self.game.phase == "ROUND_OVER")
        for i, c in enumerate(player.cards):
            draw_card_direct(self.virtual_screen, card_start + i * 40, card_y, card=c, face_down=(not show_all), width=36, height=52)

    def draw_human_player(self, mouse_pos, glow_green: bool = False):
        human = self.game.players[0]
        y = self.human_seat_y
        center_x = self.center_x

        # Check if it's human's active turn to show glowing halo
        is_human_turn = (self.game.phase in ["ORDER_DETERMINATION", "BETTING"]) or (
            self.game.phase == "PLAYING" and not self.is_processing_steps and not human.is_eliminated and not human.is_folded
        )

        # Player Header Banner
        order_tag = f"الأسبقية: #{human.turn_order_rank} | " if human.turn_order_rank > 0 else ""
        info_txt = render_arabic(f"أنت ({order_tag}الرصيد: {human.chips} 💰 | رهانك: {human.bet} | تبديلات: {human.swaps_left})")
        info_surf = FONT_MD.render(info_txt, True, TEXT_WHITE)
        
        bw = info_surf.get_width() + 40
        bh = 36
        bx = center_x - bw // 2
        by = y - 46

        # Active turn pulsing halo
        if is_human_turn:
            pulse_val = 0.5 + 0.5 * math.sin(self.halo_pulse_timer * 6.0)
            glow_thick = int(2 + pulse_val * 4)
            halo_rect = pygame.Rect(bx - glow_thick, by - glow_thick, bw + glow_thick * 2, bh + glow_thick * 2)
            pygame.draw.rect(self.virtual_screen, (250, 204, 21), halo_rect, width=glow_thick, border_radius=20)

        pygame.draw.rect(self.virtual_screen, (15, 23, 42, 230), (bx, by, bw, bh), border_radius=18)
        border_col = COLOR_ACHIEVED if glow_green else GOLD
        pygame.draw.rect(self.virtual_screen, border_col, (bx, by, bw, bh), width=2 if glow_green else 1, border_radius=18)
        self.virtual_screen.blit(info_surf, (center_x - info_surf.get_width()//2, by + 6))

        # Winning condition achieved special alert badge
        if glow_green:
            achieve_rect = pygame.Rect(center_x - 140, by - 36, 280, 30)
            pygame.draw.rect(self.virtual_screen, (20, 83, 45), achieve_rect, border_radius=8)
            pygame.draw.rect(self.virtual_screen, COLOR_ACHIEVED, achieve_rect, width=2, border_radius=8)
            t = render_arabic("🌟 حققت شرط فوز استثنائي الآن! 🌟")
            ts = FONT_SM.render(t, True, (240, 253, 244))
            self.virtual_screen.blit(ts, (achieve_rect.centerx - ts.get_width()//2, achieve_rect.y + 6))

        # Human Cards with Hover Lift Physics & Gentle Idle Breathing Bobbing!
        start_x = center_x - (len(human.cards) * 88) // 2
        for idx, card in enumerate(human.cards):
            card_x = start_x + idx * 88
            
            # Hover detection
            card_rect = pygame.Rect(card_x, y, 72, 104)
            is_hover = card_rect.collidepoint(mouse_pos)
            is_selected = (self.selected_card_index == idx)

            # Gentle breathing harmonic bobbing when unhovered
            human_card_bob = (math.sin(self.global_anim_time * 2.3 + idx * 0.8) * 1.6 +
                              math.sin(self.global_anim_time * 3.7 + idx * 1.2) * 0.8) if not (is_hover or is_selected) else 0.0

            # Card Physics: Hover LIFT 20px up with soft shadow!
            lift_y = int(y - 20 if (is_hover or is_selected) else (y + human_card_bob))

            draw_card_direct(
                self.virtual_screen, card_x, lift_y,
                card=card, face_down=False,
                is_selected=is_selected,
                width=72, height=104,
                glow_green=glow_green,
                glow_gold=is_hover
            )

    def draw_phase_controls(self, mouse_pos):
        if self.is_processing_steps:
            proc_rect = pygame.Rect(self.center_x - 120, 720, 240, 42)
            pygame.draw.rect(self.virtual_screen, (15, 23, 42), proc_rect, border_radius=8)
            pygame.draw.rect(self.virtual_screen, GOLD, proc_rect, width=1, border_radius=8)
            proc_txt = render_arabic("⏳ يجري تنفيذ الحركات... (انقر للتسريع)")
            proc_surf = FONT_MD.render(proc_txt, True, GOLD)
            self.virtual_screen.blit(proc_surf, (proc_rect.centerx - proc_surf.get_width()//2, proc_rect.centery - proc_surf.get_height()//2))
            return

        if self.game.phase == "ORDER_DETERMINATION":
            self.btn_draw_order.draw(self.virtual_screen, mouse_pos)
        elif self.game.phase == "BETTING":
            if not self.game.players[0].is_eliminated:
                self.btn_hold_play.draw(self.virtual_screen, mouse_pos)
                self.btn_raise_card.draw(self.virtual_screen, mouse_pos)
        elif self.game.phase == "PLAYING":
            if not self.game.players[0].is_eliminated and not self.game.players[0].is_folded:
                self.btn_pass.draw(self.virtual_screen, mouse_pos)
                self.btn_discard.draw(self.virtual_screen, mouse_pos)
                self.btn_blind.draw(self.virtual_screen, mouse_pos)
                self.btn_joker.draw(self.virtual_screen, mouse_pos)
                self.btn_steal.draw(self.virtual_screen, mouse_pos)
                self.btn_fold.draw(self.virtual_screen, mouse_pos)

    def draw_chances_drawer(self, chances):
        """Collapsible HUD Drawer sliding in from top-right."""
        dw, dh = 340, 360
        dx = self.width - dw - 20
        dy = 65

        drawer_s = pygame.Surface((dw, dh), pygame.SRCALPHA)
        pygame.draw.rect(drawer_s, (15, 23, 42, 245), drawer_s.get_rect(), border_radius=12)
        pygame.draw.rect(drawer_s, GOLD, drawer_s.get_rect(), width=2, border_radius=12)
        self.virtual_screen.blit(drawer_s, (dx, dy))

        title = render_arabic("🏆 جدول شروط الفوز وفرص يدك")
        ts = FONT_MD.render(title, True, GOLD_BRIGHT)
        self.virtual_screen.blit(ts, (dx + dw//2 - ts.get_width()//2, dy + 10))

        pygame.draw.line(self.virtual_screen, (51, 65, 85), (dx + 12, dy + 36), (dx + dw - 12, dy + 36), 1)

        start_y = dy + 44
        row_h = 48
        for i, item in enumerate(chances):
            cy = start_y + i * row_h
            status = item["status"]

            if status == "ACHIEVED":
                b_col = COLOR_ACHIEVED
                bg_col = (20, 83, 45, 140)
            elif status == "POSSIBLE":
                b_col = COLOR_POSSIBLE
                bg_col = (120, 53, 15, 70)
            else:
                b_col = COLOR_IMPOSSIBLE
                bg_col = (30, 41, 59, 90)

            # Row surface
            r_surf = pygame.Surface((dw - 20, row_h - 4), pygame.SRCALPHA)
            pygame.draw.rect(r_surf, bg_col, r_surf.get_rect(), border_radius=6)
            if status == "ACHIEVED":
                pygame.draw.rect(r_surf, COLOR_ACHIEVED, r_surf.get_rect(), width=1, border_radius=6)
            self.virtual_screen.blit(r_surf, (dx + 10, cy))

            # Name and Badge
            ns = FONT_SM.render(render_arabic(item["name"]), True, TEXT_WHITE)
            self.virtual_screen.blit(ns, (dx + 18, cy + 3))

            bs = FONT_SM.render(render_arabic(item["badge"]), True, b_col)
            self.virtual_screen.blit(bs, (dx + dw - bs.get_width() - 18, cy + 3))

            # Reason
            rs = FONT_XS.render(render_arabic(item["reason"]), True, TEXT_MUTED if status != "ACHIEVED" else GOLD)
            self.virtual_screen.blit(rs, (dx + 18, cy + 24))

    def draw_showdown_screen(self, mouse_pos):
        """
        Full Professional Victory / Defeat Screen:
        - Fullscreen Dark Overlay (Backdrop Blur/Tint)
        - Animated Confetti for Victory
        - 3D Gold Glow Trophy Banner for Winner
        - Animated Counting Currency Display
        - Elegant Defeat Vignette if Lost, showing exactly who defeated you and why
        """
        # Fullscreen Tint
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((5, 8, 16, 215))
        self.virtual_screen.blit(overlay, (0, 0))

        mw, mh = 720, 430
        mx = self.center_x - mw // 2
        my = self.center_y - mh // 2

        modal_s = pygame.Surface((mw, mh), pygame.SRCALPHA)

        if self.is_human_winner:
            # VICTORY SCREEN
            pygame.draw.rect(modal_s, (15, 23, 42, 245), modal_s.get_rect(), border_radius=18)
            pygame.draw.rect(modal_s, GOLD_BRIGHT, modal_s.get_rect(), width=3, border_radius=18)
            self.virtual_screen.blit(modal_s, (mx, my))

            # 3D Trophy and Gold Banner
            t_surf = FONT_HERO.render(render_arabic("🎉 نصر ساحق! فزت بالجولة 🎉"), True, GOLD_BRIGHT)
            self.virtual_screen.blit(t_surf, (self.center_x - t_surf.get_width()//2, my + 30))

            # Sub-banner
            sub_txt = render_arabic("تهانينا! حصدت كامل أموال الوعاء وتغلبت على جميع اللاعبين!")
            sub_s = FONT_MD.render(sub_txt, True, TEXT_WHITE)
            self.virtual_screen.blit(sub_s, (self.center_x - sub_s.get_width()//2, my + 95))

            # Currency Counter Animation
            coin_txt = render_arabic(f"+{self.earned_pot_display} 💰 رصيدك الإجمالي الآن")
            c_surf = FONT_XL.render(coin_txt, True, COLOR_ACHIEVED)
            self.virtual_screen.blit(c_surf, (self.center_x - c_surf.get_width()//2, my + 145))

        else:
            # DEFEAT SCREEN
            pygame.draw.rect(modal_s, (20, 10, 15, 245), modal_s.get_rect(), border_radius=18)
            pygame.draw.rect(modal_s, COLOR_IMPOSSIBLE, modal_s.get_rect(), width=3, border_radius=18)
            self.virtual_screen.blit(modal_s, (mx, my))

            t_surf = FONT_HERO.render(render_arabic("💀 خسرت هذه الجولة 💀"), True, COLOR_IMPOSSIBLE)
            self.virtual_screen.blit(t_surf, (self.center_x - t_surf.get_width()//2, my + 30))

            sub_txt = render_arabic("تفوق أحد الخصوم بيده أو لم تتأهل شروطك في الحسم النهائي")
            sub_s = FONT_MD.render(sub_txt, True, TEXT_WHITE)
            self.virtual_screen.blit(sub_s, (self.center_x - sub_s.get_width()//2, my + 95))

        # Showdown Ranking Details
        if self.round_result_data:
            results = self.round_result_data.get("results", [])
            for i, r in enumerate(results[:3]):
                p = r["player"]
                rank_col = GOLD if i == 0 else TEXT_MUTED
                p_text = f"#{i+1} {p.name}: {r['desc']}"
                p_surf = FONT_MD.render(render_arabic(p_text), True, rank_col)
                self.virtual_screen.blit(p_surf, (mx + 50, my + 210 + i * 36))

        # Next Round Button
        self.btn_next_round.rect.x = self.center_x - 120
        self.btn_next_round.rect.y = my + mh - 75
        self.btn_next_round.draw(self.virtual_screen, mouse_pos)

    def draw_rules_modal(self):
        modal = pygame.Rect(80, 40, self.width - 160, self.height - 80)
        pygame.draw.rect(self.virtual_screen, (15, 23, 42), modal, border_radius=14)
        pygame.draw.rect(self.virtual_screen, GOLD, modal, width=2, border_radius=14)

        title = render_arabic("📜 الدليل الرسمي الكامل لقواعد اللعبة (60 كرت تشمل 4 جوكر)")
        t_surf = FONT_XL.render(title, True, GOLD)
        self.virtual_screen.blit(t_surf, (modal.centerx - t_surf.get_width() // 2, modal.y + 18))

        rules_lines = [
            "1. الحزمة: 60 ورقة (4 فئات 56 كرت) + 4 كروت جوكر تكتيكية 🃏 تظهر للاعبين فقط.",
            "2. تحديد الأسبقية: سحب كرت أعمى لكل لاعب؛ أصغر كرت يبدأ اللعب أولاً، وتُعاد كروت التعادل فقط.",
            "3. الرهان والتوزيع المتدرج: رهان مبدئي 100 وتوزيع الكرت الأول، ثم خيار الزيادة (+100) حتى سقف 4X (400 عملة).",
            "4. مسار اللعب: 5 جولات متتالية، يكشف الموزع في كل منها كرتاً حتى كشف الكرت الـ 5 الأخير والحسم النهائي.",
            "5. التبديل: مرتان فقط طوال اللعبة بحد أقصى تبديل واحد في الدور مع كشف المستبعد علناً.",
            "6. مناورة الجوكر التخريبية: استبدال كرت مكشوف للموزع بكرت من يدك لإفساد خطة خصمك وسحب ورقتين جديدتين!",
            "7. حظر الجوكر وعقوبته: لا يمكن الفوز بأي شرط استثنائي إذا كان الجوكر بيدك، وتُحسب قيمته 25 نقطة عند كسر التعادل!",
            "8. الحركات الخاصة: سرقة اليد الانتحارية (فوز فوري بشرط استثنائي أو إقصاء)، ومبادلة الكرت الأعمى والتضحية (x3).",
            "9. سلم ندرة الفوز: 1- الانسجام الزوجي/الفردي | 2- السلسلة المتناوبة | 3- الحروف الخمسة | 4- الـ 48 الذهبية | 5- التطابق المزدوج (دون قيد الجوار).",
            "10. كسر التعادل: أدنى مجموع مؤهل أو استثناء الموزع الملكي (إذا كانت كروت الموزع كلها > 10 يسقط شرط الأهلية).",
            "انقر في أي مكان للإغلاق والعودة للعبة..."
        ]

        for i, line in enumerate(rules_lines):
            l_surf = FONT_SM.render(render_arabic(line), True, TEXT_WHITE if not line.startswith("انقر") else GOLD)
            self.virtual_screen.blit(l_surf, (modal.x + 30, modal.y + 65 + i * 36))

    def draw_player_select_modal(self, mouse_pos):
        """Luxury Player Count Selection Modal Dialog."""
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((5, 8, 16, 210))
        self.virtual_screen.blit(overlay, (0, 0))

        mw, mh = 620, 545
        mx = self.center_x - mw // 2
        my = self.center_y - mh // 2

        modal_s = pygame.Surface((mw, mh), pygame.SRCALPHA)
        pygame.draw.rect(modal_s, (15, 23, 42, 250), modal_s.get_rect(), border_radius=18)
        pygame.draw.rect(modal_s, GOLD, modal_s.get_rect(), width=2, border_radius=18)
        self.virtual_screen.blit(modal_s, (mx, my))

        # Title
        t_title = render_arabic("👥 اختر نظام وعدد اللاعبين على الطاولة")
        ts = FONT_XL.render(t_title, True, GOLD_BRIGHT)
        self.virtual_screen.blit(ts, (self.center_x - ts.get_width() // 2, my + 24))

        # Subtitle
        sub = render_arabic("اختر الوضع المناسب لبدء جولة جديدة فوراً مع توزيع المقاعد تلقائياً")
        subs = FONT_SM.render(sub, True, TEXT_WHITE)
        self.virtual_screen.blit(subs, (self.center_x - subs.get_width() // 2, my + 68))

        # Draw buttons and their descriptions
        for btn, count, desc in self.btn_select_mode_buttons:
            btn.draw(self.virtual_screen, mouse_pos)
            # Active badge tag
            if count == self.num_players_mode:
                badge_t = render_arabic("✓ الوضع النشط حالياً")
                bs = FONT_XS.render(badge_t, True, COLOR_ACHIEVED)
                self.virtual_screen.blit(bs, (btn.rect.right - bs.get_width() - 15, btn.rect.centery - bs.get_height() // 2))

            # Small description below button
            desc_t = render_arabic(desc)
            ds = FONT_XS.render(desc_t, True, TEXT_MUTED)
            self.virtual_screen.blit(ds, (self.center_x - ds.get_width() // 2, btn.rect.bottom + 2))

        # Close hint
        close_txt = render_arabic("انقر في أي مكان بالخارج للإلغاء والعودة للعب")
        cs = FONT_XS.render(close_txt, True, TEXT_MUTED)
        self.virtual_screen.blit(cs, (self.center_x - cs.get_width() // 2, my + mh - 26))

    def run(self):
        while True:
            dt_ms = self.clock.tick(60)
            self.handle_events()
            self.update(dt_ms)
            self.draw()

if __name__ == '__main__':
    app = CardGameApp()
    app.run()
