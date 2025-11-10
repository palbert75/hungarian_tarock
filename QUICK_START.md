# Hungarian Tarokk - Quick Start Guide

Get up and running with the Hungarian Tarokk game server in 5 minutes!

## Prerequisites

- Python 3.10 or higher
- pip (Python package installer)

## Quick Setup

### 1. Install Server Dependencies

```bash
cd server
pip install -r requirements.txt
```

### 2. Install Test Client Dependencies

```bash
cd ../test_client
pip install -r requirements.txt
```

## Run Your First Test

### Terminal 1: Start the Server

```bash
cd server
python -m server.main
```

You should see:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Terminal 2: Run Quick Test

```bash
cd test_client
python quick_test.py
```

You should see:
```
🎮 Hungarian Tarokk - Quick Test

✓ Connected successfully
✓ Room created
✓ Room state received
✓ Quick test completed successfully!
```

## Interactive Testing (4 Players)

### Start Interactive Test Client

```bash
cd test_client
python interactive_test.py
```

**Walkthrough:**

1. **Setup Phase** (automatic)
   - 4 players created: Alice, Bob, Charlie, Diana
   - All join the same room
   - Prompt: "Mark all players ready and start game?"
   - Answer: `yes`

2. **Game Starts** (automatic)
   - Cards dealt (9 per player + 6 talon)
   - Bidding phase begins
   - You'll see the main menu

3. **Main Menu Options**
   ```
   1. View all players' hands        <- See everyone's cards
   2. View game state                <- Check current phase
   3. Switch active player           <- Change who you're controlling
   4. Place bid (current player)     <- Bid in auction
   5. Discard cards (current player) <- Discard to 9 cards
   6. Call partner (current player)  <- Call partner card
   7. Play card (current player)     <- Play a card
   8. Auto-play current turn         <- Let AI play current turn
   9. View current player's options  <- See what's legal
   0. Quit
   ```

4. **Recommended First Test Flow**

   a. View the game state:
   ```
   Choose action: 2
   ```

   b. See all hands:
   ```
   Choose action: 1
   ```

   c. Auto-play through the game:
   ```
   Choose action: 8
   (Repeat option 8 until game completes)
   ```

## Automated Full Test

### Run Complete Test Suite

```bash
cd test_client
python automated_test.py
```

This will automatically:
1. Test connections
2. Test basic game flow
3. Test bidding phase
4. Play a complete game

Results shown at the end:
```
✓ PASSED - Connection Test
✓ PASSED - Basic Game Flow
✓ PASSED - Bidding Phase
✓ PASSED - Full Game Simulation

🎉 All tests passed!
```

## Common Commands

### Start Server
```bash
cd server
python -m server.main
```

### Run Server Tests
```bash
cd server
pytest
pytest -v                  # Verbose
pytest --cov=server        # With coverage
```

### Quick Connection Test
```bash
cd test_client
python quick_test.py
```

### Interactive 4-Player Test
```bash
cd test_client
python interactive_test.py
```

### Automated Test Suite
```bash
cd test_client
python automated_test.py
```

## Manual Testing Example

Let's manually test a bidding phase:

1. **Start server** (Terminal 1)
   ```bash
   cd server
   python -m server.main
   ```

2. **Start interactive client** (Terminal 2)
   ```bash
   cd test_client
   python interactive_test.py
   ```

3. **Mark all ready** when prompted
   ```
   Mark all players ready and start game? [y/n] (y): y
   ```

4. **View game state** (option 2)
   ```
   Choose action: 2

   Phase: bidding
   Current Turn: 1
   Dealer: 0
   ```

5. **Check who has turn** - Look at "Current Turn" number

6. **Switch to that player** (option 3)
   ```
   Choose action: 3
   Select player [0/1/2/3]: 1
   Switched to Bob
   ```

7. **View their hand** (option 1)
   ```
   Choose action: 1

   Bob's Hand:
   #  Card              Points  ID
   0  Tarokk XXI        5       abc123...
   1  K of hearts       5       def456...
   ...
   ```

8. **Check if they have honours** - Look for skíz, XXI, or I (pagát)

9. **Place a bid** (option 4)
   ```
   Choose action: 4
   Valid bids: three, two, pass
   Bid for Bob: three
   ✓ Placed bid: three
   ```

10. **Continue for all 4 players** - Repeat steps 6-9 for remaining players

## Project Structure

```
tarokk/
├── server/                          # Game server
│   ├── models/                      # Data models (Card, Player, GameState)
│   ├── game_logic/                  # Game rules (bidding, scoring)
│   ├── validation/                  # Rule validators
│   ├── networking/                  # WebSocket server
│   ├── tests/                       # Unit tests
│   ├── main.py                      # Server entry point
│   └── README.md                    # Server documentation
│
├── test_client/                     # Test clients
│   ├── client.py                    # Socket.IO client library
│   ├── interactive_test.py          # Interactive 4-player CLI
│   ├── automated_test.py            # Automated test suite
│   ├── quick_test.py                # Quick smoke test
│   └── README.md                    # Test client documentation
│
├── HUNGARIAN_TAROKK_RULES.md        # Complete game rules
└── QUICK_START.md                   # This file
```

## Next Steps

### Learn the Game Rules
```bash
# Read comprehensive rules documentation
cat server/HUNGARIAN_TAROKK_RULES.md
```

### Explore the Code
- Start with `server/models/card.py` - Card and deck implementation
- Then `server/models/game_state.py` - Central game logic
- Check `server/networking/server.py` - WebSocket event handlers

### Run Unit Tests
```bash
cd server
pytest -v
```

### Build a Client
See `test_client/client.py` for example Socket.IO client implementation.

## Troubleshooting

### "Connection refused"
- Make sure server is running: `cd server && python -m server.main`
- Check server is on port 8000: Look for "Running on http://0.0.0.0:8000"

### "Module not found"
```bash
# Server dependencies
cd server
pip install -r requirements.txt

# Test client dependencies
cd test_client
pip install -r requirements.txt
```

### "Port already in use"
```bash
# Find and kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Or change port in server/.env
PORT=8001
```

### Tests failing
1. Restart the server
2. Wait 2-3 seconds after server starts
3. Try again

## Getting Help

- **Server Documentation**: `server/README.md`
- **Test Client Documentation**: `test_client/README.md`
- **Game Rules**: `server/HUNGARIAN_TAROKK_RULES.md`
- **API Reference**: Check `server/networking/protocol.py`

## Quick Reference

### WebSocket Events (Client → Server)
- `join_room` - Join/create a room
- `ready` - Mark ready to start
- `place_bid` - Place a bid (three/two/one/solo/pass/hold)
- `discard_cards` - Discard cards to 9
- `call_partner` - Call partner card (usually XX)
- `play_card` - Play a card to trick

### WebSocket Events (Server → Client)
- `room_state` - Room info and players
- `game_state` - Current game state
- `your_turn` - Your turn notification
- `bid_placed` - Someone placed a bid
- `card_played` - Someone played a card
- `trick_complete` - Trick finished
- `game_over` - Game finished

### Game Phases
1. `waiting` - Lobby, waiting for players
2. `dealing` - Dealing cards
3. `bidding` - Auction phase
4. `talon_distribution` - Distributing talon cards
5. `discarding` - Players discard to 9 cards
6. `partner_call` - Declarer calls partner
7. `playing` - Trick-taking
8. `scoring` - Counting points
9. `game_end` - Game finished

Enjoy playing Hungarian Tarokk! 🎴
