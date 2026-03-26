# ⌨️ Human Typer

**Realistic keystroke simulator for Windows 11** — reads a text file and types it into any active window with human-like timing, mistakes, and corrections that are indistinguishable from real typing.

Every run generates a unique "typist personality" with randomized rhythm, speed, error patterns, and correction behavior — no two sessions ever look the same.

---

## Features

### Timing & Rhythm
- **Variable WPM** — speed fluctuates naturally using Gaussian noise, burst cycles, and fatigue drift; never metronomic
- **Bigram-aware timing** — common letter pairs (`th`, `er`, `in`) are typed faster; awkward combos (`zx`, `qp`) are slower
- **Word-position effects** — slower at word starts, fastest mid-word, slight deceleration at word ends
- **Shift key penalty** — capital letters and symbols take slightly longer
- **Burst typing** — random stretches of faster typing, as if hitting a groove
- **Fatigue simulation** — gradual slowdown over long texts with occasional "refocus" recoveries

### Pauses
- **Thinking pauses** — random 1.5–5 second pauses as if re-reading or composing thoughts
- **Punctuation pauses** — natural delays after periods, commas, and question marks
- **Paragraph pauses** — longer pauses between paragraphs

### Typos & Corrections
- **Keyboard-proximity typos** — mistakes hit adjacent keys on QWERTY layout, not random characters
- **Immediate corrections** — most typos caught instantly (backspace → retype)
- **Delayed corrections** — some typos noticed after 1–4 more characters before backspacing all and retyping
- **Correction hesitation** — realistic pause before backspacing (the "oh no" moment)
- **Faster retyping** — corrected text is retyped slightly faster, mimicking muscle memory

### IDE Support
- **`--ide-mode`** — clears auto-inserted indentation after each Enter keystroke, so the source file's original whitespace is preserved exactly. Works with IntelliJ IDEA, VS Code, Eclipse, PyCharm, and other editors with auto-indent.

### Per-Session Personality
Each run randomizes:
- Base WPM (48–82 range by default)
- Rhythm irregularity
- Pause tendency and frequency
- Burst speed and duration
- Fatigue rate and recovery chance
- Typo rate and correction behavior

---

## Requirements

- **OS:** Windows 11 (also works on Windows 10, macOS, Linux)
- **Python:** 3.8+
- **Dependencies:** `pynput`

---

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Shawn-Falconbury/human-typer.git
   cd human-typer
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run with a text file:**
   ```bash
   python human_typer.py sample_input.txt
   ```

4. **Switch to your target window** (Notepad, Word, browser, chat app, etc.) during the countdown.

---

## Usage

```bash
# Fully randomized typist personality
python human_typer.py input.txt

# For IDEs with auto-indent (IntelliJ, VS Code, etc.)
python human_typer.py input.txt --ide-mode

# Set a specific base speed
python human_typer.py input.txt --wpm 65

# Adjust typo frequency (~3% of characters)
python human_typer.py input.txt --typo-rate 0.03

# Longer countdown to switch windows
python human_typer.py input.txt --start-delay 10

# Reproducible run (same personality each time)
python human_typer.py input.txt --seed 42

# Combine options
python human_typer.py input.txt --ide-mode --wpm 70 --typo-rate 0.02
```

### Controls

| Key          | Action             |
|--------------|--------------------|
| `F7` / `F8`  | Pause / Resume    |
| `ESC`        | Stop immediately   |

> **Note:** F7 and F8 are used instead of F9 to avoid conflicts with IDE debugger shortcuts (IntelliJ, VS Code, etc.).

---

## Command-Line Options

| Option          | Default          | Description                              |
|-----------------|------------------|------------------------------------------|
| `file`          | *(required)*     | Path to the `.txt` file to type          |
| `--wpm`         | Random (48–82)   | Base words-per-minute speed              |
| `--typo-rate`   | Random (1.5–4%)  | Probability of a typo per character      |
| `--start-delay` | `5`              | Seconds before typing begins             |
| `--seed`        | None             | Random seed for reproducible runs        |
| `--ide-mode`    | Off              | Clear IDE auto-indent after each Enter   |

---

## IDE Mode

When typing into code editors like IntelliJ IDEA or VS Code, the editor automatically inserts indentation after you press Enter. This causes double-indentation because the script then types the source file's original whitespace on top of the auto-inserted whitespace.

**`--ide-mode` fixes this** by sending `Home → Home → Shift+End → Delete` after each Enter keystroke to clear whatever the IDE auto-inserted, then typing the next line's whitespace exactly as it appears in the source file.

```bash
# Without --ide-mode in IntelliJ: double-indented mess
python human_typer.py MyClass.java

# With --ide-mode: indentation matches source file exactly
python human_typer.py MyClass.java --ide-mode
```

---

## How It Works

The script uses `pynput` to inject keystrokes into the currently focused window. Each character's timing is calculated from multiple layered factors:

```
final_delay = base_delay × fatigue × burst × bigram × position × shift × noise
```

- **base_delay** — derived from WPM target
- **fatigue** — accumulates over time, with random recovery events
- **burst** — periodic faster stretches simulating flow state
- **bigram** — lookup against common/uncommon letter pair tables
- **position** — where in the current word this character falls
- **shift** — penalty for characters requiring the Shift key
- **noise** — Gaussian jitter so timing is never predictable

Typos are generated using a QWERTY adjacency map, so mistakes look like real finger slips rather than random characters. Correction behavior varies between instant backspace and delayed multi-character correction with realistic hesitation.

### Hotkey Implementation

On Windows, hotkeys are detected via `ctypes.windll.user32.GetAsyncKeyState()` polling on the main thread — this avoids low-level keyboard hooks that can be silently killed by Windows when rapid keystrokes are injected (especially in `--ide-mode`). On macOS/Linux, a `pynput` Listener is used as a fallback.

---

## License

MIT License — see [LICENSE](LICENSE) for details.
