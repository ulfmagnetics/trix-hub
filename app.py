#!/usr/bin/env python3
"""
trix-hub Hello World
Validates Docker workflow for ARM64/aarch64 deployment
"""

import platform
import sys
import time
from datetime import datetime


def print_system_info():
    """Print system information to validate ARM64 execution"""
    print("=" * 60)
    print("trix-hub Docker Hello World")
    print("=" * 60)
    print(f"Python Version: {sys.version}")
    print(f"Platform: {platform.platform()}")
    print(f"Architecture: {platform.machine()}")
    print(f"Processor: {platform.processor()}")
    print(f"System: {platform.system()}")
    print("=" * 60)


def main():
    """Main hello world loop"""
    print_system_info()

    print("\nStarting trix-hub service...")
    print("Press Ctrl+C to stop\n")

    counter = 0
    try:
        while True:
            counter += 1
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] Heartbeat #{counter} - trix-hub is running!")
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n\nShutting down trix-hub service...")
        print("Goodbye!")


if __name__ == "__main__":
    main()
