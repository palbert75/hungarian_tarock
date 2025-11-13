# Docker Deployment Guide

This guide covers how to run the Hungarian Tarokk server using Docker for both development and production environments.

## Quick Start

### Development

```bash
cd server
docker-compose up --build
```

The server will be available at `http://localhost:8000`

### Production

```bash
cd server
docker-compose -f docker-compose.prod.yml up -d
```

The server will be available at:
- `http://localhost` (via nginx reverse proxy)
- `http://localhost:8000` (direct access)

### Using Pre-built Image

Instead of building locally, you can use the public Docker image:

```bash
# Pull and run the latest version
docker pull palbert75/hungarian-tarokk-server:latest
docker run -d -p 8000:8000 -v tarokk-data:/app/data palbert75/hungarian-tarokk-server:latest
```

**Docker Hub:** https://hub.docker.com/r/palbert75/hungarian-tarokk-server

## Files Overview

### Dockerfile

Multi-stage build configuration for optimal image size:
- **Builder stage**: Installs build dependencies and Python packages
- **Final stage**: Python 3.11 slim base image with runtime dependencies only
- **Non-root user**: Runs as `tarokk:1000` for security
- **Health check**: Automated endpoint monitoring at `/health`
- **Optimized caching**: Layers organized for maximum build cache efficiency

### docker-compose.yml

Development environment configuration:
- Named volume for database persistence (`tarokk-data`)
- Hot reload support (code mounting available)
- Network isolation
- Health checks
- Restart policy: `unless-stopped`

### docker-compose.prod.yml

Production environment configuration:
- **Resource limits**: 1 CPU, 512MB RAM (256MB reserved)
- **Nginx reverse proxy**: Handles SSL/TLS termination and load balancing
- **Automated backups**: Every 6 hours, 7-day retention
- **Log rotation**: 10MB max size, 3 files retained
- **Restart policy**: `always`
- **Health monitoring**: 30-second intervals

### .dockerignore

Optimizes build context by excluding:
- Python cache files and virtual environments
- Test files and documentation
- Git repository
- Logs and temporary files
- Database files (persisted in volumes)

### docker-publish.sh

Automated script for building and publishing Docker images to Docker Hub:
- Validates Docker is running and user is authenticated
- Builds the image with multi-arch support
- Runs automated tests (health check)
- Tags with version numbers (optional)
- Pushes to Docker Hub registry
- Provides detailed success/error feedback

**Usage:**
```bash
# Build and push with latest tag only
./docker-publish.sh

# Build and push with version tags
./docker-publish.sh 1.0.0
# Creates tags: latest, 1.0.0, v1.0.0
```

### DOCKER_HUB_OVERVIEW.md

Comprehensive documentation for the Docker Hub repository page. Copy this content to your Docker Hub repository's "Overview" tab for users who find your image on Docker Hub.

## Running the Server

### Development Mode

Start the server with logs visible:

```bash
docker-compose up
```

Start in detached mode (background):

```bash
docker-compose up -d
```

View logs:

```bash
docker-compose logs -f tarokk-server
```

Stop the server:

```bash
docker-compose down
```

### Production Mode

Start all services (server, nginx, backup):

```bash
docker-compose -f docker-compose.prod.yml up -d
```

View logs for specific service:

```bash
docker-compose -f docker-compose.prod.yml logs -f tarokk-server
docker-compose -f docker-compose.prod.yml logs -f nginx
docker-compose -f docker-compose.prod.yml logs -f backup
```

Stop all services:

```bash
docker-compose -f docker-compose.prod.yml down
```

## Configuration

### Environment Variables

Configure via environment variables or `.env` file:

```bash
# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=False
LOG_LEVEL=INFO

# CORS Configuration
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Database
DATABASE_PATH=data/tarokk_game.db

# Room Management (Production)
MAX_ROOMS=100
ROOM_TIMEOUT_MINUTES=60
CLEANUP_INACTIVE_DAYS=7
```

### Production Environment File

Create `.env` file in the server directory:

```bash
# Production settings
CORS_ORIGINS=https://yourdomain.com
MAX_ROOMS=100
ROOM_TIMEOUT_MINUTES=60
CLEANUP_INACTIVE_DAYS=7
```

Then start with:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

## Database Persistence

The database is persisted using Docker named volumes:

### View Volumes

```bash
docker volume ls
```

### Inspect Volume

