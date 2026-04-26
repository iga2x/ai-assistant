import click
from rich.console import Console
from pathlib import Path
from assistant.utils.paths import CONFIG_FILE, DB_PATH, ensure_dirs
from assistant.config.manager import ConfigManager
from assistant.db.database import DatabaseManager

console = Console()

@click.command()
def doctor():
    """Run a diagnostic check on the environment."""
    console.print("Running Diagnostic Check...")
    init_success = True
    
    if Path(CONFIG_FILE).exists():
        console.print("[green]✔[/green] Config File: OK")
    else:
        console.print("[red]✘[/red] Config File: Missing")
        init_success = False

    if Path(DB_PATH).exists():
        console.print("[green]✔[/green] Database: OK")
    else:
        console.print("[red]✘[/red] Database: Missing")
        init_success = False

    if init_success:
        console.print("\n[bold green]AI Assistant is ready for action![/bold green]")
    else:
        console.print("\n[bold red]Assistant is not fully initialized. Run 'assistant init'.[/bold red]")
