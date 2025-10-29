# trix-hub

A data aggregation and rendering hub for [trix-server](https://github.com/ulfmagnetics/trix-server). Collects data from various sources, renders 64x32 bitmaps, and sends them to a MatrixPortal M4 for display on an RGB LED matrix.

## Architecture

- **trix-server** (MatrixPortal M4): HTTP server that receives and displays bitmaps
- **trix-hub** (Raspberry Pi 5): Data aggregation service that fetches data, renders bitmaps, and uploads to trix-server

## Hardware

- **Development**: Windows 11 PC with Docker Desktop + WSL2
- **Production**: Raspberry Pi 5 (ARM64/aarch64) at `rpi5-streamer.local` (192.168.1.82)
- **Display**: MatrixPortal M4 with 64x32 RGB LED panel

## Docker Workflow

This project uses Docker for consistent deployment across development and production environments.

### Build ARM64 Image (on Windows PC)

```bash
# Build the image (Docker Desktop will use ARM64 emulation)
docker-compose build

# Verify the image was created
docker images | grep trix-hub
```

### Export Image for Transfer

```bash
# Save the image to a compressed tarball
mkdir -p build
docker save trix-hub:latest | gzip > build/trix-hub.tar.gz

# Transfer to Raspberry Pi 5 (along with the production compose file)
scp build/trix-hub.tar.gz docker-compose.prod.yml rpi5-streamer.local:~/trix-hub/
```

### Load and Run on Raspberry Pi 5

```bash
# SSH into the Pi
ssh rpi5-streamer.local

# Load the image
docker load < trix-hub.tar.gz

# Run with the production compose file (no source code needed)
docker compose -f docker-compose.prod.yml up -d

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Stop the service
docker compose -f docker-compose.prod.yml down
```

**Note:** Use `docker-compose.prod.yml` for production deployment. The regular `docker-compose.yml` includes development volume mounts that require source files to be present.

### Configuration

Edit [docker-compose.prod.yml](docker-compose.prod.yml) (or [docker-compose.yml](docker-compose.yml) for development) to configure:
- `TRIX_SERVER_URL`: URL of your trix-server endpoint
- `MATRIX_WIDTH` / `MATRIX_HEIGHT`: Display dimensions (default: 64x32)
- `UPDATE_INTERVAL`: How often to refresh data (seconds)
- `TZ`: Timezone for time-based displays

### Troubleshooting

#### "not a directory" or "mount" errors

If you see an error like:
```
error mounting "/path/to/app.py" to rootfs: not a directory
```

**Cause:** The `docker-compose.yml` file tries to mount a local `app.py` file that doesn't exist.

**Solution:** Use the production compose file:
```bash
docker compose -f docker-compose.prod.yml up
```

Or comment out the `volumes:` section in `docker-compose.yml`.

### Development

For local development with live code reloading on your Windows PC:

```bash
# The app.py file is mounted as a volume in docker-compose.yml
# Edit app.py, then restart the container to see changes
docker-compose restart
```

**Note:** The development compose file requires source files to be present locally.

## Project Roadmap

- **Phase 1**: MatrixPortal Display Server ✓ COMPLETE
- **Phase 2**: Data Hub Skeleton ← CURRENT
  - Simple time display as proof-of-concept
  - Validate Docker workflow end-to-end
- **Phase 3**: Scheduling system (rotate between data sources)
- **Phase 4**: Web UI for configuration

## Current Status

This is a hello world validation setup. The current [app.py](app.py) prints system information and a heartbeat to verify ARM64 execution on the Raspberry Pi 5.