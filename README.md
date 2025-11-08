# trix-hub

A data aggregation and rendering hub for [trix-server](https://github.com/ulfmagnetics/trix-server). Collects data from various sources, renders 64x32 bitmaps, and sends them to a MatrixPortal M4 for display on an RGB LED matrix.

## Architecture

- **trix-server** (MatrixPortal M4): HTTP server that receives and displays bitmaps
- **trix-hub** (Raspberry Pi 5): Data aggregation service that fetches data, renders bitmaps, and uploads to trix-server

### Provider/Renderer Architecture

trix-hub uses a clean separation between **data providers** (what to display) and **renderers** (how to display it):

```
┌─────────────────┐
│   Data Source   │ (API, calculation, etc.)
└────────┬────────┘
         │
┌────────▼────────┐
│  Data Provider  │ (fetches & structures data)
└────────┬────────┘
         │
         ├─────────────┬─────────────┬──────────────┐
         │             │             │              │
┌────────▼────────┐ ┌──▼──────┐ ┌───▼─────┐ ┌─────▼────────┐
│ Bitmap Renderer │ │  ASCII  │ │  HTML   │ │ Future/Test  │
│   (PIL Image)   │ │ Renderer│ │ Renderer│ │   Renderers  │
└────────┬────────┘ └──┬──────┘ └───┬─────┘ └──────────────┘
         │             │             │
         v             v             v
    Matrix Portal   Terminal    Web Browser
```

**Key Components:**

- **DisplayData**: Structured, renderer-agnostic data format
- **DataProvider**: Base class for fetching data (e.g., TimeProvider, WeatherProvider)
  - Includes built-in caching to avoid redundant API calls
  - Returns DisplayData objects
- **Renderer**: Base class for rendering DisplayData to specific formats
  - BitmapRenderer: Creates 64x32 PIL Images for LED matrix
  - ASCIIRenderer: Creates colored pixel-perfect terminal preview (64x16 using half-block technique)
  - HTMLRenderer: Future web UI support

**Benefits:**

- Single source of truth: Fetch data once, render many ways
- Easy testing: Use ASCII renderer during development
- Future-proof: Add new renderers without touching providers
- Cacheable: Data caching works across all renderers

### Example Usage

```python
from trixhub.providers import TimeProvider
from trixhub.renderers import BitmapRenderer, ASCIIRenderer
from trixhub.client import MatrixClient

# Create provider
provider = TimeProvider()

# Create renderers
bitmap_renderer = BitmapRenderer(64, 32)
ascii_renderer = ASCIIRenderer(64, 32)  # Renders as 64x16 colored terminal output

# Fetch data once
data = provider.get_data()

# Render to multiple formats
ascii_output = ascii_renderer.render(data)  # Colored pixel terminal preview
bitmap = bitmap_renderer.render(data)       # LED matrix bitmap

# Display in terminal
print(ascii_output)  # See exactly what will appear on LED matrix!

# Send to Matrix Portal
client = MatrixClient("http://trix-server.local/bitmap")
client.post_bitmap(bitmap)
```

See [demo.py](demo.py) for more examples.

## Hardware

- **Development**: Windows 11 PC with Docker Desktop + WSL2
- **Production**: Raspberry Pi 5 (ARM64/aarch64) at `rpi5-streamer.local` (192.168.1.82)
- **Display**: MatrixPortal M4 with 64x32 RGB LED panel

## Deployment

### Quick Deploy with NPM Scripts

The easiest way to deploy trix-hub is using the npm scripts:

```bash
# Quick deploy (build, package, and transfer to Pi)
npm run deploy

# Full deployment (includes loading and starting on Pi)
npm run deploy:full

# View logs from the running container
npm run logs

# Check container status
npm run status
```

### Available NPM Scripts

**Build & Package:**
- `npm run build` - Build ARM64 Docker image
- `npm run package` - Save image to trix-hub.tar.gz
- `npm run clean` - Remove local tar.gz file

**Deploy:**
- `npm run deploy` - Build, package, and transfer to Pi
- `npm run transfer` - Transfer files to Pi only

**Pi Management (via SSH):**
- `npm run deploy:load` - Load the image on Pi
- `npm run deploy:start` - Start the container on Pi
- `npm run deploy:stop` - Stop the container on Pi
- `npm run deploy:restart` - Restart the container on Pi
- `npm run deploy:full` - Complete end-to-end deployment

**Monitoring:**
- `npm run logs` - View container logs (follow mode)
- `npm run status` - Check container status

**Note:** All Pi deployment commands use `~/trix-hub/` as the deployment directory. Ensure this directory exists on your Pi (the scripts will create it automatically on first transfer).

## Manual Docker Workflow

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
docker save trix-hub:latest | gzip > trix-hub.tar.gz

# Transfer to Raspberry Pi 5 (along with the production compose file)
scp trix-hub.tar.gz docker-compose.prod.yml rpi5-streamer.local:~/trix-hub/
```

**Tip:** Use `npm run package` and `npm run transfer` instead for easier workflow.

### Load and Run on Raspberry Pi 5

```bash
# SSH into the Pi
ssh rpi5-streamer.local

# Load the image
cd ~/trix-hub
docker load < trix-hub.tar.gz

# Run with the production compose file (no source code needed)
docker compose -f docker-compose.prod.yml up -d

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Stop the service
docker compose -f docker-compose.prod.yml down
```

**Tip:** Use `npm run deploy:load` and `npm run deploy:start` to do this remotely from your PC.

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

For local development with live code reloading:

**Quick Iteration (No Rebuild):**
```bash
# Source files are mounted as volumes in docker-compose.yml
# Edit code, then run tests immediately - no rebuild needed!
npm run test:ascii

# Or run demo.py directly in container
docker compose run --rm trix-hub python demo.py ascii
```

**Volume Mounts:**
- `app.py` - Main application
- `demo.py` - Demo script
- `trixhub/` - Full package (providers, renderers, etc.)

Changes to these files take effect immediately without rebuilding the image.

**Before Deploying:**
```bash
# Validate with full production build
npm run test:rebuild
```

**Note:** The development compose file requires source files to be present locally.

## Testing & Development

### Running the Demo

The [demo.py](demo.py) script demonstrates the provider/renderer architecture:

```bash
# Run all demos
python demo.py

# Run specific demo
python demo.py ascii      # Colored ASCII pixel renderer (64x16 terminal output)
python demo.py bitmap     # Bitmap renderer (saves to file via stubbed client)
python demo.py caching    # Show caching behavior
python demo.py multiple   # Multiple renderers with same data
python demo.py live       # Live updates with cache expiration
```

**Using npm test scripts** (runs in Docker container):
```bash
npm test              # Run all demos in container
npm run test:ascii    # Quick colored ASCII preview
npm run test:bitmap   # Bitmap generation test
npm run test:rebuild  # Rebuild image then test
```

### Local Testing (No Hardware Required)

Test the library without the LED matrix using the colored ASCII renderer:

```python
from trixhub.providers import TimeProvider
from trixhub.renderers import ASCIIRenderer

provider = TimeProvider()
renderer = ASCIIRenderer(64, 32)

data = provider.get_data()
print(renderer.render(data))
```

The ASCII renderer uses the **half-block technique** (▄ character with ANSI color codes) to display a pixel-perfect 64×16 colored preview of your 64×32 bitmap in the terminal. Each terminal cell shows 2 vertical pixels using foreground and background colors, giving you an exact preview of what will appear on the LED matrix.

**Terminal Requirements:**
- 24-bit true color support recommended (most modern terminals)
- Automatically falls back to 256-color mode if true color unavailable
- Set `COLORTERM=truecolor` environment variable for best results

### Adding New Providers

1. Create a new file in `trixhub/providers/` (e.g., `weather_provider.py`)
2. Subclass `DataProvider`
3. Implement `fetch_data()` returning `DisplayData`
4. Optionally override `get_cache_duration()`
5. Add rendering support in `BitmapRenderer._render_weather()`
   - ASCIIRenderer automatically works by using BitmapRenderer internally

See [TimeProvider](trixhub/providers/time_provider.py) for a complete example.

## Project Roadmap

- **Phase 1**: MatrixPortal Display Server ✓ COMPLETE
- **Phase 2**: Data Hub Architecture ✓ COMPLETE
  - Provider/Renderer architecture implemented
  - TimeProvider working
  - BitmapRenderer and ASCIIRenderer functional
  - Local testing support
- **Phase 3**: Additional Providers ← NEXT
  - Weather provider
  - Calendar provider
  - Quote/message provider
- **Phase 4**: Scheduling system (rotate between data sources)
- **Phase 5**: Matrix Portal HTTP integration (replace stub client)
- **Phase 6**: Web UI for configuration

## Current Status

The provider/renderer architecture is complete and functional. The system includes:

- **TimeProvider**: Displays current time and date
- **BitmapRenderer**: Creates 64x32 bitmaps for LED matrix
- **ASCIIRenderer**: Creates 64×16 colored terminal output using half-block technique for pixel-perfect preview
- **MatrixClient**: Stubbed (saves to files, HTTP POST not yet implemented)

You can test locally with `npm run test:ascii` for instant colored preview, or build and deploy to the Pi with `npm run deploy:full`.