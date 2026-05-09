from assistant.app.cli import cli
from assistant.version import get_version


def main():
    """Entry point for the AI Assistant application."""
    version = get_version()
    print(f"Starting AI Assistant v{version}...")
    cli()

if __name__ == "__main__":
    main()
