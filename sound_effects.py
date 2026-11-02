"""
Sound Manager for Strategic Card Game.
Synthesizes clean, high-quality casino sound effects using NumPy and Pygame Mixer.
Zero external asset dependency needed!
"""
import pygame
import numpy as np

class SoundManager:
    def __init__(self):
        self.enabled = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self.sample_rate = 44100
            self.sounds = {}
            self.enabled = True
            self._generate_all_sounds()
        except Exception as e:
            print(f"[SoundManager] Warning: Sound init failed: {e}")
            self.enabled = False

    def _make_sound(self, samples: np.ndarray) -> pygame.mixer.Sound:
        # samples should be float32 from -1.0 to 1.0
        samples = np.clip(samples, -1.0, 1.0)
        int16_samples = (samples * 32767).astype(np.int16)
        stereo_samples = np.column_stack((int16_samples, int16_samples))
        return pygame.sndarray.make_sound(stereo_samples)

    def _generate_all_sounds(self):
        sr = self.sample_rate

        # 1. Card Deal / Flip sound (crisp snap / woosh)
        t_deal = np.linspace(0, 0.08, int(sr * 0.08), endpoint=False)
        noise = np.random.uniform(-0.5, 0.5, len(t_deal))
        env = np.exp(-t_deal * 50)
        sweep = np.sin(2 * np.pi * (800 - t_deal * 4000) * t_deal)
        deal_samples = (sweep * 0.3 + noise * 0.4) * env
        self.sounds['card_deal'] = self._make_sound(deal_samples)

        # 2. Card Hover / Click (soft high wooden click)
        t_click = np.linspace(0, 0.04, int(sr * 0.04), endpoint=False)
        click_env = np.exp(-t_click * 120)
        click_samples = np.sin(2 * np.pi * 1400 * t_click) * click_env * 0.25
        self.sounds['card_click'] = self._make_sound(click_samples)

        # 3. Chip / Coin Clink sound (metallic ceramic clink)
        t_chip = np.linspace(0, 0.12, int(sr * 0.12), endpoint=False)
        chip_env = np.exp(-t_chip * 40)
        chip_samples = (np.sin(2 * np.pi * 2400 * t_chip) * 0.4 +
                        np.sin(2 * np.pi * 3600 * t_chip) * 0.3) * chip_env
        self.sounds['chip'] = self._make_sound(chip_samples)

        # 4. Victory Fanfare (Triumphant Chord Arpeggio)
        dur = 0.5
        t_fan = np.linspace(0, dur, int(sr * dur), endpoint=False)
        freqs = [523.25, 659.25, 783.99, 1046.50] # C5, E5, G5, C6
        fan_samples = np.zeros(len(t_fan))
        step_len = int(len(t_fan) / 4)
        for i, f in enumerate(freqs):
            start = i * step_len
            t_sub = np.linspace(0, dur - (i * dur / 4), len(t_fan) - start, endpoint=False)
            env_sub = np.exp(-t_sub * 4.5)
            wave = (np.sin(2 * np.pi * f * t_sub) + 0.4 * np.sin(2 * np.pi * (f * 2) * t_sub)) * env_sub * 0.3
            fan_samples[start:] += wave
        self.sounds['victory'] = self._make_sound(fan_samples)

        # 5. Defeat / Loss Thud (Low somber resonant chord)
        t_loss = np.linspace(0, 0.6, int(sr * 0.6), endpoint=False)
        loss_env = np.exp(-t_loss * 5.0)
        loss_samples = (np.sin(2 * np.pi * 130.81 * t_loss) * 0.4 + # C3
                        np.sin(2 * np.pi * 155.56 * t_loss) * 0.3 + # Eb3
                        np.sin(2 * np.pi * 98.00 * t_loss) * 0.3) * loss_env # G2
        self.sounds['defeat'] = self._make_sound(loss_samples)

        # 6. Steal / Dramatic Alert sound
        t_alert = np.linspace(0, 0.25, int(sr * 0.25), endpoint=False)
        alert_env = np.exp(-t_alert * 10)
        alert_samples = np.sin(2 * np.pi * 880 * t_alert) * alert_env * 0.35
        self.sounds['steal'] = self._make_sound(alert_samples)

        # 7. Elimination Thunder / Heavy Impact sound
        t_elim = np.linspace(0, 0.7, int(sr * 0.7), endpoint=False)
        elim_env = np.exp(-t_elim * 6.0)
        noise_elim = np.random.uniform(-0.6, 0.6, len(t_elim))
        boom = np.sin(2 * np.pi * (110 - t_elim * 90) * t_elim)
        elim_samples = (boom * 0.6 + noise_elim * 0.4) * elim_env
        self.sounds['elimination'] = self._make_sound(elim_samples)

        # 8. Turn Fanfare / Turn Shift Chime (High crisp golden crystalline chime)
        t_turn = np.linspace(0, 0.35, int(sr * 0.35), endpoint=False)
        env_turn = np.exp(-t_turn * 9.0)
        turn_samples = (
            np.sin(2 * np.pi * 1174.66 * t_turn) * 0.35 +   # D6
            np.sin(2 * np.pi * 1760.00 * t_turn) * 0.25 +   # A6
            np.sin(2 * np.pi * 2349.32 * t_turn) * 0.15     # D7
        ) * env_turn
        self.sounds['turn_fanfare'] = self._make_sound(turn_samples)

        # 9. Card Swoosh (Silky smooth airy parabolic card flight)
        dur_sw = 0.28
        t_sw = np.linspace(0, dur_sw, int(sr * dur_sw), endpoint=False)
        noise_sw = np.random.uniform(-0.35, 0.35, len(t_sw))
        # Frequency modulated swoop from 400Hz up to 750Hz and down to 250Hz
        freq_curve = 380 + 350 * np.sin(np.pi * (t_sw / dur_sw))
        phase = 2 * np.pi * np.cumsum(freq_curve) / sr
        swoop_sine = np.sin(phase) * 0.22
        env_sw = np.sin(np.pi * (t_sw / dur_sw)) ** 1.8
        sw_samples = (swoop_sine + noise_sw * 0.3) * env_sw
        self.sounds['card_swoosh'] = self._make_sound(sw_samples)

    def play(self, sound_name: str):
        if not self.enabled:
            return
        snd = self.sounds.get(sound_name)
        if snd:
            try:
                snd.play()
            except Exception:
                pass
