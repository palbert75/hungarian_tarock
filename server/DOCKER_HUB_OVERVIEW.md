# Hungarian Tarokk Server

A production-ready WebSocket server for the Hungarian Tarokk card game, built with FastAPI, Socket.IO, and SQLite persistence.

## Quick Start

```bash
docker run -d \
  --name tarokk-server \
  -p 8000:8000 \
  -v tarokk-data:/app/data \
  palbert75/hungarian-tarokk-server:latest
```

Visit `http://localhost:8000` to verify the server is running.

## Features

- **Real-time Multiplayer** - WebSocket-based gameplay via Socket.IO
- **Game State Persistence** - SQLite database with automatic save/restore
- **Player Reconnection** - Resume games after disconnection
- **Chat System** - In-game chat with history
- **Announcements** - Game announcements tracking (Trull, Four Kings, etc.)
- **Health Monitoring** - Built-in health check endpoint
- **Structured Logging** - JSON-formatted logs for easy parsing
- **Security** - Runs as non-root user, CORS protection
- **Resource Limits** - Optimized for production deployment

## Full Example with Configuration

```bash
docker run -d \
  --name tarokk-server \
  -p 8000:8000 \
  -v tarokk-data:/app/data \
  -e CORS_ORIGINS="https://yourdomain.com" \
  -e LOG_LEVEL=INFO \
  -e MAX_ROOMS=100 \
  -e ROOM_TIMEOUT_MINUTES=60 \
  --restart unless-stopped \
  palbert75/hungarian-tarokk-server:latest
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |
| `DEBUG` | `False` | Debug mode (set to `True` for development) |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `CORS_ORIGINS` | `*` | Allowed CORS origins (comma-separated) |
| `DATABASE_PATH` | `data/tarokk_game.db` | SQLite database path |
| `MAX_ROOMS` | `100` | Maximum concurrent game rooms |
| `ROOM_TIMEOUT_MINUTES` | `60` | Inactive room timeout |
| `CLEANUP_INACTIVE_DAYS` | `7` | Days before cleaning inactive rooms |

## Volumes

### `/app/data`
Persists the SQLite database containing:
- Game states
- Player data
- Chat history
- Announcements
- Trick history

**Example:**
```bash
# Named volume (recommended)
docker run -v tarokk-data:/app/data palbert75/hungarian-tarokk-server:latest

# Bind mount
docker run -v /path/on/host:/app/data palbert75/hungarian-tarokk-server:latest
```

### `/app/backups` (optional)
Mount for database backups:
```bash
docker run -v ./backups:/app/backups palbert75/hungarian-tarokk-server:latest
```

## Exposed Ports

- **8000** - Main HTTP/WebSocket server
  - HTTP API: `http://localhost:8000`
  - Socket.IO: `ws://localhost:8000/socket.io/`
  - Health check: `http://localhost:8000/health`

## Health Check

Built-in Docker health check monitors the `/health` endpoint:
- **Interval:** 30 seconds
- **Timeout:** 10 seconds
- **Retries:** 3
- **Start period:** 5 seconds

Check container health:
```bash
docker ps
# Look for "healthy" status

docker inspect tarokk-server | grep -A 5 Health
```

## Docker Compose

### Development
```yaml
version: '3.8'

services:
  tarokk-server:
    image: palbert75/hungarian-tarokk-server:latest
    container_name: tarokk-server
    ports:
      - "8000:8000"
    environment:
      - DEBUG=False
      - CORS_ORIGINS=*
    volumes:
      - tarokk-data:/app/data
    restart: unless-stopped

volumes:
  tarokk-data:
```

### Production with Nginx
```yaml
version: '3.8'

services:
  tarokk-server:
    image: palbert75/hungarian-tarokk-server:latest
    container_name: tarokk-server
    environment:
      - DEBUG=False
      - LOG_LEVEL=INFO
      - CORS_ORIGINS=https://yourdomain.com
      - MAX_ROOMS=100
    volumes:
      - tarokk-data:/app/data
    restart: always
    networks:
      - tarokk-network

  nginx:
    image: nginx:alpine
    container_name: tarokk-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - tarokk-server
    restart: always
    networks:
      - tarokk-network

volumes:
  tarokk-data:

networks:
  tarokk-network:
    driver: bridge
```

