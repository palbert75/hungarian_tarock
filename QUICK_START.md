# Hungarian Tarokk – Quick Start

Play a hand against bots on your own machine in a few minutes.

## Prerequisites

- Python 3.10 or higher
- Node.js 18 or higher

## 1. Start the server

```bash
cd server
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py
```

The server listens on http://localhost:8000. Check it with:

```bash
curl http://localhost:8000/health        # {"status":"healthy"}
```

## 2. Start the web client

In a second terminal:

```bash
cd client
npm install
VITE_SERVER_URL=http://localhost:8000 npm run dev
```

Open http://localhost:3003, enter a name and tap **Play against bots**
(*Játék gépek ellen*). Without `VITE_SERVER_URL` the client talks to the
hosted server instead of yours.

To play with other people, open a table, share the invite link, and fill the
seats that stay free with bots.

## 3. Run the checks

```bash
cd server
.venv/bin/python -m pytest -q            # rules, bots, whole hands, restart, statistics

cd ../client
npx tsc --noEmit && npm test && npm run build
```

## Where things are

```
tarokk/
├── server/                  # Game server (Python, FastAPI, Socket.IO)
│   ├── models/              # Cards, players, the state of a hand
│   ├── game_logic/          # Bidding, announcements, scoring
│   ├── validation/          # What may be played, discarded, announced
│   ├── bots/                # The bots' rules; the hints use the same rules
│   ├── networking/          # Socket events, tables, problem reports, limits
│   ├── persistence/         # Saved tables (SQLite) and statistics
│   ├── tests/               # pytest
│   ├── tools/               # Reports, statistics, restart trial, decision trees
│   ├── k8s/, deploy.sh      # Production deployment
│   └── main.py              # Entry point
├── client/                  # Web client (React, TypeScript, Vite, installable PWA)
└── docs/                    # Player guide (Hungarian)
```

## Useful settings

Set as environment variables or in `server/.env` (see `server/.env.example`):

| Variable | Default | Meaning |
|---|---|---|
| `PORT` | `8000` | Port of the server |
| `DEBUG` | `True` | Development mode: reload on code changes, log every frame. Set `false` in production |
| `MAX_ROOMS` | `100` | Tables open at the same time |
| `CORS_ORIGINS` | `*` | Web pages that may connect, comma-separated |
| `STATS_TOKEN` | unset | Switches on `/stats` (played hands per day) for this token |

## Troubleshooting

**Port already in use**

```bash
lsof -ti:8000 | xargs kill
# or
PORT=8001 .venv/bin/python main.py
```

**The client shows "Kapcsolódás…" forever**: the server is not running, or
`VITE_SERVER_URL` points somewhere else.

**A table from yesterday is back after a restart**: the server saves every
table to `server/data/tarokk_game.db` and loads it again. Delete the file to
start clean.

## More

- Game rules: `server/HUNGARIAN_TAROKK_RULES.md`
- Server and its events: `server/README.md`, `server/networking/protocol.py`
- How the bots decide: Settings → *How the bots play* in the app
- Saved tables and restarts: `server/PERSISTENCE.md`
