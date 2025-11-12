# Game Persistence System

## Overview

The Hungarian Tarokk server now includes a comprehensive SQLite-based persistence layer that preserves game rooms and states across server restarts. This ensures players can reconnect to ongoing games even if the server crashes or needs to be restarted.

## Architecture

### Components

1. **Database Layer** (`persistence/database.py`)
   - SQLite database with proper schema
   - Tables for rooms, players, game states, and chat messages
   - ACID-compliant transactions

2. **Persistence Manager** (`persistence/persistence_manager.py`)
   - Coordinates saving and loading of complete game state
   - Handles serialization/deserialization of complex objects
   - Manages room lifecycle

3. **Server Integration** (`networking/server.py`)
   - Auto-save hooks after every state change
   - Initialization on startup
   - Graceful shutdown with final save

## Database Schema

### Tables

#### `rooms`
- `room_id` (TEXT, PRIMARY KEY)
- `created_at` (TIMESTAMP)
- `last_activity` (TIMESTAMP)
- `is_active` (INTEGER) - Soft delete flag

#### `players`
- `player_id` (TEXT, PRIMARY KEY)
- `room_id` (TEXT, FOREIGN KEY)
- `name` (TEXT)
- `position` (INTEGER)
- `is_connected` (INTEGER)
- `is_ready` (INTEGER)
- `session_id` (TEXT) - NULL until player reconnects

#### `game_states`
- `room_id` (TEXT, PRIMARY KEY, FOREIGN KEY)
- `phase` (TEXT) - Current game phase
- `current_turn` (INTEGER)
- `dealer_position` (INTEGER)
- `declarer_position` (INTEGER, NULLABLE)
- `partner_position` (INTEGER, NULLABLE)
- `partner_revealed` (INTEGER)
- `called_card_rank` (TEXT, NULLABLE)
- `trick_number` (INTEGER)
- `game_data` (JSON) - Complete game state blob
- `updated_at` (TIMESTAMP)

#### `chat_messages`
- `id` (TEXT, PRIMARY KEY)
- `room_id` (TEXT, FOREIGN KEY)
- `player_name` (TEXT)
- `message` (TEXT)
- `timestamp` (INTEGER)

### Indices
- `idx_players_room` on `players(room_id)`
- `idx_chat_room` on `chat_messages(room_id, timestamp)`

## Features

### Automatic Saving

The system automatically saves game state after:
- Player joins/leaves a room
- Player marks ready
- Bids are placed
- Cards are discarded
- Partner is called
- Announcements are made
- Cards are played
- Tricks are completed
- Game ends

### Startup Behavior

On server startup:
1. All persisted rooms are loaded from database
2. All players are marked as disconnected
3. Session IDs are cleared (players must reconnect)
4. Game state is fully restored including:
   - Player hands
   - Talon cards
   - Current trick
   - Bid history
   - Announcements
   - Trick history
   - Chat messages (last 100)

### Reconnection Flow

1. Player tries to join with their player_id
2. Server finds existing player in database
3. Player's session_id is updated
4. Player marked as connected
5. Full game state sent to player
6. Chat history sent to player
7. Game continues seamlessly

### Graceful Shutdown

On server shutdown (Ctrl+C):
1. All active rooms are saved
2. Database connection is closed cleanly
3. No data loss occurs

## Data Retention

- **Active Rooms**: Kept indefinitely while players are present
- **Inactive Rooms**: Automatically cleaned up after 7 days
- **Chat History**: Last 100 messages per room
- **Game States**: Complete state including all cards

## Configuration

Database location can be configured in `main.py`:

```python
await init_persistence("data/tarokk_game.db")  # Default location
```

The database file is created automatically in the `data/` directory.

## What Gets Persisted

### Complete Game State
- ✅ All player information (ID, name, position, ready status)
- ✅ Complete hands for all players
- ✅ Talon cards
- ✅ Current trick and trick history
- ✅ Bid history and winning bid
- ✅ Declarer and partner positions
- ✅ Announcements (including contra/recontra)
- ✅ Game phase
- ✅ Current turn
- ✅ Discard piles
- ✅ Chat messages

