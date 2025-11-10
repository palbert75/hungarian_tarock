# Hungarian Tarokk Game Server

A real-time WebSocket server for playing Hungarian Tarokk (Illustrated Hungarian Tarokk / XX Hívás), a 4-player trick-taking card game.

## Features

- Real-time multiplayer gameplay using WebSockets
- Complete implementation of Hungarian Tarokk rules
- 42-card deck (Industrie und Glück)
- Bidding system with honour requirements
- Talon distribution and discard phase
- Partner calling mechanism
- Trick-taking with follow suit rules
- Automatic scoring and winner determination
- Room/lobby management for 4 players
- Reconnection support

## Project Structure

```
server/
├── models/              # Data models
│   ├── card.py         # Card, Suit, Rank definitions
│   ├── deck.py         # 42-card deck
│   ├── player.py       # Player state
│   ├── game_state.py   # Central game state
│   └── bid.py          # Bid types
├── game_logic/          # Game rules implementation
│   ├── bidding.py      # Bidding validation
│   └── scoring.py      # Point calculation
├── validation/          # Rule validators
│   └── rules.py        # Legal move validation
├── networking/          # WebSocket server
│   ├── server.py       # Socket.IO handlers
│   ├── protocol.py     # Message protocol
│   └── room_manager.py # Room management
├── utils/               # Utilities
│   └── position.py     # Counter-clockwise helpers
├── tests/               # Unit tests
├── config.py            # Configuration
└── main.py              # Entry point
```

## Installation

### Prerequisites

- Python 3.10 or higher
- pip

### Setup

1. Clone the repository:
```bash
cd /Users/papp/Documents/Secret/tarokk/server
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create environment file:
```bash
cp .env.example .env
# Edit .env with your configuration
```

## Running the Server

### Development Mode

```bash
python -m server.main
```

Or using uvicorn directly:
```bash
uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
```

The server will start on `http://localhost:8000`

### Production Mode

```bash
# Set DEBUG=False in .env
uvicorn server.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=server --cov-report=html

# Run specific test file
pytest tests/test_deck.py

# Run with verbose output
pytest -v
```

## API Documentation

### WebSocket Events

#### Client → Server Events

**connect**
- Fired when client connects

**create_room**
```json
{
  "player_name": "Alice"
}
```

**join_room**
```json
{
  "room_id": "uuid",
  "player_name": "Bob"
}
```

**ready**
```json
{}
```

**place_bid**
```json
{
  "bid_type": "three" | "two" | "one" | "solo" | "pass" | "hold"
}
```

**discard_cards**
```json
{
  "card_ids": ["card_uuid1", "card_uuid2", ...]
}
```

**call_partner**
```json
{
  "tarokk_rank": "XX"
}
```

**play_card**
```json
{
  "card_id": "card_uuid"
}
```

#### Server → Client Events

**room_state**
```json
{
  "room_id": "uuid",
  "players": [
    {
      "id": "uuid",
      "name": "Alice",
      "position": 0,
      "is_ready": true,
      "is_connected": true
    }
  ],
  "is_full": false,
  "game_started": false
}
```

**game_state**
```json
{
  "game_id": "uuid",
  "phase": "bidding" | "discarding" | "playing" | ...,
  "current_turn": 2,
  "dealer_position": 0,
  "your_position": 1,
  "your_hand": [...],
  "players": [...],
  "bid_history": [...],
  "trick_number": 1
}
```

**your_turn**
```json
{
  "valid_actions": ["place_bid"],
  "valid_bids": ["three", "two", "pass"],
  "valid_cards": ["card_uuid1", ...]
}
```

**bid_placed**
```json
{
  "player_position": 2,
  "bid_type": "three"
}
```

**card_played**
```json
{
  "player_position": 1,
  "card": {
    "suit": "hearts",
    "rank": "K",
    "points": 5
  }
}
```

**trick_complete**
```json
{
  "winner": 1,
  "cards": [...],
  "points_in_trick": 8
}
```

**game_over**
```json
{
  "declarer": 1,
  "partner": 3,
  "declarer_team_points": 52,
  "opponent_team_points": 42,
  "winner": "declarer_team",
  "game_value": 3
}
```

**error**
```json
{
  "code": "BID_ERROR",
  "message": "Must have at least one honour to bid"
}
```

## Game Rules

See [HUNGARIAN_TAROKK_RULES.md](../HUNGARIAN_TAROKK_RULES.md) for complete rules documentation.

### Quick Summary

1. **Setup**: 4 players, 42-card deck, 9 cards per player + 6 card talon
2. **Bidding**: Counter-clockwise from dealer's right, must have honour (skíz/XXI/pagát) to bid
3. **Talon**: Declarer and others receive cards from talon based on bid
4. **Discard**: All players discard to 9 cards (cannot discard Kings or Honours)
5. **Partner**: Declarer calls a tarokk card to designate partner (usually XX)
6. **Tricks**: 9 tricks, dealer's right leads first, must follow suit, tarokk is trump
7. **Scoring**: Declarer's team needs 48+ points (out of 94 total) to win

## Configuration

Edit `.env` file:

```env
# Server
HOST=0.0.0.0
PORT=8000
DEBUG=True

# Logging
LOG_LEVEL=INFO

# CORS
CORS_ORIGINS=*

# Game
MAX_ROOMS=100
ROOM_TIMEOUT_MINUTES=60
```

## Client Integration

### JavaScript/TypeScript Example

```javascript
import { io } from 'socket.io-client';

const socket = io('http://localhost:8000', {
  path: '/socket.io'
});

// Connect
socket.on('connect', () => {
  console.log('Connected!');

  // Join or create room
  socket.emit('join_room', {
    player_name: 'Alice'
  });
});

// Listen for room state
socket.on('room_state', (data) => {
  console.log('Room state:', data);
});

// Listen for game state
socket.on('game_state', (data) => {
  console.log('Game state:', data);
});

// Place bid
socket.emit('place_bid', {
  bid_type: 'three'
});

// Play card
socket.emit('play_card', {
  card_id: 'card-uuid'
});
```

## Development

### Code Quality

```bash
# Linting with ruff
ruff check server/

# Auto-fix issues
ruff check --fix server/

# Format code
ruff format server/
```

### Adding New Features

1. Update models in `server/models/`
2. Implement game logic in `server/game_logic/`
3. Add validation in `server/validation/`
4. Update server handlers in `server/networking/server.py`
5. Add tests in `tests/`
6. Update documentation

## Troubleshooting

### Common Issues

**Port already in use**
```bash
# Change PORT in .env or kill existing process
lsof -ti:8000 | xargs kill -9
```

**Module not found**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

**Connection issues**
- Check CORS_ORIGINS in .env
- Ensure firewall allows port 8000
- Verify client is connecting to correct URL/port

## License

[Add your license here]

## Contributing

[Add contributing guidelines]

## Credits

Based on the Hungarian Tarokk card game rules from:
- https://www.pagat.com/tarot/xx-hivas.html

## Support

[Add support contact information]
