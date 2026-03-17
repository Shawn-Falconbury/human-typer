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

# Set a specific base speed
python human_typer.py input.txt --wpm 65

# Adjust typo frequency (~3% of characters)
python human_typer.py input.txt --typo-rate 0.03

# Longer countdown to switch windows
python human_typer.py input.txt --start-delay 10

# Reproducible run (same personality each time)
python human_typer.py input.txt --seed 42

# Combine options
python human_typer.py input.txt --wpm 70 --typo-rate 0.02 --start-delay 8
```

### Controls

| Key        | Action             |
|------------|--------------------|
| `F8` / `F9` | Pause / Resume   |
| `ESC`      | Stop immediately   |

> **Note:** Both F8 and F9 work as pause/resume toggles. Some IDEs (IntelliJ, VS Code) intercept F9 for debugging, so F8 is provided as an alternative.

---

## Command-Line Options

| Option          | Default          | Description                              |
|-----------------|------------------|------------------------------------------|
| `file`          | *(required)*     | Path to the `.txt` file to type          |
| `--wpm`         | Random (48–82)   | Base words-per-minute speed              |
| `--typo-rate`   | Random (1.5–4%)  | Probability of a typo per character      |
| `--start-delay` | `5`              | Seconds before typing begins             |
| `--seed`        | None             | Random seed for reproducible runs        |

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

---

## License

MIT License — see [LICENSE](LICENSE) for details.
