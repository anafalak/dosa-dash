# Dosa Dash 2D — Kitchen Escape

A side-scrolling runner built with **Python + pygame**.

A dosa is sitting on a kitchen counter. A human **hand** reaches in to grab it — so it **runs**!
Jump over pots, plates, jars, kettles, tomatoes and rolling pins. Hit one and the hand catches you.
**Catch chutney** to become **immune**: while the green shield is up you smash straight through obstacles.

## Project structure

```
dosa-dash/
├── main.py            # the whole game (run this)
├── requirements.txt   # pygame
├── run.bat            # Windows: double-click to install + play
├── README.md
├── .gitignore
├── highscore.txt      # created automatically after your first run
└── assets/
    ├── dosa.png       # YOUR dosa image   (you add this)
    ├── chutney.png    # YOUR chutney image (you add this)
    └── README.txt
```

## Setup and run

You need **Python 3.9+** (python.org; tick "Add Python to PATH" on Windows).

### Windows (VS Code terminal / PowerShell)
```powershell
cd dosa-dash
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```
Or simply double-click **run.bat**.

In VS Code, press `Ctrl+Shift+P` → *Python: Select Interpreter* → pick `.venv` so the editor finds pygame.

### macOS / Linux
```bash
cd dosa-dash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Controls

| Key | Action |
|---|---|
| Enter / Space / Click | Start |
| Space / Up / W / Click | Jump (hold = higher, tap = short hop) |
| Esc or P | Pause / resume (Esc on the menu or game-over screen quits) |
| R | Restart (from pause or game over) |

## How it plays

- **Intro:** press Enter, the hand creeps in, the dosa panics, the hand slams the counter and misses — run!
- **Obstacles** get faster and denser the further you go.
- **Chutney** floats above some obstacles. Each one gives **4 s of immunity** (stacks up to 8 s). While immune, touching an obstacle smashes it (+5 points) instead of killing you.
- **Death:** the hand drops down, picks the dosa up and carries it away.
- **Score** = metres + 10 per chutney + 5 per smash. Best score is saved to `highscore.txt`.

## Your images

Drop `dosa.png` and `chutney.png` into `assets/`.
- Transparent PNGs are best; any size works (auto-cropped and scaled).
- Face the dosa **right**.
- If a PNG has a plain solid background instead of transparency, the game tries to remove it automatically.
- Missing files → the game draws a placeholder, so it always runs. The console prints which file wasn't found.

## Tuning (top of `main.py`)

| Constant | Effect |
|---|---|
| `BASE_SPEED`, `MAX_SPEED` | Starting / top running speed |
| `JUMP_V`, `GRAVITY` | Jump height and floatiness |
| `IMMUNITY_TIME`, `IMMUNITY_MAX` | Chutney shield length |
| `CHUTNEY_CHANCE` | How often chutney appears (0–1) |
| `DOSA_HEIGHT`, `CHUTNEY_HEIGHT` | On-screen sprite sizes |

## Troubleshooting

- **`ModuleNotFoundError: No module named 'pygame'`** → run the install command above, and make sure you run `main.py` with the same Python (the `.venv` one).
- **First launch takes a few seconds** → pygame is building its system-font cache; it's fast afterwards.
- **My image doesn't show** → check the exact file name/case and that it's inside `assets/` next to `main.py`.