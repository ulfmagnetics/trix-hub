#!/usr/bin/env python3
"""
trix-hub Application

LED Matrix Data Aggregation Hub for Raspberry Pi 5.
Rotates through configured data providers, rendering bitmaps and posting to trix-server.
"""

import argparse
import signal
import sys
from datetime import datetime

from trixhub.config import get_config
from trixhub.schedulers import get_scheduler


# Global scheduler instance for signal handler
scheduler = None


def signal_handler(signum, frame):
    """Handle shutdown signals - exit immediately."""
    global scheduler

    print()
    print("=" * 70)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Shutdown requested with signum {signum}...")
    print("=" * 70)

    # Clear display on shutdown
    if scheduler and scheduler.client and not scheduler.debug:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Attempting to clear display...")
        scheduler.client.clear_display()

    # Exit immediately - don't wait for graceful shutdown
    sys.exit(0)


def main():
    """Main entry point."""
    global scheduler

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="trix-hub - LED Matrix Data Aggregation Hub",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python app.py              Run in normal mode (post bitmaps to matrix)
  python app.py --debug      Run in debug mode (print ASCII to console)
        """
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Debug mode: render ASCII to console instead of posting bitmaps"
    )
    args = parser.parse_args()

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Docker stop

    try:
        # Get config and create appropriate scheduler based on mode
        config = get_config()
        scheduler = get_scheduler(config, debug=args.debug)
        scheduler.run()

    except Exception as e:
        print(f"\n[ERROR] Fatal error: {e}", file=sys.stderr)
        sys.exit(1)

    finally:
        print()
        print("=" * 70)
        print("trix-hub stopped")
        print("=" * 70)


if __name__ == "__main__":
    main()
