#!/usr/bin/env python3
"""
Human Typer — Realistic keystroke simulator for Windows 11
Reads a text file and types it into the active window with human-like
timing, mistakes, corrections, pauses, and cadence variation.

Requirements:
    pip install pynput

Usage:
    python human_typer.py input.txt
    python human_typer.py input.txt --wpm 65 --typo-rate 0.025
    python human_typer.py input.txt --ide-mode        # for IntelliJ, VS Code, etc.

Press F8 or F9 to pause/resume. Press ESC to abort.
"""

import argparse
import math
import platform
import random
import string
import sys
import time
import threading
from pathlib import Path

# ─── Keyboard layout: adjacency map for realistic typos ─────────────────────
ADJACENT_KEYS = {
    'q': 'wa', 'w': 'qeas', 'e': 'wrds', 'r': 'etdf', 't': 'ryfg',
    'y': 'tugh', 'u': 'yijh', 'i': 'uojk', 'o': 'iplk', 'p': 'ol',
    'a': 'qwsz', 's': 'awedxz', 'd': 'serfcx', 'f': 'drtgvc',
    'g': 'ftyhbv', 'h': 'gyujnb', 'j': 'huiknm', 'k': 'jiolm',
    'l': 'kop', 'z': 'asx', 'x': 'zsdc', 'c': 'xdfv', 'v': 'cfgb',
    'b': 'vghn', 'n': 'bhjm', 'm': 'njk',
    '1': '2q', '2': '13qw', '3': '24we', '4': '35er', '5': '46rt',
    '6': '57ty', '7': '68yu', '8': '79ui', '9': '80io', '0': '9p',
}

FAST_BIGRAMS = {
    'th', 'he', 'in', 'er', 'an', 'on', 'en', 'at', 'es', 'ed',
    'or', 'te', 'ti', 'is', 'it', 'al', 'ar', 'st', 'to', 'nt',
    'ng', 'se', 'ha', 'ou', 'io', 'le', 'no', 're', 'hi', 'ea',
    'ri', 'ro', 'co', 'de', 'ra', 'li', 'ch', 'ic', 'ei', 'nd',
    'll', 'ma', 'si', 'om', 'ur', 'ca', 'el', 'ta', 'la', 'ns',
    'ge', 'ly', 'ne', 'us', 'ec', 'di', 've', 'me', 'sa', 'ce',
}

SLOW_BIGRAMS = {
    'br', 'cr', 'fr', 'gr', 'pr', 'tr', 'bl', 'cl', 'fl', 'gl',
    'pl', 'mn', 'nm', 'bf', 'fb', 'gk', 'kg', 'pq', 'qp', 'xz',
    'zx', 'zy', 'yz', 'qz', 'zq', 'jy', 'yj', 'vw', 'wv',
}

SHIFT_CHARS = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$%^&*()_+{}|:"<>?~')

# ─── Windows virtual key codes for polling ──────────────────────────────────
IS_WINDOWS = platform.system() == 'Windows'

if IS_WINDOWS:
    import ctypes
    user32 = ctypes.windll.user32

    VK_ESCAPE = 0x1B
    VK_F8 = 0x77
    VK_F9 = 0x78

    def _win_key_just_pressed(vk_code):
        """Check if a key was pressed since last call (bit 0 = toggled).

        GetAsyncKeyState returns:
          - bit 15 (0x8000): key is currently held down
          - bit 0  (0x0001): key was pressed since last call to this function

        We use bit 0 so we get a single trigger per press, not continuous
        firing while held.
        """
        state = user32.GetAsyncKeyState(vk_code)
        return bool(state & 0x0001)

    def _win_drain_key(vk_code):
        """Consume any pending press for this key (clear bit 0)."""
        user32.GetAsyncKeyState(vk_code)