### Session Information
- Player connection status (marked disconnected on restart)
- Session IDs (cleared on restart, rebuilt on reconnection)

## Recovery Scenarios

### Scenario 1: Server Crash During Game
1. Server crashes mid-game
2. All game state is already in database (auto-saved)
3. Server restarts
4. Players reconnect with their player_id
5. Game continues from exact point

### Scenario 2: Planned Maintenance
1. Graceful shutdown (Ctrl+C)
2. All rooms saved to database
3. Server restarts
4. Rooms restored
5. Players reconnect
6. Games resume

### Scenario 3: One Player Disconnects
1. Player loses connection
2. Player marked as disconnected (not removed)
3. Game waits for player
4. Player reconnects
5. Full state sent to player
6. Game continues

## Performance Considerations

### Write Performance
- Auto-saves are async (non-blocking)
- SQLite uses WAL mode for concurrent reads
- Saves typically complete in <10ms

### Read Performance
- Database loaded once on startup
- In-memory operations during gameplay
- No database reads during active play

### Storage
- Average game: ~50KB in database
- 100 concurrent games: ~5MB
- Chat messages: ~500 bytes each

## Backup Strategy

### Manual Backup
```bash
cp data/tarokk_game.db data/backup_$(date +%Y%m%d_%H%M%S).db
```

### Automated Backup (Recommended)
```bash
# Add to crontab
0 */6 * * * cp /path/to/data/tarokk_game.db /path/to/backups/tarokk_$(date +\%Y\%m\%d_\%H\%M\%S).db
```

## Maintenance

### Cleanup Old Rooms
Automatic cleanup runs on startup for rooms inactive >7 days.

Manual cleanup:
```python
await persistence_manager.cleanup_old_rooms(days=7)
```

### Database Optimization
```bash
sqlite3 data/tarokk_game.db "VACUUM;"
```

## Monitoring

### Check Database Size
```bash
ls -lh data/tarokk_game.db
```

### Query Active Rooms
```bash
sqlite3 data/tarokk_game.db "SELECT COUNT(*) FROM rooms WHERE is_active=1;"
```

### Query Total Players
```bash
sqlite3 data/tarokk_game.db "SELECT COUNT(*) FROM players;"
```

## Troubleshooting

### Database Locked Error
- Ensure only one server instance is running
- Check for zombie processes
- Restart server if needed

### Corruption Recovery
```bash
# Check database integrity
sqlite3 data/tarokk_game.db "PRAGMA integrity_check;"

# If corrupted, restore from backup
cp data/backup_latest.db data/tarokk_game.db
```

### Reset All Data
```bash
# Backup first!
mv data/tarokk_game.db data/tarokk_game.db.old

# Fresh start
# New database will be created on next startup
```

## Migration from Non-Persistent Version

If upgrading from a version without persistence:
1. All existing in-memory games will be saved on next shutdown
2. On startup, database will be created automatically
3. No manual migration needed

## Future Enhancements

Potential improvements:
- PostgreSQL support for distributed deployments
- Real-time replication for high availability
- Periodic snapshots for point-in-time recovery
- Audit logging for game actions
- Analytics and statistics storage

## Security Considerations

- Database stored locally (no network exposure)
- No sensitive data stored (no passwords, payment info)
- Player IDs are UUIDs (not guessable)
- SQL injection prevented by parameterized queries

## Testing

### Test Persistence
1. Start server
2. Create a game with 4 players
3. Play a few hands
4. Stop server (Ctrl+C)
5. Restart server
6. Players reconnect with same IDs
7. Game should resume from exact state

### Verify Data
```bash
sqlite3 data/tarokk_game.db "SELECT * FROM rooms;"
sqlite3 data/tarokk_game.db "SELECT * FROM players;"
sqlite3 data/tarokk_game.db "SELECT phase, trick_number FROM game_states;"
```
