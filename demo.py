#!/usr/bin/env python3
"""
trix-hub Demo Script

Demonstrates the DataProvider/Renderer architecture with TimeProvider.
Shows how to use both ASCII (terminal testing) and Bitmap (Matrix Portal) renderers.
"""

import sys
import time
from trixhub.providers import TimeProvider, WeatherProvider
from trixhub.renderers import BitmapRenderer, ASCIIRenderer
from trixhub.client import MatrixClient


def demo_ascii_renderer():
    """
    Demo ASCII renderer for terminal output.

    Useful for testing provider data without hardware.
    """
    print("=" * 64)
    print("ASCII Renderer Demo")
    print("=" * 64)
    print()

    # Create provider and renderer
    provider = TimeProvider()
    renderer = ASCIIRenderer(width=64, height=32)

    # Get data and render
    data = provider.get_data()
    ascii_output = renderer.render(data)

    # Display
    print(ascii_output)
    print()

    # Show data structure
    print("DisplayData structure:")
    print(f"  timestamp: {data.timestamp}")
    print(f"  content type: {data.content.get('type')}")
    print(f"  content keys: {list(data.content.keys())}")
    print(f"  metadata: {data.metadata}")
    print()


def demo_bitmap_renderer():
    """
    Demo bitmap renderer for LED matrix.

    Creates a bitmap and saves it to file (via stubbed Matrix client).
    """
    print("=" * 64)
    print("Bitmap Renderer Demo")
    print("=" * 64)
    print()

    # Create provider and renderer
    provider = TimeProvider()
    renderer = BitmapRenderer(width=64, height=32)

    # Get data and render
    data = provider.get_data()
    bitmap = renderer.render(data)

    # Show bitmap info
    print(f"Created bitmap: {bitmap.size} pixels, mode: {bitmap.mode}")
    print()

    # Send to Matrix Portal (stubbed - saves to file)
    client = MatrixClient(
        server_url="http://trix-server.local/bitmap",
        width=64,
        height=32
    )

    success = client.post_bitmap(bitmap)
    if success:
        print("✓ Bitmap saved successfully")
    else:
        print("✗ Failed to save bitmap")
    print()


def demo_caching():
    """
    Demo caching behavior.

    Shows how provider caching avoids redundant data fetches.
    """
    print("=" * 64)
    print("Caching Demo")
    print("=" * 64)
    print()

    provider = TimeProvider()

    print(f"Cache duration: {provider.get_cache_duration()}")
    print()

    # First fetch
    print("First fetch:")
    data1 = provider.get_data()
    print(f"  Timestamp: {data1.timestamp}")
    print(f"  Time: {data1.content['time_12h']}")
    print()

    # Immediate second fetch (should use cache)
    print("Second fetch (should use cache):")
    data2 = provider.get_data()
    print(f"  Timestamp: {data2.timestamp}")
    print(f"  Time: {data2.content['time_12h']}")
    print(f"  Same object? {data1 is data2}")
    print()

    # Force refresh
    print("Force refresh:")
    data3 = provider.get_data(force_refresh=True)
    print(f"  Timestamp: {data3.timestamp}")
    print(f"  Time: {data3.content['time_12h']}")
    print(f"  Same object? {data1 is data3}")
    print()


def demo_multiple_renderers():
    """
    Demo using multiple renderers with same data.

    Shows how one data fetch can produce multiple output formats.
    """
    print("=" * 64)
    print("Multiple Renderers Demo")
    print("=" * 64)
    print()

    # Create provider and multiple renderers
    provider = TimeProvider()
    ascii_renderer = ASCIIRenderer(64, 32)
    bitmap_renderer = BitmapRenderer(64, 32)

    # Fetch data once
    print("Fetching data once...")
    data = provider.get_data()
    print()

    # Render to multiple formats
    print("Rendering to ASCII:")
    ascii_output = ascii_renderer.render(data)
    print(ascii_output)
    print()

    print("Rendering to Bitmap:")
    bitmap = bitmap_renderer.render(data)
    print(f"  Created {bitmap.size} bitmap")
    print()

    # Save bitmap
    client = MatrixClient("http://trix-server.local/bitmap")
    client.post_bitmap(bitmap)
    print()


