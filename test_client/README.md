# Hungarian Tarokk Test Client

Interactive and automated testing tools for the Hungarian Tarokk game server.

## Features

- **Interactive Multi-Player Testing**: Control 4 different players simultaneously
- **Automated Test Scenarios**: Run complete game simulations
- **Quick Connection Tests**: Verify server is running
- **Rich CLI Interface**: Beautiful terminal UI with colors and tables

## Installation

```bash
cd test_client
pip install -r requirements.txt
```

## Test Scripts

### 1. Interactive Test Client (`interactive_test.py`)

Control 4 players interactively to manually test game flow.

**Usage:**
```bash
python interactive_test.py [server_url]

# Examples:
python interactive_test.py
python interactive_test.py http://localhost:8000
```

**Features:**
- View all players' hands
- View current game state
- Switch between players
- Place bids, discard cards, play cards
- Auto-play current turn
- View available options for each player

**Menu Options:**
```
1. View all players' hands
2. View game state
3. Switch active player
4. Place bid (current player)
5. Discard cards (current player)
6. Call partner (current player)
7. Play card (current player)
8. Auto-play current turn
9. View current player's options
0. Quit
```

### 2. Automated Test Suite (`automated_test.py`)

Run automated tests to verify server functionality.

**Usage:**
```bash
python automated_test.py [server_url]

# Examples:
python automated_test.py
python automated_test.py http://localhost:8000
```

**Test Scenarios:**
- Connection/disconnection
- Basic game flow (setup → bidding)
- Bidding phase validation
- Full game simulation (complete game)

**Output:**
- ✓ PASSED / ✗ FAILED for each test
- Summary of results
- Exit code 0 (success) or 1 (failure)

### 3. Quick Test (`quick_test.py`)

Rapid verification that server is running and responsive.

**Usage:**
```bash
python quick_test.py [server_url]

# Examples:
python quick_test.py
python quick_test.py http://localhost:8000
```

**Tests:**
- Server connection
- Room creation
- Room state updates

## Using the Client Library

### Basic Usage

```python
from client import TarokkClient

# Create client
client = TarokkClient("http://localhost:8000", "PlayerName")

# Connect
client.connect()

# Join/create room
client.join_room()

# Mark ready
client.ready()

# Place bid
client.place_bid("three")

# Discard cards
client.discard_cards(["card_id1", "card_id2"])

# Call partner
client.call_partner("XX")

# Play card
client.play_card("card_id")

# Disconnect
client.disconnect()
```

### Event Handlers

```python
# Register custom event handler
def on_game_started(data):
    print("Game started!", data)

client.on("game_started", on_game_started)

# Available events:
# - room_state
# - game_state
# - game_started
# - your_turn
# - bid_placed
# - talon_distributed
# - player_discarded
# - partner_called
# - partner_revealed
# - card_played
# - trick_complete
# - game_over
# - error
```

### Accessing Game State

```python
# Get current hand
hand = client.get_hand()

# Print hand nicely
client.print_hand()

# Print game state
client.print_game_state()

# Access raw game state
game_state = client.game_state
phase = game_state.get("phase")
current_turn = game_state.get("current_turn")
your_position = game_state.get("your_position")
```

## Testing Workflow

### Manual Testing Flow

1. **Start the server**
   ```bash
   cd ../server
   python -m server.main
   ```

2. **Run interactive test client**
   ```bash
   cd ../test_client
   python interactive_test.py
   ```

3. **Test game flow**
   - Script will auto-create 4 players and room
   - Mark all ready to start game
   - Use menu to control each player through:
     - Bidding phase
     - Talon distribution
     - Discard phase
     - Partner calling
     - Trick-taking
     - Scoring

### Automated Testing Flow

1. **Start the server**
   ```bash
   cd ../server
   python -m server.main
   ```

2. **Run automated tests**
   ```bash
   cd ../test_client
   python automated_test.py
   ```

3. **Review results**
   - Tests run automatically
   - Results printed at end
   - Exit code indicates success/failure

### Quick Smoke Test

```bash
# Terminal 1: Start server
cd server
python -m server.main

# Terminal 2: Run quick test
cd test_client
python quick_test.py
```

## Simulating a 4-Player Game

### Using Interactive Client

```bash
python interactive_test.py
```

**Steps:**
1. Say "yes" when prompted to mark all ready
2. Game starts automatically
3. Use menu option 8 "Auto-play current turn" to quickly progress
4. Or manually control each player through options 4-7

**Tips:**
- Option 1: See all hands at once
- Option 2: Check game phase and status
- Option 9: See what current player can do
- Option 8: Auto-play for faster testing

### Using Automated Test

```bash
python automated_test.py
```

The "Full Game Simulation" test will play a complete game automatically.

## Troubleshooting

### Connection Refused

**Problem:** `Connection refused` or `Failed to connect`

**Solutions:**
1. Ensure server is running: `cd ../server && python -m server.main`
2. Check server URL is correct (default: `http://localhost:8000`)
3. Verify port 8000 is not blocked by firewall

### Module Not Found

**Problem:** `ModuleNotFoundError: No module named 'socketio'`

**Solution:** Install dependencies
```bash
pip install -r requirements.txt
```

### Rich Not Displaying Colors

**Problem:** No colors in terminal output

**Solution:** Use a terminal that supports ANSI colors (most modern terminals do)

### WebSocket Errors

**Problem:** WebSocket connection errors

**Solutions:**
1. Check server logs for errors
2. Ensure server is running in async mode
3. Verify Socket.IO versions match (client and server)

## Advanced Usage

### Custom Test Scenario

```python
from client import TarokkClient
import time

# Create 4 players
players = [
    TarokkClient("http://localhost:8000", f"Player{i}")
    for i in range(4)
]

# Connect all
for p in players:
    p.connect()
    time.sleep(0.5)

# Create room
players[0].join_room()
time.sleep(1)

room_id = players[0].room_id

# Others join
for p in players[1:]:
    p.join_room(room_id)
    time.sleep(0.5)

# Mark ready
for p in players:
    p.ready()
    time.sleep(0.3)

time.sleep(2)

# Now game should be in bidding phase
# ... implement your custom test logic ...

# Cleanup
for p in players:
    p.disconnect()
```

### Monitoring Specific Events

```python
client = TarokkClient("http://localhost:8000", "Observer")
client.connect()

# Track all bids
bids = []

def track_bid(data):
    bids.append(data)
    print(f"Bid placed: {data}")

client.on("bid_placed", track_bid)

# Join room and observe
client.join_room("room-id")

# Wait and collect data
time.sleep(60)

print(f"Total bids observed: {len(bids)}")
```

## Files

- `client.py` - Core Socket.IO client library
- `interactive_test.py` - Interactive 4-player CLI
- `automated_test.py` - Automated test suite
- `quick_test.py` - Quick connection test
- `requirements.txt` - Python dependencies
- `README.md` - This file

## Requirements

- Python 3.10+
- python-socketio[client] 5.11.0
- rich 13.7.1
- prompt-toolkit 3.0.47

## See Also

- [Server README](../server/README.md) - Server documentation
- [Game Rules](../server/HUNGARIAN_TAROKK_RULES.md) - Complete game rules

## Support

For issues or questions, check the server logs for error messages.
