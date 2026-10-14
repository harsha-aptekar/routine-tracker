"""Entry point: python3 -m routine_tracker [--background]."""
import argparse
import sys

from .ui.app import TrackerApp


def main() -> int:
    parser = argparse.ArgumentParser(description="Daily routine tracker")
    parser.add_argument("--background", action="store_true", help="start without opening the window (reminders only)")
    return TrackerApp(parser.parse_args().background).run([sys.argv[0]])


if __name__ == "__main__":
    sys.exit(main())
