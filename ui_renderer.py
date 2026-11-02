import os
import pygame
import math
import random
from typing import List, Dict, Optional, Tuple

pygame.init()
pygame.font.init()

# Luxury Color Palette
BG_DARK = (8, 12, 22)             # Deep Obsidian Night
TABLE_FELT_CENTER = (16, 92, 58)  # Casino Emerald Rich Green
TABLE_FELT_EDGE = (10, 56, 36)    # Darker Green Gradient
TABLE_WOOD_RIM = (42, 24, 16)     # Mahogany Wood Border
TABLE_GOLD_TRIM = (212, 175, 55)  # Metallic Gold Accent
CARD_BG = (255, 255, 252)
CARD_BORDER = (215, 222, 232)
CARD_BACK_BASE = (26, 46, 105)
CARD_BACK_INNER = (37, 72, 160)
GOLD = (245, 197, 24)
GOLD_BRIGHT = (255, 223, 80)
GOLD_DARK = (165, 120, 10)
TEXT_WHITE = (248, 250, 252)
TEXT_MUTED = (160, 175, 195)
RED_SUIT = (225, 29, 72)
BLACK_SUIT = (15, 23, 42)

# Action button tones
BTN_PRIMARY = (37, 99, 235)
BTN_SUCCESS = (16, 185, 129)
BTN_DANGER = (225, 29, 72)
BTN_PURPLE = (147, 51, 234)
BTN_SLATE = (71, 85, 105)

# Status Badge Colors
COLOR_ACHIEVED = (34, 197, 94)
COLOR_POSSIBLE = (245, 158, 11)
COLOR_IMPOSSIBLE = (239, 68, 68)

def load_system_font(size: int, bold: bool = False):
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "Segoe UI", "Arial", "Tahoma"
    ]
    for p in candidates:
        try:
            if os.path.exists(p):
                return pygame.font.Font(p, size)
            else:
                return pygame.font.SysFont(p, size, bold=bold)
        except Exception:
            continue
    return pygame.font.Font(None, size)

FONT_XS = load_system_font(13, bold=False)
FONT_SM = load_system_font(15, bold=False)
FONT_MD = load_system_font(18, bold=True)
FONT_LG = load_system_font(23, bold=True)
FONT_XL = load_system_font(32, bold=True)
FONT_HERO = load_system_font(44, bold=True)
FONT_SUIT = load_system_font(28, bold=True)

def render_arabic(text: str) -> str:
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        reshaped = arabic_reshaper.reshape(str(text))
        return get_display(reshaped)
    except Exception:
        return str(text)