def demo_live_updates():
    """
    Demo live updates with cache expiration.

    Shows how data refreshes automatically after cache expires.
    """
    print("=" * 64)
    print("Live Updates Demo")
    print("=" * 64)
    print()

    provider = TimeProvider()
    renderer = ASCIIRenderer(64, 32)

    print("Showing 3 updates (watch time change)...")
    print("Press Ctrl+C to stop")
    print()

    try:
        for i in range(3):
            # Get data and render
            data = provider.get_data()
            output = renderer.render(data)

            # Display with header
            print(f"\n--- Update #{i+1} ---")
            print(output)

            if i < 2:
                # Wait for cache to expire
                print("\nWaiting for cache to expire...")
                time.sleep(31)  # Cache is 30 seconds

    except KeyboardInterrupt:
        print("\n\nStopped by user")


def demo_weather():
    """
    Demo weather provider with ASCII and bitmap renderers.

    Shows current weather and forecast using Open-Meteo API.
    """
    print("=" * 64)
    print("Weather Provider Demo")
    print("=" * 64)
    print()

    # Create provider and renderers
    provider = WeatherProvider()
    ascii_renderer = ASCIIRenderer(width=64, height=32)
    bitmap_renderer = BitmapRenderer(width=64, height=32)

    # Get data
    print("Fetching weather data...")
    data = provider.get_data()
    print()

    # Show data structure
    if data.content.get('error'):
        print(f"Error: {data.content.get('error_message')}")
        print()
    else:
        print("Weather data received:")
        print(f"  Location: {data.content.get('location')}")

        current = data.content.get('current', {})
        forecast1 = data.content.get('forecast1', {})
        forecast2 = data.content.get('forecast2', {})

        current_temp = current.get('temperature')
        current_condition = current.get('condition')
        current_windspeed = current.get('windspeed')
        current_units = current.get('units', 'fahrenheit')

        forecast1_temp = forecast1.get('temperature')
        forecast1_condition = forecast1.get('condition')
        forecast1_hours = forecast1.get('hours_ahead', 3)

        forecast2_temp = forecast2.get('temperature')
        forecast2_condition = forecast2.get('condition')
        forecast2_hours = forecast2.get('hours_ahead', 6)

        unit_symbol = '°F' if current_units == 'fahrenheit' else '°C'

        print(f"  Current: {current_temp}{unit_symbol} - {current_condition} - {current_windspeed}mph")
        print(f"  Forecast (+{forecast1_hours}h): {forecast1_temp}{unit_symbol} - {forecast1_condition}")
        print(f"  Forecast (+{forecast2_hours}h): {forecast2_temp}{unit_symbol} - {forecast2_condition}")
        print()

    # Render to ASCII
    print("ASCII Rendering:")
    ascii_output = ascii_renderer.render(data)
    print(ascii_output)
    print()

    # Render to bitmap
    print("Bitmap Rendering:")
    bitmap = bitmap_renderer.render(data)
    print(f"  Created {bitmap.size} bitmap")

    # Save bitmap
    client = MatrixClient("http://trix-server.local/bitmap")
    success = client.post_bitmap(bitmap)
    if success:
        print("  ✓ Bitmap saved successfully")
    else:
        print("  ✗ Failed to save bitmap")
    print()


def main():
    """Run all demos"""

    if len(sys.argv) > 1:
        demo_name = sys.argv[1]

        demos = {
            "ascii": demo_ascii_renderer,
            "bitmap": demo_bitmap_renderer,
            "caching": demo_caching,
            "multiple": demo_multiple_renderers,
            "live": demo_live_updates,
            "weather": demo_weather,
        }

        if demo_name in demos:
            demos[demo_name]()
        else:
            print(f"Unknown demo: {demo_name}")
            print(f"Available demos: {', '.join(demos.keys())}")
            sys.exit(1)
    else:
        # Run all demos
        demo_ascii_renderer()
        demo_bitmap_renderer()
        demo_caching()
        demo_multiple_renderers()

        print("\n" + "=" * 64)
        print("All demos completed!")
        print("=" * 64)
        print()
        print("To run individual demos:")
        print("  python demo.py ascii")
        print("  python demo.py bitmap")
        print("  python demo.py caching")
        print("  python demo.py multiple")
        print("  python demo.py live")
        print("  python demo.py weather")
        print()


if __name__ == "__main__":
    main()
