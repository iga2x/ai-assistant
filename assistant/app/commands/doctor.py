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
    console.print("[bold cyan]Running Diagnostic Check...[/bold cyan]\n")
    init_success = True
    
    # 1. File checks
    console.print("[bold]System Status:[/bold]")
    if Path(CONFIG_FILE).exists():
        console.print("  [green]✔[/green] Config File: OK")
    else:
        console.print("  [red]✘[/red] Config File: Missing")
        init_success = False

    if Path(DB_PATH).exists():
        console.print("  [green]✔[/green] Database: OK")
    else:
        console.print("  [red]✘[/red] Database: Missing")
        init_success = False

    # 2. Dependency checks
    console.print("\n[bold]Dependency Status:[/bold]")
    dependencies = {
        "schedule": "Required for automatic data retention",
        "psutil": "Required for system monitoring",
        "rich": "Required for UI rendering",
        "click": "Required for CLI commands",
        "pydantic": "Required for data validation",
        "sqlalchemy": "Required for database operations"
    }

    import importlib.util
    for mod, desc in dependencies.items():
        if importlib.util.find_spec(mod):
            console.print(f"  [green]✔[/green] {mod}: OK")
        else:
            console.print(f"  [red]✘[/red] {mod}: Missing ({desc})")
            init_success = False

    if init_success:
        console.print("\n[bold green]AI Assistant is ready for action![/bold green]")
    else:
        console.print("\n[bold red]Assistant is not fully initialized. Check the errors above.[/bold red]")
        console.print("Try running: [yellow]pip install -e .[/yellow]")