# Ambient Floating Sparkling Mote / Dust System
class AmbientMote:
    def __init__(self, bounds_rect: Tuple[int, int, int, int]):
        bx, by, bw, bh = bounds_rect
        self.bounds = bounds_rect
        self.x = random.uniform(bx, bx + bw)
        self.y = random.uniform(by, by + bh)
        self.vx = random.uniform(-0.35, 0.35)
        self.vy = random.uniform(-0.45, -0.1)
        self.base_radius = random.uniform(1.2, 3.2)
        self.phase = random.uniform(0, math.pi * 2)
        self.pulse_speed = random.uniform(1.5, 3.5)
        self.color = random.choice([
            (255, 235, 140),  # Warm starlight gold
            (255, 215, 80),   # Vibrant gold
            (190, 240, 255),  # Crystal cyan diamond
            (255, 255, 255),  # Pure diamond sparkle
            (130, 230, 180)   # Soft emerald glint
        ])
        self.life = random.randint(300, 700)
        self.max_life = self.life

    def update(self, dt_ms: int = 16):
        dt_sec = dt_ms / 1000.0
        self.phase += self.pulse_speed * dt_sec
        # Gentle natural Brownian swirl
        self.x += (self.vx + math.sin(self.phase * 0.7) * 0.25) * (dt_ms / 16.0)
        self.y += (self.vy + math.cos(self.phase * 0.9) * 0.15) * (dt_ms / 16.0)
        self.life -= 1

        bx, by, bw, bh = self.bounds
        if self.life <= 0 or self.x < bx or self.x > bx + bw or self.y < by or self.y > by + bh:
            self._respawn()

    def _respawn(self):
        bx, by, bw, bh = self.bounds
        self.x = random.uniform(bx, bx + bw)
        self.y = random.uniform(by + bh * 0.4, by + bh)  # Drift upwards from lower half
        self.life = random.randint(400, 800)
        self.max_life = self.life
        self.phase = random.uniform(0, math.pi * 2)

    def draw(self, surface: pygame.Surface):
        if self.life <= 0:
            return
        life_ratio = self.life / float(self.max_life)
        # Fade in and fade out envelope
        alpha_env = math.sin(life_ratio * math.pi)
        shimmer = (0.5 + 0.5 * math.sin(self.phase))
        alpha = int(180 * alpha_env * shimmer)
        if alpha <= 5:
            return

        r = max(1, int(self.base_radius * (0.8 + 0.4 * shimmer)))
        mote_surf = pygame.Surface((r * 4 + 4, r * 4 + 4), pygame.SRCALPHA)
        center = (r * 2 + 2, r * 2 + 2)
        # Outer soft glow aura
        pygame.draw.circle(mote_surf, (*self.color, alpha // 3), center, r * 2)
        # Inner sharp core
        pygame.draw.circle(mote_surf, (255, 255, 255, alpha), center, r)
        surface.blit(mote_surf, (int(self.x - center[0]), int(self.y - center[1])))

class AmbientMoteManager:
    def __init__(self, bounds_rect=(70, 70, 1140, 580), count: int = 35):
        self.bounds = bounds_rect
        self.motes = [AmbientMote(bounds_rect) for _ in range(count)]

    def update(self, dt_ms: int = 16):
        for m in self.motes:
            m.update(dt_ms)

    def draw(self, surface: pygame.Surface):
        for m in self.motes:
            m.draw(surface)

# Confetti Particle System for Celebratory Victory
class ConfettiParticle:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.vx = random.uniform(-4, 4)
        self.vy = random.uniform(-10, -2)
        self.gravity = random.uniform(0.18, 0.32)
        self.color = random.choice([
            (255, 215, 0), (255, 235, 120), (234, 179, 8),
            (34, 197, 94), (59, 130, 246), (236, 72, 153),
            (248, 250, 252)
        ])
        self.size = random.uniform(5, 11)
        self.angle = random.uniform(0, 360)
        self.rot_speed = random.uniform(-10, 10)
        self.life = random.randint(180, 280)
        self.max_life = self.life

    def update(self):
        self.x += self.vx
        self.vy += self.gravity
        self.y += self.vy
        self.angle += self.rot_speed
        self.life -= 1

    def draw(self, surface: pygame.Surface):
        if self.life <= 0:
            return
        alpha = int(255 * (self.life / float(self.max_life)))
        s = pygame.Surface((int(self.size), int(self.size * 0.6)), pygame.SRCALPHA)
        s.fill((*self.color, alpha))
        rotated = pygame.transform.rotate(s, self.angle)
        surface.blit(rotated, (int(self.x), int(self.y)))

class FlyingChipParticle:
    def __init__(self, start_pos: Tuple[float, float], target_pos: Tuple[float, float], duration_ms: int = 500, color=GOLD, on_complete=None):
        self.start_x, self.start_y = start_pos
        self.target_x, self.target_y = target_pos
        self.duration_ms = duration_ms
        self.elapsed_ms = 0
        self.color = color
        self.finished = False
        self.on_complete = on_complete
        self.arc_height = random.uniform(30, 60)

    def update(self, dt_ms: int):
        self.elapsed_ms += dt_ms
        if self.elapsed_ms >= self.duration_ms:
            self.elapsed_ms = self.duration_ms
            self.finished = True
            if self.on_complete:
                self.on_complete()

    def draw(self, surface: pygame.Surface):
        t = self.elapsed_ms / float(self.duration_ms) if self.duration_ms > 0 else 1.0
        t_ease = 1.0 - math.pow(1.0 - t, 3)
        arc = math.sin(t * math.pi) * self.arc_height
        curr_x = self.start_x + (self.target_x - self.start_x) * t_ease
        curr_y = (self.start_y + (self.target_y - self.start_y) * t_ease) - arc

        # Chip shadow
        pygame.draw.ellipse(surface, (0, 0, 0, 80), (int(curr_x - 10), int(curr_y + 4), 20, 10))
        # Chip body
        dark_col = tuple(max(0, int(c * 0.6)) for c in self.color)
        pygame.draw.ellipse(surface, dark_col, (int(curr_x - 10), int(curr_y - 5), 20, 10))
        pygame.draw.ellipse(surface, self.color, (int(curr_x - 9), int(curr_y - 4), 18, 8))
        pygame.draw.ellipse(surface, (255, 255, 255), (int(curr_x - 5), int(curr_y - 2), 10, 4), width=1)

class ShockwaveRing:
    def __init__(self, x: float, y: float, max_radius: float = 140, duration_ms: int = 650, color=(225, 29, 72)):
        self.x = x
        self.y = y
        self.max_radius = max_radius
        self.duration_ms = duration_ms
        self.elapsed_ms = 0
        self.color = color
        self.finished = False

    def update(self, dt_ms: int):
        self.elapsed_ms += dt_ms
        if self.elapsed_ms >= self.duration_ms:
            self.elapsed_ms = self.duration_ms
            self.finished = True

    def draw(self, surface: pygame.Surface):
        t = self.elapsed_ms / float(self.duration_ms) if self.duration_ms > 0 else 1.0
        current_radius = int(self.max_radius * (1.0 - math.pow(1.0 - t, 2)))
        alpha = int(255 * (1.0 - t))
        if current_radius <= 1 or alpha <= 0:
            return

        ring_surf = pygame.Surface((current_radius * 2 + 10, current_radius * 2 + 10), pygame.SRCALPHA)
        center = (current_radius + 5, current_radius + 5)
        ring_col = (*self.color, alpha)
        width = max(2, int(6 * (1.0 - t)))
        pygame.draw.circle(ring_surf, ring_col, center, current_radius, width=width)
        surface.blit(ring_surf, (int(self.x - center[0]), int(self.y - center[1])))

class CardFlipAnimation:
    """3D Horizontal Flip Card Reveal Animation."""
    def __init__(self, card, pos: Tuple[int, int], duration_ms: int = 550, width: int = 68, height: int = 98, on_complete=None):
        self.card = card
        self.x, self.y = pos
        self.duration_ms = duration_ms
        self.elapsed_ms = 0
        self.width = width
        self.height = height
        self.finished = False
        self.on_complete = on_complete

    def update(self, dt_ms: int):
        self.elapsed_ms += dt_ms
        if self.elapsed_ms >= self.duration_ms:
            self.elapsed_ms = self.duration_ms
            self.finished = True
            if self.on_complete:
                self.on_complete()

    def draw(self, surface: pygame.Surface):
        t = self.elapsed_ms / float(self.duration_ms) if self.duration_ms > 0 else 1.0
        # Cosine scaling for horizontal perspective squeeze
        scale_x = abs(math.cos(t * math.pi))
        curr_w = max(2, int(self.width * scale_x))
        offset_x = (self.width - curr_w) // 2
        # First half shows card back, second half shows card face
        is_face_down = (t < 0.5)

        temp_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        draw_card_direct(temp_surf, 0, 0, card=self.card, face_down=is_face_down, width=self.width, height=self.height)

        scaled_surf = pygame.transform.smoothscale(temp_surf, (curr_w, self.height))
        surface.blit(scaled_surf, (self.x + offset_x, self.y))

class ParticleManager:
    def __init__(self):
        self.particles: List[ConfettiParticle] = []
        self.flying_chips: List[FlyingChipParticle] = []
        self.shockwaves: List[ShockwaveRing] = []

    def spawn_confetti(self, center_x: int, center_y: int, count: int = 120):
        for _ in range(count):
            self.particles.append(ConfettiParticle(
                center_x + random.uniform(-150, 150),
                center_y + random.uniform(-40, 40)
            ))

    def spawn_flying_chips(self, start_pos: Tuple[float, float], target_pos: Tuple[float, float], count: int = 6):
        chip_colors = [GOLD, (239, 68, 68), (59, 130, 246)]
        for i in range(count):
            st = (start_pos[0] + random.uniform(-10, 10), start_pos[1] + random.uniform(-10, 10))
            tg = (target_pos[0] + random.uniform(-15, 15), target_pos[1] + random.uniform(-15, 15))
            dur = random.randint(400, 650)
            col = random.choice(chip_colors)
            self.flying_chips.append(FlyingChipParticle(st, tg, duration_ms=dur, color=col))

    def spawn_shockwave(self, center_x: float, center_y: float, color=(225, 29, 72)):
        self.shockwaves.append(ShockwaveRing(center_x, center_y, max_radius=150, duration_ms=650, color=color))

    def update(self, dt_ms: int = 16):
        for p in list(self.particles):
            p.update()
            if p.life <= 0 or p.y > 900:
                self.particles.remove(p)

        for fc in list(self.flying_chips):
            fc.update(dt_ms)
            if fc.finished:
                self.flying_chips.remove(fc)

        for sw in list(self.shockwaves):
            sw.update(dt_ms)
            if sw.finished:
                self.shockwaves.remove(sw)

    def draw(self, surface: pygame.Surface):
        for sw in self.shockwaves:
            sw.draw(surface)
        for fc in self.flying_chips:
            fc.draw(surface)
        for p in self.particles:
            p.draw(surface)

# Slower, Elegant Human-Readable Parabolic Flight Animation (850-1050ms)
class CardSparkleTrail:
    def __init__(self, x: float, y: float, color=GOLD_BRIGHT):
        self.x = x + random.uniform(-6, 6)
        self.y = y + random.uniform(-6, 6)
        self.vx = random.uniform(-0.8, 0.8)
        self.vy = random.uniform(-0.6, 0.6)
        self.life = random.randint(18, 36)
        self.max_life = self.life
        self.radius = random.uniform(1.8, 3.8)
        self.color = color

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1

    def draw(self, surface: pygame.Surface):
        if self.life <= 0:
            return
        ratio = self.life / float(self.max_life)
        alpha = int(220 * ratio)
        r = max(1, int(self.radius * ratio))
        s = pygame.Surface((r * 4 + 2, r * 4 + 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (r * 2 + 1, r * 2 + 1), r)
        surface.blit(s, (int(self.x - r * 2 - 1), int(self.y - r * 2 - 1)))

class CardAnimation:
    """
    Slower, Elegant Human-Readable Flight Animation.
    Duration calibrated to 850-1050ms with parabolic arc, ground shadow separation,
    banking rotation, and golden sparkling trail.
    """
    def __init__(self, card, start_pos, target_pos, duration_ms=900, is_face_down=False, arc_height=110.0, on_complete=None):
        self.card = card
        self.start_x, self.start_y = start_pos
        self.target_x, self.target_y = target_pos
        self.duration_ms = duration_ms
        self.elapsed_ms = 0
        self.is_face_down = is_face_down
        self.arc_height = arc_height
        self.on_complete = on_complete
        self.finished = False

        # Random gentle banking entry tilt
        self.start_angle = random.uniform(-16, 16)
        # Bank dynamically into the direction of travel
        dx = self.target_x - self.start_x
        self.bank_angle = max(-18.0, min(18.0, dx * 0.035))

        self.trail_particles: List[CardSparkleTrail] = []
        self.trail_timer = 0

    def update(self, dt_ms: int):
        self.elapsed_ms += dt_ms

        # Spawn sparkling trailing motes along the flight path
        t = min(1.0, self.elapsed_ms / float(self.duration_ms)) if self.duration_ms > 0 else 1.0
        # Smooth ease-in-out cubic for realistic momentum
        if t < 0.5:
            t_ease = 4.0 * t * t * t
        else:
            t_ease = 1.0 - math.pow(-2.0 * t + 2.0, 3) / 2.0

        curr_arc = math.sin(t * math.pi) * self.arc_height
        curr_x = self.start_x + (self.target_x - self.start_x) * t_ease
        curr_y = (self.start_y + (self.target_y - self.start_y) * t_ease) - curr_arc

        self.trail_timer += dt_ms
        if self.trail_timer >= 24 and t < 0.96:
            self.trail_timer = 0
            for _ in range(2):
                self.trail_particles.append(CardSparkleTrail(curr_x + 36, curr_y + 52))

        for p in list(self.trail_particles):
            p.update()
            if p.life <= 0:
                self.trail_particles.remove(p)

        if self.elapsed_ms >= self.duration_ms:
            self.elapsed_ms = self.duration_ms
            self.finished = True
            if self.on_complete:
                self.on_complete()

    def draw(self, surface: pygame.Surface):
        # 1. Draw sparkling trail behind the card
        for p in self.trail_particles:
            p.draw(surface)

        t = min(1.0, self.elapsed_ms / float(self.duration_ms)) if self.duration_ms > 0 else 1.0
        # Smooth ease-in-out cubic
        if t < 0.5:
            t_ease = 4.0 * t * t * t
        else:
            t_ease = 1.0 - math.pow(-2.0 * t + 2.0, 3) / 2.0

        arc = math.sin(t * math.pi) * self.arc_height
        curr_x = self.start_x + (self.target_x - self.start_x) * t_ease
        curr_y = (self.start_y + (self.target_y - self.start_y) * t_ease) - arc

        # Dynamic ground shadow: stays on table surface and scales down/blurs as card lifts
        ground_x = curr_x
        ground_y = self.start_y + (self.target_y - self.start_y) * t_ease + 12
        lift_ratio = arc / max(1.0, self.arc_height)
        shadow_w = max(40, int(72 * (1.0 - lift_ratio * 0.25)))
        shadow_h = max(24, int(42 * (1.0 - lift_ratio * 0.35)))
        shadow_alpha = max(20, int(110 * (1.0 - lift_ratio * 0.55)))

        shadow_surf = pygame.Surface((shadow_w + 10, shadow_h + 10), pygame.SRCALPHA)
        pygame.draw.ellipse(
            shadow_surf,
            (0, 0, 0, shadow_alpha),
            (5, 5, shadow_w, shadow_h)
        )
        surface.blit(shadow_surf, (int(ground_x + 36 - shadow_w // 2 - 5), int(ground_y + 35 - shadow_h // 2 - 5)))

        # Dynamic banking rotation: starts at start_angle, banks into turn mid-flight, levels out to 0 at landing
        mid_bank = math.sin(t * math.pi) * self.bank_angle
        curr_angle = (self.start_angle * (1.0 - t)) + mid_bank

        # Draw card to a temporary surface and rotate if needed
        card_surf = pygame.Surface((72, 104), pygame.SRCALPHA)
        draw_card_direct(card_surf, 0, 0, card=self.card, face_down=self.is_face_down, width=72, height=104)

        if abs(curr_angle) > 0.4:
            rotated_surf = pygame.transform.rotate(card_surf, curr_angle)
            rect = rotated_surf.get_rect(center=(int(curr_x + 36), int(curr_y + 52)))
            surface.blit(rotated_surf, rect.topleft)
        else:
            surface.blit(card_surf, (int(curr_x), int(curr_y)))

# Alias for backwards and forwards compatibility
CardFlightAnimation = CardAnimation

# Direct Card Surface Renderer
def draw_card_direct(surface: pygame.Surface, x: int, y: int, card=None, face_down=False, is_selected=False, width=72, height=104, glow_green=False, glow_gold=False, is_dimmed=False):
    rect = pygame.Rect(x, y, width, height)

    # Ambient drop shadow
    if not is_dimmed:
        shadow_surf = pygame.Surface((width + 8, height + 8), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, (0, 0, 0, 110), pygame.Rect(4, 5, width, height), border_radius=8)
        surface.blit(shadow_surf, (x - 2, y - 2))

    if face_down or card is None:
        pygame.draw.rect(surface, (245, 245, 245), rect, border_radius=8)
        inner_rect = rect.inflate(-6, -6)
        pygame.draw.rect(surface, CARD_BACK_BASE, inner_rect, border_radius=6)
        pat_rect = inner_rect.inflate(-6, -6)
        pygame.draw.rect(surface, CARD_BACK_INNER, pat_rect, width=2, border_radius=4)
        star = FONT_MD.render("🎴", True, GOLD)
        surface.blit(star, (x + width//2 - star.get_width()//2, y + height//2 - star.get_height()//2))
        return

    # Joker Card Special Face
    if getattr(card, 'is_joker', False):
        jk_bg = (253, 244, 255) if not is_dimmed else (200, 195, 205)
        pygame.draw.rect(surface, jk_bg, rect, border_radius=8)
        border_col = (168, 85, 247) if not is_dimmed else (140, 130, 150)
        pygame.draw.rect(surface, border_col, rect, width=2 if not is_dimmed else 1, border_radius=8)
        jk_icon = FONT_LG.render("🃏", True, (147, 51, 234))
        surface.blit(jk_icon, (x + width//2 - jk_icon.get_width()//2, y + height//2 - jk_icon.get_height()//2 - 6))
        jk_lbl = FONT_XS.render(render_arabic("جوكر"), True, (126, 34, 206))
        surface.blit(jk_lbl, (x + width//2 - jk_lbl.get_width()//2, y + height - 20))
        return

    # Face background
    if is_dimmed:
        bg_color = (200, 205, 215)
    elif is_selected:
        bg_color = (255, 255, 238)
    else:
        bg_color = CARD_BG
    pygame.draw.rect(surface, bg_color, rect, border_radius=8)

    # Border selection / glow
    if glow_green:
        border_col = COLOR_ACHIEVED
        border_w = 3
    elif glow_gold or is_selected:
        border_col = GOLD_BRIGHT
        border_w = 3
    elif is_dimmed:
        border_col = (140, 150, 165)
        border_w = 1
    else:
        border_col = CARD_BORDER
        border_w = 1
    pygame.draw.rect(surface, border_col, rect, width=border_w, border_radius=8)

    # Suit and rank
    suit_col = RED_SUIT if card.suit in ['♥', '♦'] else BLACK_SUIT
    if is_dimmed:
        # Mute suit colors for dimmed cards
        suit_col = (140, 80, 80) if card.suit in ['♥', '♦'] else (70, 80, 95)

    r_surf = FONT_MD.render(card.rank, True, suit_col)
    s_surf = FONT_SUIT.render(card.suit, True, suit_col)

    surface.blit(r_surf, (x + 6, y + 4))
    surface.blit(s_surf, (x + 6, y + 22))

    if card.is_letter:
        big_l = FONT_LG.render(card.rank, True, suit_col)
        surface.blit(big_l, (x + width//2 - big_l.get_width()//2, y + height//2 - big_l.get_height()//2 - 4))
    else:
        surface.blit(s_surf, (x + width//2 - s_surf.get_width()//2, y + height//2 - s_surf.get_height()//2 - 5))

    br_rank = FONT_XS.render(card.rank, True, suit_col)
    surface.blit(br_rank, (x + width - br_rank.get_width() - 6, y + height - br_rank.get_height() - 4))

    # Dim overlay if requested
    if is_dimmed:
        dim_surf = pygame.Surface((width, height), pygame.SRCALPHA)
        dim_surf.fill((10, 15, 30, 150))
        surface.blit(dim_surf, (x, y))

# Interactive Luxury Button with Glow and Hover
class Button:
    def __init__(self, x: int, y: int, width: int, height: int, text: str, bg_color=BTN_PRIMARY, callback=None, icon: str = ""):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.icon = icon
        full_text = f"{icon} {text}" if icon else text
        self.reshaped_text = render_arabic(full_text)
        self.bg_color = bg_color
        self.hover_color = tuple(min(255, int(c * 1.25)) for c in bg_color)
        self.callback = callback
        self.enabled = True
        self.hover_anim = 0.0

    def update(self, dt_ms: int, mouse_pos):
        is_hover = self.rect.collidepoint(mouse_pos) and self.enabled
        target = 1.0 if is_hover else 0.0
        self.hover_anim += (target - self.hover_anim) * min(1.0, dt_ms * 0.012)

    def draw(self, surface: pygame.Surface, mouse_pos):
        is_hover = self.rect.collidepoint(mouse_pos) and self.enabled
        
        # Smooth color blend
        r = int(self.bg_color[0] + (self.hover_color[0] - self.bg_color[0]) * self.hover_anim)
        g = int(self.bg_color[1] + (self.hover_color[1] - self.bg_color[1]) * self.hover_anim)
        b = int(self.bg_color[2] + (self.hover_color[2] - self.bg_color[2]) * self.hover_anim)
        color = (r, g, b) if self.enabled else (55, 65, 81)

        # Hover lift offset
        y_offset = int(-3 * self.hover_anim)
        draw_rect = pygame.Rect(self.rect.x, self.rect.y + y_offset, self.rect.width, self.rect.height)

        # Shadow
        shadow_rect = pygame.Rect(self.rect.x, self.rect.y + 3, self.rect.width, self.rect.height)
        pygame.draw.rect(surface, (0, 0, 0, 90), shadow_rect, border_radius=8)

        # Base button
        pygame.draw.rect(surface, color, draw_rect, border_radius=8)

        # Glowing border on hover
        border_col = GOLD if is_hover else (255, 255, 255, 40)
        border_w = 2 if is_hover else 1
        pygame.draw.rect(surface, border_col, draw_rect, width=border_w, border_radius=8)

        txt_col = TEXT_WHITE if self.enabled else TEXT_MUTED
        txt_surf = FONT_MD.render(self.reshaped_text, True, txt_col)
        surface.blit(txt_surf, (
            draw_rect.centerx - txt_surf.get_width() // 2,
            draw_rect.centery - txt_surf.get_height() // 2
        ))

    def handle_event(self, event) -> bool:
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.callback:
                    self.callback()
                return True
        return False

# Center Announcement Banner
class CenterAnnouncement:
    def __init__(self):
        self.title: str = ""
        self.subtitle: str = ""
        self.color = GOLD
        self.duration_ms: int = 0
        self.elapsed_ms: int = 0
        self.active: bool = False

    def show(self, title: str, subtitle: str = "", duration_ms: int = 2200, color=GOLD):
        self.title = title
        self.subtitle = subtitle
        self.color = color
        self.duration_ms = duration_ms
        self.elapsed_ms = 0
        self.active = True

    def update(self, dt_ms: int):
        if not self.active:
            return
        self.elapsed_ms += dt_ms
        if self.elapsed_ms >= self.duration_ms:
            self.active = False

    def draw(self, surface: pygame.Surface, screen_width: int, screen_height: int):
        if not self.active:
            return

        fade = 1.0
        time_left = self.duration_ms - self.elapsed_ms
        if self.elapsed_ms < 160:
            fade = self.elapsed_ms / 160.0
        elif time_left < 280:
            fade = max(0.0, time_left / 280.0)

        alpha = int(245 * fade)
        w, h = 760, 125
        x = (screen_width - w) // 2
        y = 280

        s = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(s, (15, 23, 42, alpha), s.get_rect(), border_radius=16)
        pygame.draw.rect(s, (self.color[0], self.color[1], self.color[2], alpha), s.get_rect(), width=2, border_radius=16)
        surface.blit(s, (x, y))

        t_surf = FONT_XL.render(render_arabic(self.title), True, self.color)
        surface.blit(t_surf, (x + w//2 - t_surf.get_width()//2, y + 20))

        if self.subtitle:
            sub_surf = FONT_MD.render(render_arabic(self.subtitle), True, TEXT_WHITE)
            surface.blit(sub_surf, (x + w//2 - sub_surf.get_width()//2, y + 72))

# 3D Poker Chips Stacks Renderer with Soft Pulsing Radial Aura
def draw_poker_chips_pot(surface: pygame.Surface, x: int, y: int, pot_amount: int, anim_time: float = 0.0):
    # 1. Soft Pulsing Radial Aura under the chips pot
    pulse = 0.5 + 0.5 * math.sin(anim_time * 2.8)
    aura_radius_x = int(95 + pulse * 18)
    aura_radius_y = int(48 + pulse * 10)
    aura_surf = pygame.Surface((aura_radius_x * 2 + 10, aura_radius_y * 2 + 10), pygame.SRCALPHA)
    aura_center = (aura_radius_x + 5, aura_radius_y + 5)
    
    # Layered radial gradient rings
    for r_step in range(3, 0, -1):
        step_frac = r_step / 3.0
        rx = int(aura_radius_x * step_frac)
        ry = int(aura_radius_y * step_frac)
        alpha = int((38 * (1.0 - step_frac * 0.4)) * (0.7 + 0.3 * pulse))
        pygame.draw.ellipse(aura_surf, (245, 197, 24, alpha), (aura_center[0] - rx, aura_center[1] - ry, rx * 2, ry * 2))

    surface.blit(aura_surf, (x - aura_center[0], y - aura_center[1] + 12))

    # 2. Draw stacked chips with subtle vertical breathing bobbing
    chip_colors = [
        ((239, 68, 68), (185, 28, 28)),   # Red $100
        ((59, 130, 246), (29, 78, 216)),  # Blue $50
        ((245, 158, 11), (180, 83, 9)),   # Gold $500
    ]
    # Draw 3 miniature stacks
    stack_offsets = [(-38, 0), (0, -6), (38, 0)]
    chips_count = max(3, min(8, pot_amount // 100))

    pot_bob = math.sin(anim_time * 1.9) * 2.2

    for idx, (ox, oy) in enumerate(stack_offsets):
        primary, dark = chip_colors[idx % len(chip_colors)]
        base_x = x + ox
        base_y = y + oy + pot_bob
        for c in range(chips_count):
            cy = base_y - c * 5
            # Shadow
            pygame.draw.ellipse(surface, (0, 0, 0, 70), (base_x - 16, cy + 2, 32, 14))
            # Chip cylinder
            pygame.draw.ellipse(surface, dark, (base_x - 16, cy, 32, 14))
            pygame.draw.ellipse(surface, primary, (base_x - 14, cy + 1, 28, 11))
            pygame.draw.ellipse(surface, (255, 255, 255), (base_x - 7, cy + 3, 14, 6), width=1)

    # Pot glowing banner
    pot_txt = render_arabic(f"الوعاء الكلي: {pot_amount} 💰")
    p_surf = FONT_LG.render(pot_txt, True, GOLD_BRIGHT)
    bg_w = p_surf.get_width() + 36
    bg_rect = pygame.Rect(x - bg_w//2, y + 22, bg_w, 36)
    
    badge_s = pygame.Surface((bg_w, 36), pygame.SRCALPHA)
    pygame.draw.rect(badge_s, (15, 23, 42, 230), badge_s.get_rect(), border_radius=18)
    pygame.draw.rect(badge_s, GOLD, badge_s.get_rect(), width=2, border_radius=18)
    surface.blit(badge_s, bg_rect.topleft)
    surface.blit(p_surf, (x - p_surf.get_width()//2, y + 27))

# Premier Turn Transition System Renderers
def draw_turn_spotlight(surface: pygame.Surface, target_x: int, target_y: int, radius_x: int = 120, radius_y: int = 70, anim_progress: float = 1.0):
    """
    Dramatic theatrical volumetric spotlight cone descending from high ceiling onto active player.
    """
    prog = max(0.0, min(1.0, anim_progress))
    alpha_max = int(85 * prog)
    if alpha_max <= 2:
        return

    # 1. Soft elliptical floor pool
    pool_surf = pygame.Surface((radius_x * 2 + 20, radius_y * 2 + 20), pygame.SRCALPHA)
    pc = (radius_x + 10, radius_y + 10)
    for step in range(3, 0, -1):
        frac = step / 3.0
        rx = int(radius_x * frac)
        ry = int(radius_y * frac)
        a = int(alpha_max * (1.0 - frac * 0.35))
        pygame.draw.ellipse(pool_surf, (255, 235, 120, a), (pc[0] - rx, pc[1] - ry, rx * 2, ry * 2))
    surface.blit(pool_surf, (target_x - pc[0], target_y - pc[1]))

    # 2. Volumetric descending light beam from top center of ceiling (640, -40)
    light_beam_surf = pygame.Surface((surface.get_width(), surface.get_height()), pygame.SRCALPHA)
    beam_color = (255, 240, 150, int(alpha_max * 0.35))
    top_origin_x = target_x + (surface.get_width() // 2 - target_x) * 0.25
    top_origin_y = -30
    poly_points = [
        (top_origin_x - 30, top_origin_y),
        (top_origin_x + 30, top_origin_y),
        (target_x + radius_x * 0.85, target_y),
        (target_x - radius_x * 0.85, target_y)
    ]
    pygame.draw.polygon(light_beam_surf, beam_color, poly_points)
    surface.blit(light_beam_surf, (0, 0))

def draw_turn_arrow_beacon(surface: pygame.Surface, x: int, y: int, anim_time: float = 0.0):
    """
    3D Golden chevron arrow beacon bouncing above the active player with glow.
    """
    bob = math.sin(anim_time * 5.2) * 6.5
    center_y = y + bob
    
    # Arrow size
    w = 26
    h = 18

    # Drop shadow
    shadow_points = [
        (x, center_y + h + 3),
        (x - w // 2, center_y + 3),
        (x - w // 4, center_y + 3),
        (x, center_y + h // 2 + 3),
        (x + w // 4, center_y + 3),
        (x + w // 2, center_y + 3),
    ]
    pygame.draw.polygon(surface, (0, 0, 0, 90), shadow_points)

    # 3D Golden chevron
    chevron_points = [
        (x, center_y + h),
        (x - w // 2, center_y),
        (x - w // 4, center_y),
        (x, center_y + h // 2),
        (x + w // 4, center_y),
        (x + w // 2, center_y),
    ]
    pygame.draw.polygon(surface, GOLD_BRIGHT, chevron_points)
    pygame.draw.polygon(surface, (255, 255, 240), chevron_points, width=1)

# Comprehensive 56-Cards Matrix Board (Modal/Drawer)
def draw_deck_matrix_modal(surface: pygame.Surface, screen_width: int, screen_height: int, known_revealed_cards: set, mouse_pos):
    """
    Renders an interactive high-visibility matrix of all 56 cards in the deck!
    - Dimmed/Faded: Cards that are still hidden / unseen.
    - Glowing & Highlighted: Cards that have been revealed/discovered!
    - Stats counter: e.g. '18/56 كرت مكشوف'.
    """
    from rules_engine import SUITS, RANK_VALUES, Card

    # Dimmed background backdrop
    backdrop = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    backdrop.fill((5, 8, 16, 220))
    surface.blit(backdrop, (0, 0))

    # Modal Box
    mw, mh = 1040, 560
    mx = (screen_width - mw) // 2
    my = (screen_height - mh) // 2

    modal_surf = pygame.Surface((mw, mh), pygame.SRCALPHA)
    pygame.draw.rect(modal_surf, (15, 22, 36, 250), modal_surf.get_rect(), border_radius=16)
    pygame.draw.rect(modal_surf, GOLD, modal_surf.get_rect(), width=2, border_radius=16)
    surface.blit(modal_surf, (mx, my))

    # Title & Stats
    rev_count = len(known_revealed_cards)
    total_count = 60
    title_text = render_arabic("🃏 خريطة حزمة البطاقات الكاملة (60 كرت تشمل 4 جوكر) | كاشف الأوراق المكشوفة والمجهولة")
    t_surf = FONT_LG.render(title_text, True, GOLD_BRIGHT)
    surface.blit(t_surf, (mx + mw//2 - t_surf.get_width()//2, my + 16))

    sub_text = render_arabic(f"المكشوفة حتى الآن: {rev_count} من {total_count} كرت  |  المتبقية في المجهول: {total_count - rev_count}")
    sub_surf = FONT_MD.render(sub_text, True, COLOR_ACHIEVED if rev_count > 0 else TEXT_MUTED)
    surface.blit(sub_surf, (mx + mw//2 - sub_surf.get_width()//2, my + 52))

    # Legend Indicators
    leg1 = render_arabic("🟢 مضيء ومحدد: كرت تم كشفه / بيدك / عند الموزع")
    leg2 = render_arabic("⚪ باهت ومخفي: كرت مجهول لم يظهر بعد")
    l1_s = FONT_XS.render(leg1, True, COLOR_ACHIEVED)
    l2_s = FONT_XS.render(leg2, True, TEXT_MUTED)
    surface.blit(l1_s, (mx + 40, my + 85))
    surface.blit(l2_s, (mx + mw - l2_s.get_width() - 40, my + 85))

    # Grid of Cards
    ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'S'] # 14 ranks
    suits = SUITS # 4 suits: ♠, ♥, ♦, ♣

    card_w = 64
    card_h = 88
    gap_x = 7
    gap_y = 12
    start_grid_x = mx + 25
    start_grid_y = my + 115

    for s_idx, suit in enumerate(suits):
        row_y = start_grid_y + s_idx * (card_h + gap_y)

        # Suit icon at the left
        s_col = RED_SUIT if suit in ['♥', '♦'] else TEXT_WHITE
        suit_badge = FONT_LG.render(suit, True, s_col)
        surface.blit(suit_badge, (start_grid_x, row_y + card_h//2 - suit_badge.get_height()//2))

        for r_idx, rank in enumerate(ranks):
            col_x = start_grid_x + 30 + r_idx * (card_w + gap_x)
            card_obj = Card(rank, suit)

            # Check if this card is in known_revealed_cards
            is_revealed = any(c.rank == rank and c.suit == suit for c in known_revealed_cards)

            # Mini Hover detection
            c_rect = pygame.Rect(col_x, row_y, card_w, card_h)
            is_hover = c_rect.collidepoint(mouse_pos)

            if is_revealed:
                # Glowing Bright Card
                draw_card_direct(
                    surface, col_x, row_y,
                    card=card_obj, face_down=False,
                    width=card_w, height=card_h,
                    glow_green=True, glow_gold=is_hover,
                    is_dimmed=False
                )
            else:
                # Dimmed/Faded Card
                draw_card_direct(
                    surface, col_x, row_y,
                    card=card_obj, face_down=False,
                    width=card_w, height=card_h,
                    is_dimmed=True
                )

    # Footer note
    close_txt = render_arabic("انقر في أي مكان خارج أو على زر الإغلاق للعودة للطاولة")
    cl_surf = FONT_SM.render(close_txt, True, GOLD)
    surface.blit(cl_surf, (mx + mw//2 - cl_surf.get_width()//2, my + mh - 36))