## API Endpoints

### HTTP Endpoints

- `GET /` - Server info and version
- `GET /health` - Health check (returns `{"status": "healthy"}`)

### WebSocket Events

**Client → Server:**
- `create_room` - Create new game room
- `join_room` - Join existing room
- `start_game` - Start the game
- `place_bid` - Place a bid
- `select_game_mode` - Choose game mode
- `exchange_talon` - Exchange cards with talon
- `discard_cards` - Discard cards
- `play_card` - Play a card
- `send_chat_message` - Send chat message

**Server → Client:**
- `room_created` - Room creation confirmation
- `player_joined` - Player joined notification
- `game_started` - Game start notification
- `game_state_update` - Full game state
- `trick_complete` - Trick winner notification
- `chat_message` - Chat message broadcast
- `error` - Error notification

## Logging

Structured JSON logs to stdout:
```json
{
  "event": "player_joined",
  "timestamp": "2025-01-13T10:30:45.123Z",
  "level": "info",
  "room_id": "ABC123",
  "player_name": "Player 1"
}
```

View logs:
```bash
docker logs -f tarokk-server
```

## Database Management

### Backup Database
```bash
# Copy database from container
docker cp tarokk-server:/app/data/tarokk_game.db ./backup_$(date +%Y%m%d).db

# Or use mounted volume
docker run --rm \
  -v tarokk-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/tarokk-data-backup.tar.gz -C /data .
```

### Restore Database
```bash
# Stop the server
docker stop tarokk-server

# Copy database to container
docker cp ./backup.db tarokk-server:/app/data/tarokk_game.db

# Or restore from tar
docker run --rm \
  -v tarokk-data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/tarokk-data-backup.tar.gz -C /data

# Restart the server
docker start tarokk-server
```

## Resource Requirements

**Minimum:**
- CPU: 0.5 cores
- Memory: 256MB
- Disk: 100MB + database size

**Recommended:**
- CPU: 1 core
- Memory: 512MB
- Disk: 1GB

Set resource limits:
```bash
docker run -d \
  --cpus="1" \
  --memory="512m" \
  -p 8000:8000 \
  palbert75/hungarian-tarokk-server:latest
```

## Troubleshooting

### Container won't start
```bash
# Check logs
docker logs tarokk-server

# Verify image
docker inspect palbert75/hungarian-tarokk-server:latest
```

### Database permission errors
```bash
# Fix volume permissions
docker run --rm \
  -v tarokk-data:/app/data \
  alpine chown -R 1000:1000 /app/data
```

### Health check failing
```bash
# Test health endpoint
docker exec tarokk-server curl http://localhost:8000/health

# Check if server is listening
docker exec tarokk-server netstat -tlnp
```

### Memory issues
```bash
# Check memory usage
docker stats tarokk-server

# Increase memory limit
docker update --memory="1g" tarokk-server
```

## Security Considerations

- Runs as non-root user (`tarokk:1000`)
- CORS protection (configure `CORS_ORIGINS`)
- No exposed secrets or credentials
- Minimal base image (Python 3.11 slim)
- Health monitoring enabled
- Resource limits recommended

**Production checklist:**
- [ ] Set proper `CORS_ORIGINS`
- [ ] Configure SSL/TLS (use nginx reverse proxy)
- [ ] Set resource limits
- [ ] Enable automatic restarts
- [ ] Configure log rotation
- [ ] Set up automated backups
- [ ] Monitor health checks
- [ ] Use secrets management for sensitive data

## Image Details

- **Base Image:** `python:3.11-slim`
- **Size:** ~200MB (multi-stage build)
- **Architecture:** linux/amd64
- **User:** tarokk (UID 1000)
- **Working Directory:** `/app`
- **Entrypoint:** `python -m main`

## Links

- **Source Code:** https://github.com/palbert75/tarokk (update with your repo)
- **Documentation:** See Docker.md in the repository
- **Issues:** Report bugs on GitHub

## Tags

- `latest` - Latest stable version
- `v1.0.0` - Specific version (coming soon)

## License

[Your license here]

## Support

For questions and support, please open an issue on GitHub.

---

**Note:** This is a game server. Make sure to deploy with appropriate security measures for production use.