```bash
docker volume inspect tarokk-data
```

### Backup Volume Data

```bash
# Using the automated backup service (recommended)
docker-compose -f docker-compose.prod.yml exec backup ls -lh /backups

# Manual backup
docker run --rm -v tarokk-data:/data -v $(pwd)/manual-backup:/backup \
  alpine tar czf /backup/tarokk-data-$(date +%Y%m%d).tar.gz -C /data .
```

### Restore Volume Data

```bash
# Stop the server
docker-compose -f docker-compose.prod.yml down

# Restore from tar archive
docker run --rm -v tarokk-data:/data -v $(pwd)/manual-backup:/backup \
  alpine sh -c "cd /data && tar xzf /backup/tarokk-data-YYYYMMDD.tar.gz"

# Restart the server
docker-compose -f docker-compose.prod.yml up -d
```

## Backup Management

The production setup includes an automated backup service.

### Backup Configuration

- **Frequency**: Every 6 hours (21600 seconds)
- **Retention**: 7 days
- **Location**: `./backups/` directory
- **Naming**: `tarokk_game_YYYYMMDD_HHMMSS.db`

### View Backups

```bash
ls -lh backups/
```

### Manual Backup Trigger

```bash
docker-compose -f docker-compose.prod.yml exec backup sh -c \
  "cp /data/tarokk_game.db /backups/tarokk_game_manual_$(date +%Y%m%d_%H%M%S).db"
```

### Restore from Backup

```bash
# 1. Stop the server
docker-compose -f docker-compose.prod.yml stop tarokk-server

# 2. Copy backup to volume
docker-compose -f docker-compose.prod.yml exec backup sh -c \
  "cp /backups/tarokk_game_YYYYMMDD_HHMMSS.db /data/tarokk_game.db"

# 3. Restart the server
docker-compose -f docker-compose.prod.yml start tarokk-server
```

### Customize Backup Schedule

Edit `docker-compose.prod.yml` and modify the backup service command:

```yaml
command: >
  -c "while true; do
    echo 'Creating backup...'
    cp /data/tarokk_game.db /backups/tarokk_game_$$(date +%Y%m%d_%H%M%S).db
    echo 'Cleaning old backups (keeping last 7 days)...'
    find /backups -name 'tarokk_game_*.db' -mtime +7 -delete
    echo 'Backup complete. Sleeping for 6 hours...'
    sleep 21600  # Change this value (in seconds)
  done"
```

## Nginx Configuration

### Basic Setup

Create `server/nginx/nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream tarokk_backend {
        server tarokk-server:8000;
    }

    server {
        listen 80;
        server_name yourdomain.com www.yourdomain.com;

        # Redirect to HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name yourdomain.com www.yourdomain.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        # Security headers
        add_header Strict-Transport-Security "max-age=31536000" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-Frame-Options "SAMEORIGIN" always;

        location / {
            proxy_pass http://tarokk_backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # WebSocket support for Socket.IO
        location /socket.io/ {
            proxy_pass http://tarokk_backend/socket.io/;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_cache_bypass $http_upgrade;
        }
    }
}
```

### SSL Certificate Setup

Place SSL certificates in `server/nginx/ssl/`:

```bash
mkdir -p server/nginx/ssl
# Copy your certificates
cp /path/to/cert.pem server/nginx/ssl/
cp /path/to/key.pem server/nginx/ssl/
```

### Disable Nginx (Development)

If you don't need the reverse proxy, comment out the nginx service in `docker-compose.prod.yml`:

```yaml
# nginx:
#   image: nginx:alpine
#   ...
```

## Health Checks

### Container Health

```bash
docker-compose ps
```

Healthy containers show `healthy` status.

### Manual Health Check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "healthy"}
```

### Health Check Configuration

Defined in Dockerfile and docker-compose files:
- **Interval**: 30 seconds
- **Timeout**: 10 seconds
- **Retries**: 3
- **Start period**: 5-10 seconds

## Resource Management

### View Resource Usage

```bash
docker stats tarokk-server-prod
```

### Production Resource Limits

Configured in `docker-compose.prod.yml`:
- **CPU Limit**: 1 core
- **CPU Reserved**: 0.5 cores
- **Memory Limit**: 512MB
- **Memory Reserved**: 256MB

### Adjust Limits

Edit `docker-compose.prod.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '2'        # Increase CPU limit
      memory: 1024M    # Increase memory limit
    reservations:
      cpus: '1'
      memory: 512M
