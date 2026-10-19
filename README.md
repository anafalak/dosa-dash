 # Dosa Dash 2D — Kitchen Escape (Web Version)

A side-scrolling runner that runs entirely in the browser — no install needed.

## Deploy to Vercel

1. Push this folder to a GitHub repository.
2. Go to [vercel.com](https://vercel.com) → **Add New Project** → import the repo.
3. Vercel auto-detects the static site. Click **Deploy**.
4. Done — you get a public link instantly.

## Files

```
dosa-dash-web/
├── index.html     # the whole game (one file)
├── vercel.json    # Vercel routing config
└── README.md
```

## Controls

| Input | Action |
|---|---|
| Enter / Space / Tap | Start / restart |
| Space / Up / W / Tap | Jump (hold = higher, tap = short hop) |
| Esc or P | Pause / resume |
| R | Restart (from pause or game over) |

## How it plays

- **Intro:** the hand creeps in, the dosa panics and runs!
- **Obstacles** (pots, plates, jars, kettles, tomatoes, rolling pins) get faster over time.
- **Chutney** floats above some obstacles — catch it for 4 s of immunity (stackable to 8 s).
- While immune, hitting an obstacle smashes it (+5 points) instead of killing you.
- **Score** = metres + 10 per chutney + 5 per smash. Best score saved in the browser.

## Also works locally

Just open `index.html` in any browser — no server needed.