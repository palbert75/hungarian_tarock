# Hungarian Tarokk Game Server

A complete implementation of Hungarian Tarokk (Illustrated Hungarian Tarokk / XX Hívás), a traditional 4-player trick-taking card game, with real-time multiplayer support via WebSockets.

**Demo:** https://huntarokk.netlify.app/

## 🎮 Features

- **Complete Game Implementation**: Full rules of Hungarian Tarokk
- **42-Card Deck**: Authentic Industrie und Glück deck
- **Real-Time Multiplayer**: WebSocket-based server using Socket.IO
- **4-Player Support**: Room-based matchmaking
- **Full Game Flow**: Bidding → Talon → Discard → Partner Call → Trick-Taking → Scoring
- **Rule Validation**: Enforces all game rules (follow suit, honour requirements, etc.)
- **Games Survive a Server Update**: Every table is saved; after a restart players are back at their seats within seconds
- **Phone-First Web App**: Three-band game screen (table, hand, thumb buttons), installable to the home screen (PWA)
- **Bots**: Fill free seats with rule-based bots, or let the host hand a dropped player's seat to a bot
- **Tutorial Hints**: Optional hints in every phase, with the reason; the same rules the bots follow
- **Hungarian and English**: Switch in settings; Hungarian is the default on Hungarian devices
- **Table Play**: Fixed seats arranged by the host, rotating dealer, next hand at the same table, running totals
- **Graceful Drop-Outs**: A dropped player's seat is held; everyone sees who dropped out and who is back

## 🚀 Quick Start

See [QUICK_START.md](QUICK_START.md) for a 5-minute getting started guide.

```bash
# Terminal 1: server on port 8000
cd server
pip install -r requirements.txt
python main.py

# Terminal 2: web client on http://localhost:3003
cd client
npm install
VITE_SERVER_URL=http://localhost:8000 npm run dev
```

Open the page, enter a name and tap **Play against bots**. Without
`VITE_SERVER_URL` the client talks to the hosted server.

Checks: `cd server && python -m pytest` and
`cd client && npx tsc --noEmit && npm test && npm run build`.

### Bots and hints

The bot rules live in `server/bots/` (`strategy.py` decides, `view.py` is what
a seat may see, `counting.py` counts tarokks). A bot never sees another hand,
the talon or an unrevealed partner. The tutorial hint a player gets is exactly
what a bot would do in that seat. `server/tests/test_bot_simulation.py` plays
300 whole hands with four bots; `server/tests/test_bot_strategy.py` has one
test per rule.

## 📁 Project Structure

```
tarokk/
├── server/                      # Game server (Python + FastAPI + Socket.IO)
│   ├── models/                  # Data models (Card, Deck, Player, GameState, Bid)
│   ├── game_logic/              # Game rules (Bidding, Scoring)
│   ├── validation/              # Rule validators
│   ├── bots/                    # Bot rules (also used for the hints)
│   ├── networking/              # WebSocket server (Socket.IO), tables, reports, limits
│   ├── persistence/             # Saved tables (SQLite) and statistics
│   ├── tools/                   # Reports, statistics, restart trial, decision trees
│   ├── k8s/ + deploy.sh         # Production deployment
│   ├── utils/                   # Utilities (position helpers)
│   ├── tests/                   # Unit tests (pytest)
│   ├── main.py                  # Server entry point
│   ├── config.py                # Configuration
│   ├── requirements.txt         # Python dependencies
│   └── README.md                # Server documentation
│
├── client/                      # Web client (React + TypeScript + Vite, installable PWA)
│   ├── src/screens/             # Opening screen, lobby, table, result
│   ├── src/components/          # Cards, hand, seats, chat, hints
│   ├── src/services/            # Socket connection
│   └── src/i18n/                # Hungarian and English texts
│
├── docs/                        # Player guide (Hungarian)
├── QUICK_START.md               # Quick start guide
└── README.md                    # This file
```

## 🎴 Game Overview

**Hungarian Tarokk** is a 4-player trick-taking game using a 42-card deck:
- **22 Tarokk (Trump) Cards**: skíz, XXI-II, pagát (I)
- **20 Suit Cards**: K, Q, C, J and a fifth card in 4 suits: the 10 in Spades and Clubs, the Ace in Hearts and Diamonds

**Objective**: Declarer and partner must score 48+ points (out of 94 total)

**Game Flow**:
1. **Bidding**: Players bid for declarer position (must have honour card)
2. **Talon**: Declarer and others receive cards from 6-card talon
3. **Discard**: All players discard to 9 cards (cannot discard Kings/Honours)
4. **Partner Call**: Declarer calls a tarokk card (usually XX)
5. **Trick-Taking**: 9 tricks, must follow suit, tarokk is trump
6. **Scoring**: Count points, declarer team needs 48+ to win

See [HUNGARIAN_TAROKK_RULES.md](server/HUNGARIAN_TAROKK_RULES.md) for complete rules.

## 🛠️ Technology Stack

**Server:**
- Python 3.10+
- FastAPI (web framework)
- python-socketio (WebSocket/Socket.IO)
- Pydantic (data validation)
- structlog (structured logging)
- pytest (testing)

**Web client:**
- React + TypeScript
- Vite (build, PWA)
- socket.io-client

## 📖 Documentation

