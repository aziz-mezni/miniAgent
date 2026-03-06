"""Entry point for Buddy — python -m buddy"""

from buddy.app import BuddyApp


def main() -> None:
    app = BuddyApp()
    app.run()


if __name__ == "__main__":
    main()