```

## Troubleshooting

### Container Won't Start

Check logs:
```bash
docker-compose logs tarokk-server
```

Check container status:
```bash
docker-compose ps
```

### Database Issues

Access the database directly:
```bash
docker-compose exec tarokk-server sqlite3 data/tarokk_game.db
```

Verify database file exists:
```bash
docker-compose exec tarokk-server ls -lh data/
```

### Permission Issues

Ensure correct ownership:
```bash
docker-compose exec tarokk-server ls -la /app/data
```

Should show `tarokk:tarokk` ownership.

### Port Conflicts

If port 8000 is in use:
```bash
# Check what's using the port
lsof -i :8000

# Change port in docker-compose.yml
ports:
  - "8001:8000"  # Use 8001 instead
```

### Network Issues

Restart networking:
```bash
docker-compose down
docker network prune
docker-compose up -d
```

### Health Check Failing

Check if the application is responding:
```bash
docker-compose exec tarokk-server curl http://localhost:8000/health
```

View detailed health logs:
```bash
docker inspect tarokk-server | jq '.[0].State.Health'
```

### Out of Memory

If container is killed due to OOM:
```bash
# Check logs for OOM
docker-compose logs tarokk-server | grep -i "killed"

# Increase memory limit
# Edit docker-compose.prod.yml and increase memory limits
```

## Security Best Practices

1. **Non-root User**: Container runs as `tarokk:1000`
2. **Read-only Volumes**: Mount nginx config as read-only (`:ro`)
3. **Network Isolation**: Services communicate via internal network
4. **Resource Limits**: Prevents resource exhaustion
5. **Health Monitoring**: Automated restart on failures
6. **Log Rotation**: Prevents disk space issues
7. **SSL/TLS**: Use nginx with valid certificates
8. **CORS Configuration**: Restrict to your domain only
9. **Regular Backups**: Automated backup service included
10. **Keep Updated**: Regularly update base images

## Maintenance

### Update Application

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose -f docker-compose.prod.yml up -d --build
```

### Update Base Images

```bash
# Pull latest Python base image
docker-compose -f docker-compose.prod.yml pull

# Rebuild with new base
docker-compose -f docker-compose.prod.yml up -d --build
```

### Clean Up Old Images

```bash
# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune
```

### View Disk Usage

```bash
docker system df
```

## Monitoring

### View All Logs

```bash
docker-compose -f docker-compose.prod.yml logs -f
```

### View Specific Service Logs

```bash
docker-compose -f docker-compose.prod.yml logs -f tarokk-server
docker-compose -f docker-compose.prod.yml logs -f nginx
docker-compose -f docker-compose.prod.yml logs -f backup
```

### Log Files

Application logs are in JSON format (structured logging) and rotated automatically:
- **Max size**: 10MB per file
- **Max files**: 3 files kept
- **Driver**: json-file

### Export Logs

```bash
docker-compose -f docker-compose.prod.yml logs --no-color > tarokk-server.log
```

## Performance Optimization

### Multi-stage Build

The Dockerfile uses multi-stage builds to minimize image size:
- Builder stage: ~1GB (includes gcc and build tools)
- Final image: ~200MB (runtime only)

### Build Cache

Optimize build times by ordering Dockerfile layers:
1. Dependencies (rarely change) → cached
2. Application code (frequently changes) → rebuilt only when needed

### Volume Performance

For better I/O performance on macOS:
```yaml
volumes:
  tarokk-data:
    driver: local
    driver_opts:
      type: none
      device: /path/to/host/directory
      o: bind
```

## Production Checklist

Before deploying to production:

- [ ] Set `DEBUG=False`
- [ ] Configure proper `CORS_ORIGINS`
- [ ] Set up SSL certificates for nginx
- [ ] Configure resource limits appropriately
- [ ] Set up automated backups
- [ ] Enable log rotation
- [ ] Test health checks
- [ ] Verify database persistence
- [ ] Configure firewall rules
- [ ] Set up monitoring/alerting
- [ ] Document recovery procedures
- [ ] Test backup restoration
- [ ] Review security headers in nginx
- [ ] Update default passwords/secrets
- [ ] Configure rate limiting (if needed)

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [SQLite Backup Best Practices](https://www.sqlite.org/backup.html)