- **[QUICK_START.md](QUICK_START.md)** - Get started in 5 minutes
- **[server/README.md](server/README.md)** - Server documentation, API reference
- **[HUNGARIAN_TAROKK_RULES.md](server/HUNGARIAN_TAROKK_RULES.md)** - Complete game rules

## 🧪 Testing

### Server

```bash
cd server
pytest                    # Run all tests
pytest -v                 # Verbose output
```

The tests cover the rules, one test per bot rule, 300 whole hands played by
four bots, saving and restoring a table at every moment of a hand, the
statistics and the limits.

### Web client

```bash
cd client
npx tsc --noEmit && npm test && npm run build
```

### Does a running game survive a restart?

```bash
cd server
pip install "python-socketio[client]"     # only this trial needs it
python tools/restart_trial.py             # against a server started from this folder
python tools/restart_trial.py image NAME  # against a Docker image, with a data volume
```

A player sits down against three bots, the server is restarted in the fourth
trick, and the trial checks that the player is back at the same table and the
hand can be finished.

## 🎯 API Overview

### WebSocket Connection

```javascript
const socket = io('http://localhost:8000', {
  path: '/socket.io'
});
```

### Client → Server Events

- `join_room` - Join or create a room
- `ready` - Mark ready to start game
- `place_bid` - Place bid (three/two/one/solo/pass/hold)
- `discard_cards` - Discard cards
- `call_partner` - Call partner card
- `play_card` - Play a card

### Server → Client Events

- `room_state` - Room info and players
- `game_state` - Current game state
- `your_turn` - Your turn with valid actions
- `bid_placed` - Bid notification
- `card_played` - Card played notification
- `trick_complete` - Trick winner
- `game_over` - Final scores

See [server/README.md](server/README.md) for complete API documentation.

## 🔧 Development

### Server

```bash
cd server
pip install -r requirements.txt
python main.py            # development mode: restarts on every code change
pytest
```

`DEBUG=false python main.py` runs it the way production does: no reloader,
quiet logs, and on shutdown it tells the players and saves every table.

### Web client

```bash
cd client
npm install
VITE_SERVER_URL=http://localhost:8000 npm run dev
```

### Production

The client is built by Netlify on every push to `main`. The server is
deployed with `server/deploy.sh` (tests, image tagged with the commit,
rollout, health check; `./deploy.sh rollback` goes back one version).
`server/tools/stats.sh` prints the hands played per day.

## 🌟 Example Usage

### JavaScript/TypeScript Client

```javascript
import { io } from 'socket.io-client';

const socket = io('http://localhost:8000');

// Join room
socket.emit('join_room', { player_name: 'Alice' });

// Listen for events
socket.on('game_state', (data) => {
  console.log('Game state:', data);
});

socket.on('your_turn', (data) => {
  console.log('Your turn! Valid actions:', data.valid_actions);
});

// Place bid
socket.emit('place_bid', { bid_type: 'three' });

// Play card
socket.emit('play_card', { card_id: 'card-uuid' });
```

## 📝 Game Rules Summary

### Deck (42 cards, 94 points total)

**Tarokks (22 cards):**
- Honours (5 pts each): skíz, XXI, pagát (I)
- Others (1 pt each): XX-II

**Suits (20 cards, 5 per suit):**
- King (5 pts), Queen (4 pts), Cavalier (3 pts), Jack (2 pts), Ten in the black suits / Ace in the red suits (1 pt)

### Bidding

- **Requirement**: Must have honour (skíz, XXI, or pagát) to bid
- **Bids** (ascending): three → two → one → solo
- **Hold**: Match highest bid (only if already bid)
- **Direction**: Counter-clockwise from dealer's right

### Talon & Discard

- **Declarer takes**: Solo=0, One=1, Two=2, Three=3 cards
- **Others receive**: Remaining talon cards
- **All discard to 9 cards**: Cannot discard Kings or Honours

### Partner & Teams

- **Declarer calls**: A tarokk card (usually XX)
- **Partner**: Player holding that card (identity hidden until played)
- **Teams**: Declarer + Partner vs. Other 2

### Trick-Taking

- **9 tricks total**
- **First lead**: Dealer's right
- **Must follow suit**
- **If void**: Must play tarokk
- **Trump**: Tarokk beats all suits

### Scoring

- **To win**: Declarer team needs 48+ points
- **Payment**: Based on game value and bonuses

## 🐛 Troubleshooting

### Server won't start

```bash
# Check if port 8000 is in use
lsof -ti:8000 | xargs kill -9

# Or change port
PORT=8001 python main.py
```

### Connection refused

1. Ensure server is running
2. Check server URL is correct
3. Verify firewall settings

### Module not found

```bash
# Reinstall dependencies
pip install -r requirements.txt
```

### Tests failing

1. Restart server
2. Wait 2-3 seconds for startup
3. Run tests again

## 🤝 Contributing

Contributions welcome! Open ideas:

- Hand annulment
- 5-player variant
- Game replay system
- Player accounts and rankings

## 📜 License

MIT – see [LICENSE](LICENSE).

## 🙏 Credits

Game rules based on:
- https://www.pagat.com/tarot/xx-hivas.html

## 📧 Support

For issues, questions, or suggestions, please check:
- Server logs for error messages
- [QUICK_START.md](QUICK_START.md) for setup help
- The problem report in the app (☰ → report a problem), which stores the whole table with your description

---

**Enjoy playing Hungarian Tarokk!** 🎴🃏