class TypingProfile:
    """Encapsulates all the parameters that define a 'typist personality'."""

    def __init__(self, base_wpm=None, typo_rate=None):
        self.base_wpm = base_wpm or random.uniform(48, 82)
        self.typo_rate = typo_rate if typo_rate is not None else random.uniform(0.015, 0.04)

        self.rhythm_irregularity = random.uniform(0.15, 0.40)
        self.pause_tendency = random.uniform(0.3, 0.8)
        self.burst_speed_factor = random.uniform(1.15, 1.45)
        self.fatigue_rate = random.uniform(0.0001, 0.0005)
        self.recovery_chance = random.uniform(0.002, 0.008)
        self.think_pause_chance = random.uniform(0.001, 0.006)

        self.instant_correct_pct = random.uniform(0.55, 0.85)
        self.delayed_correct_max = random.randint(1, 4)
        self.correction_pause_base = random.uniform(0.08, 0.25)

        self.chars_typed = 0
        self.in_burst = False
        self.burst_remaining = 0

    def base_delay(self):
        cpm = self.base_wpm * 5
        return 60.0 / cpm

    def get_delay(self, prev_char, curr_char, position_in_word, word_length):
        base = self.base_delay()

        fatigue_factor = 1.0 + (self.chars_typed * self.fatigue_rate)
        if random.random() < self.recovery_chance:
            fatigue_factor *= random.uniform(0.85, 0.95)

        if self.in_burst:
            self.burst_remaining -= 1
            if self.burst_remaining <= 0:
                self.in_burst = False
            burst_mod = 1.0 / self.burst_speed_factor
        else:
            if random.random() < 0.015:
                self.in_burst = True
                self.burst_remaining = random.randint(8, 30)
            burst_mod = 1.0

        bigram = (prev_char + curr_char).lower()
        if bigram in FAST_BIGRAMS:
            bigram_mod = random.uniform(0.70, 0.88)
        elif bigram in SLOW_BIGRAMS:
            bigram_mod = random.uniform(1.15, 1.45)
        else:
            bigram_mod = random.uniform(0.92, 1.08)

        if position_in_word == 0:
            pos_mod = random.uniform(1.05, 1.30)
        elif position_in_word >= word_length - 1:
            pos_mod = random.uniform(0.98, 1.15)
        else:
            pos_mod = random.uniform(0.85, 1.02)

        shift_mod = random.uniform(1.08, 1.25) if curr_char in SHIFT_CHARS else 1.0
        if curr_char == ' ':
            shift_mod = random.uniform(0.80, 0.98)

        delay = base * fatigue_factor * burst_mod * bigram_mod * pos_mod * shift_mod

        noise = random.gauss(1.0, self.rhythm_irregularity * 0.3)
        noise = max(0.4, min(2.2, noise))
        delay *= noise

        if random.random() < 0.03 * self.pause_tendency:
            delay += random.uniform(0.05, 0.20)

        self.chars_typed += 1
        return max(0.02, delay)

    def get_punctuation_pause(self, char):
        if char == '.':   return random.uniform(0.25, 0.90)
        elif char == ',': return random.uniform(0.08, 0.35)
        elif char == '!': return random.uniform(0.20, 0.70)
        elif char == '?': return random.uniform(0.25, 0.80)
        elif char == ':': return random.uniform(0.15, 0.45)
        elif char == ';': return random.uniform(0.12, 0.40)
        return 0

    def get_newline_pause(self):
        return random.uniform(0.4, 2.0)

    def get_thinking_pause(self):
        return random.uniform(1.5, 5.0)

    def should_make_typo(self):
        return random.random() < self.typo_rate

    def get_typo_char(self, intended_char):
        lower = intended_char.lower()
        if lower in ADJACENT_KEYS and random.random() < 0.70:
            typo = random.choice(ADJACENT_KEYS[lower])
            return typo.upper() if intended_char.isupper() else typo
        if lower.isalpha() and random.random() < 0.50:
            offset = random.choice([-1, 1, -2, 2])
            idx = ord(lower) - ord('a') + offset
            if 0 <= idx < 26:
                typo = chr(ord('a') + idx)
                return typo.upper() if intended_char.isupper() else typo
        if random.random() < 0.5:
            typo = random.choice(string.ascii_lowercase)
            return typo.upper() if intended_char.isupper() else typo
        return intended_char

    def get_correction_behavior(self):
        if random.random() < self.instant_correct_pct:
            return True, 0
        else:
            return False, random.randint(1, self.delayed_correct_max)


