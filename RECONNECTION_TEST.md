# How to Test Persistence & Reconnection

## Current Status
✅ Persistence is working correctly
✅ Game state is saved to database
✅ Game state is loaded on server restart
✅ Player hands are fully restored

## Testing Reconnection

### Step 1: Start a Game
1. Start the server
2. Connect 4 players (save their player IDs from browser localStorage)
3. Play a few hands
4. **DON'T close the clients yet**

### Step 2: Restart Server (While Clients Stay Open)
1. Stop the server (Ctrl+C)
2. Server saves all rooms on shutdown
3. Restart the server
4. Server loads all rooms from database

### Step 3: Clients Automatically Reconnect
The clients should automatically:
1. Detect disconnection
2. Try to reconnect with their stored `player_id`
3. Server finds them in the database
4. Game state is sent back
5. Game continues from exact point

### Step 4: Manual Reconnection (If Auto-Reconnect Fails)
If a client closes completely:
1. Reopen the page
2. Enter the same name
3. Client sends stored `player_id` when joining
4. Server recognizes the player
5. Full state restored

## What Gets Persisted

✅ **Player Data:**
- Unique player IDs
- Names and positions
- Current hands (all cards)
- Tricks won
- Discard piles

✅ **Game State:**
- Current phase (playing, bidding, etc.)
- Current turn
- Trick number
- Talon cards
- Current trick
- Bid history
- Announcements
- Trick history

✅ **Room Data:**
- Room ID
- Chat messages (last 100)
- All player sessions

## Checking What's in the Database

```bash
# View all rooms
sqlite3 data/tarokk_game.db "SELECT room_id, phase, trick_number FROM game_states;"

# View all players
sqlite3 data/tarokk_game.db "SELECT name, position, is_connected FROM players;"

# View chat messages
sqlite3 data/tarokk_game.db "SELECT player_name, message FROM chat_messages LIMIT 10;"

# Check player hands are saved
sqlite3 data/tarokk_game.db "SELECT json_extract(game_data, '$.players[0].hand') FROM game_states;" | python3 -m json.tool
```

## Reconnection Flow Details

### Server Side (Already Implemented)
1. On startup: Load all rooms from database
2. Mark all players as disconnected
3. When player connects with player_id:
   - Find player in database
   - Update session_id
   - Mark as connected
   - Send full game state
   - Send chat history

### Client Side (Need to Check)
The client needs to:
1. ✅ Store player_id in localStorage (already done via zustand persist)
2. ✅ Send player_id when joining room (already implemented)
3. ✅ Handle reconnection on socket disconnect (already implemented)

## Expected Behavior

### Scenario 1: Server Restart (Clients Stay Open)
- Clients show "reconnecting" status
- Server restarts and loads rooms
- Clients reconnect automatically
- Game continues seamlessly

### Scenario 2: Client Closes and Reopens
- Client reopens page
- Player name is remembered (localStorage)
- Client sends player_id when joining
- Server finds player in database
- Full game state sent to client
- Game continues

### Scenario 3: Long Disconnect
- Player disconnects for >5 minutes
- Other players see them as disconnected
- Game pauses or continues (depending on rules)
- Player reconnects with same player_id
- Game resumes

## Troubleshooting

### Players Can't Reconnect
Check:
1. Is player_id being stored in client localStorage?
   - Open DevTools → Application → Local Storage
   - Look for `tarokk-game-storage`
2. Is player_id being sent to server?
   - Check network tab for `join_room` message
3. Is server finding the player?
   - Check server logs for "player_reconnected"

### Game State Not Restored
Check:
1. Server logs on startup for "rooms_loaded_on_startup"
2. Database has data: `sqlite3 data/tarokk_game.db "SELECT COUNT(*) FROM rooms;"`
3. game_data JSON is not null

### Cards Missing After Reconnect
Check:
1. Player hands in database: Run the JSON query above
2. Server logs for "room_loaded" message
3. Client receives full game_state (check network tab)

## Current Test Results

From test_persistence.py:
```
✓ Loaded 1 room
✓ 4 players with complete hands (8 cards each)
✓ Game phase: playing (trick 2)
✓ All cards reconstructed correctly
✓ Chat messages preserved (4 messages)
```

## Next Steps to Verify

1. **Test auto-reconnection:**
   - Keep clients open
   - Restart server
   - Check if clients reconnect automatically

2. **Test manual reconnection:**
   - Close a client
   - Reopen page
   - Check if player rejoins with same state

3. **Test mid-game restart:**
   - Play to middle of a hand
   - Restart server
   - Verify all cards/state preserved

If any of these fail, we can debug the specific issue.