class HumanTyper:
    """Main typing engine — reads text and injects keystrokes."""

    def __init__(self, text, profile=None, start_delay=3, ide_mode=False):
        self.text = text
        self.profile = profile or TypingProfile()
        self.start_delay = start_delay
        self.ide_mode = ide_mode

        self._paused = False
        self._stopped = False

        self._keyboard = None
        # Listener only used on non-Windows (pynput fallback)
        self._listener = None

    # ── Hotkey detection (platform-specific) ─────────────────────────────

    def _poll_hotkeys(self):
        """Check for F8/F9/ESC via Windows API polling.

        Called from the main thread inside _wait() — no hooks, no
        listener threads, no risk of hook timeout from injected keys.
        """
        if _win_key_just_pressed(VK_ESCAPE):
            self._stopped = True
            return

        if _win_key_just_pressed(VK_F8) or _win_key_just_pressed(VK_F9):
            self._paused = not self._paused
            if self._paused:
                print("\n[PAUSED] Press F8 or F9 to resume", flush=True)
            else:
                print("[RESUMED] Typing continues...\n", flush=True)

    def _on_key_press_pynput(self, key):
        """Fallback hotkey handler for non-Windows (macOS/Linux).

        Uses pynput Listener. On Windows we poll instead — see _poll_hotkeys().
        """
        from pynput.keyboard import Key
        if key in (Key.f8, Key.f9):
            self._paused = not self._paused
            if self._paused:
                print("\n[PAUSED] Press F8 or F9 to resume", flush=True)
            else:
                print("[RESUMED] Typing continues...\n", flush=True)
        elif key == Key.esc:
            self._stopped = True

    # ── Wait / sleep with hotkey responsiveness ──────────────────────────

    def _wait(self, seconds):
        """Sleep for `seconds`, polling for pause/stop hotkeys each tick."""
        elapsed = 0.0
        increment = 0.02

        while elapsed < seconds:
            if IS_WINDOWS:
                self._poll_hotkeys()
            if self._stopped:
                return False

            # If paused, spin here until unpaused or stopped
            while self._paused:
                time.sleep(0.05)
                if IS_WINDOWS:
                    self._poll_hotkeys()
                if self._stopped:
                    return False

            time.sleep(min(increment, seconds - elapsed))
            elapsed += increment

        return True

    # ── Keystroke injection ──────────────────────────────────────────────

    def _type_char(self, char):
        from pynput.keyboard import Key
        if char == '\n':
            self._keyboard.press(Key.enter)
            self._keyboard.release(Key.enter)
        elif char == '\t':
            self._keyboard.press(Key.tab)
            self._keyboard.release(Key.tab)
        else:
            self._keyboard.type(char)

    def _clear_auto_indent(self):
        """Clear IDE auto-inserted whitespace after Enter.

        Sends: Home → Home → Shift+End → Delete
        Double-Home handles 'smart home' toggle in IntelliJ/VS Code.
        """
        from pynput.keyboard import Key

        # Let IDE finish processing Enter + auto-indent
        time.sleep(random.uniform(0.08, 0.14))

        # Home twice → column 0
        self._keyboard.press(Key.home)
        self._keyboard.release(Key.home)
        time.sleep(0.02)
        self._keyboard.press(Key.home)
        self._keyboard.release(Key.home)
        time.sleep(0.02)

        # Shift+End → select all auto-indent
        self._keyboard.press(Key.shift)
        self._keyboard.press(Key.end)
        self._keyboard.release(Key.end)
        self._keyboard.release(Key.shift)
        time.sleep(0.02)

        # Delete the selection
        self._keyboard.press(Key.delete)
        self._keyboard.release(Key.delete)
        time.sleep(0.02)

    def _backspace(self, count=1):
        from pynput.keyboard import Key
        for _ in range(count):
            delay = random.uniform(0.03, 0.09)
            if not self._wait(delay):
                return False
            self._keyboard.press(Key.backspace)
            self._keyboard.release(Key.backspace)
        return True

    # ── Lifecycle ────────────────────────────────────────────────────────

    def _cleanup(self):
        if self._listener is not None:
            self._listener.stop()
            self._listener.join(timeout=2.0)
            self._listener = None

    def run(self):
        from pynput.keyboard import Controller, Listener
        self._keyboard = Controller()

        if IS_WINDOWS:
            # Windows: use polling — no listener needed
            # Drain any stale key states before we start
            _win_drain_key(VK_F8)
            _win_drain_key(VK_F9)
            _win_drain_key(VK_ESCAPE)
        else:
            # macOS/Linux: use pynput Listener as fallback
            self._listener = Listener(on_press=self._on_key_press_pynput)
            self._listener.daemon = False
            self._listener.start()

        try:
            self._run_inner()
        finally:
            self._cleanup()

    def _run_inner(self):
        """Core typing loop."""

        mode_label = "IDE mode (auto-indent cleanup ON)" if self.ide_mode else "Standard mode"
        hotkey_method = "Windows API polling" if IS_WINDOWS else "pynput Listener"
        print(f"\nTyping will begin in {self.start_delay} seconds...")
        print(f"  Mode:       {mode_label}")
        print(f"  Hotkeys:    {hotkey_method}")
        print(f"  WPM target: ~{self.profile.base_wpm:.0f}")
        print(f"  Typo rate:  ~{self.profile.typo_rate * 100:.1f}%")
        print(f"  Rhythm irregularity: {self.profile.rhythm_irregularity:.2f}")
        print(f"\n  F8 / F9 = Pause/Resume | ESC = Stop\n")
        print(f"  Switch to your target window NOW!\n", flush=True)

        for i in range(self.start_delay, 0, -1):
            print(f"  {i}...", flush=True)
            if not self._wait(1.0):
                print("\n[STOPPED] ESC pressed — aborting.", flush=True)
                return
        print("  GO!\n", flush=True)

        prev_char = ' '
        i = 0

        while i < len(self.text):
            if self._stopped:
                break

            char = self.text[i]

            # ── Word boundaries ──
            word_start = i
            while word_start > 0 and self.text[word_start - 1] not in ' \n\t':
                word_start -= 1
            word_end = i
            while word_end < len(self.text) and self.text[word_end] not in ' \n\t':
                word_end += 1
            position_in_word = i - word_start
            word_length = word_end - word_start

            # ── Delay ──
            delay = self.profile.get_delay(prev_char, char, position_in_word, word_length)

            if prev_char in '.!?,:;' and char == ' ':
                delay += self.profile.get_punctuation_pause(prev_char)

            if char == '\n' and prev_char == '\n':
                delay += self.profile.get_newline_pause()

            if random.random() < self.profile.think_pause_chance:
                delay += self.profile.get_thinking_pause()

            if not self._wait(delay):
                break

            # ── Newline handling ──
            if char == '\n':
                self._type_char(char)
                if self.ide_mode:
                    self._clear_auto_indent()
                prev_char = char
                i += 1
                continue

            # ── Typo injection ──
            if char.isalnum() and self.profile.should_make_typo():
                immediate, extra_chars = self.profile.get_correction_behavior()

                if immediate:
                    wrong = self.profile.get_typo_char(char)
                    self._type_char(wrong)

                    correction_pause = (self.profile.correction_pause_base
                                        + random.uniform(0.05, 0.30))
                    if not self._wait(correction_pause):
                        break
                    if not self._backspace(1):
                        break
                    if not self._wait(random.uniform(0.02, 0.10)):
                        break
                    self._type_char(char)
                else:
                    wrong = self.profile.get_typo_char(char)
                    self._type_char(wrong)

                    lookahead = min(extra_chars, len(self.text) - i - 1)
                    if lookahead > 0:
                        for j in range(1, lookahead + 1):
                            next_char = self.text[i + j]
                            next_delay = self.profile.get_delay(
                                self.text[i + j - 1], next_char, 0, 1
                            )
                            if not self._wait(next_delay):
                                break
                            self._type_char(next_char)

                        notice_pause = random.uniform(0.2, 0.7)
                        if not self._wait(notice_pause):
                            break
                        if not self._backspace(lookahead + 1):
                            break
                        if not self._wait(random.uniform(0.05, 0.20)):
                            break

                        for j in range(0, lookahead + 1):
                            retype_char = self.text[i + j]
                            retype_delay = self.profile.get_delay(
                                prev_char if j == 0 else self.text[i + j - 1],
                                retype_char, j, lookahead + 1
                            )
                            retype_delay *= random.uniform(0.75, 0.92)
                            if not self._wait(retype_delay):
                                break
                            self._type_char(retype_char)

                        prev_char = self.text[i + lookahead]
                        i += lookahead + 1
                        continue
            else:
                self._type_char(char)

            prev_char = char
            i += 1

        if self._stopped:
            print("\n[STOPPED] ESC pressed — aborting.", flush=True)
        else:
            print("\n[COMPLETE] Finished typing.", flush=True)


def main():
    parser = argparse.ArgumentParser(
        description="Human Typer — realistic keystroke simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python human_typer.py input.txt
  python human_typer.py input.txt --wpm 70
  python human_typer.py input.txt --ide-mode              # for IntelliJ, VS Code, etc.
  python human_typer.py input.txt --ide-mode --wpm 60
  python human_typer.py input.txt --seed 42               # reproducible run

Controls:
  F8 / F9   Pause / Resume
  ESC       Stop immediately
        """
    )
    parser.add_argument("file", help="Path to the text file to type")
    parser.add_argument("--wpm", type=float, default=None,
                        help="Base WPM (default: random 48–82)")
    parser.add_argument("--typo-rate", type=float, default=None,
                        help="Typo probability per char (default: random 0.015–0.04)")
    parser.add_argument("--start-delay", type=int, default=5,
                        help="Seconds before typing starts (default: 5)")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducibility")
    parser.add_argument("--ide-mode", action="store_true",
                        help="Clear IDE auto-indentation after each Enter "
                             "(use with IntelliJ, VS Code, Eclipse, etc.)")

    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    path = Path(args.file)
    if not path.exists():
        print(f"Error: File not found: {path}")
        sys.exit(1)

    text = path.read_text(encoding='utf-8')
    if not text.strip():
        print("Error: File is empty.")
        sys.exit(1)

    print(f"Loaded {len(text)} characters from '{path.name}'")

    profile = TypingProfile(base_wpm=args.wpm, typo_rate=args.typo_rate)
    typer = HumanTyper(text, profile=profile, start_delay=args.start_delay,
                       ide_mode=args.ide_mode)

    try:
        typer.run()
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Ctrl+C pressed.")


if __name__ == "__main__":
    main()
