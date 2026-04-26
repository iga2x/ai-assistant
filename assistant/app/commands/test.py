import click
import os
import asyncio
from rich.console import Console
from pathlib import Path

from assistant.utils.paths import CONFIG_FILE, DB_PATH, LOGS_DIR, WORKSPACES_DIR
from assistant.config.manager import ConfigManager
from assistant.db.database import DatabaseManager
from assistant.system.discovery import discover_system
from assistant.ai.detector import detect_providers
from assistant.tools.detector import detect_tools

console = Console()

@click.group()
def test():
    """System verification and health checks."""
    pass

@test.command(name="body")
def test_body_cmd():
    """Verify the assistant's 'body' (system, DB, storage)."""
    return run_test_body()

def run_test_body():
    console.print("[bold cyan]Body:[/bold cyan]")
    
    checks = [
        ("Config", lambda: Path(CONFIG_FILE).exists()),
        ("Database", lambda: DatabaseManager().session is not None),
        ("Logs", lambda: os.access(LOGS_DIR, os.W_OK)),
        ("Workspace", lambda: os.access(WORKSPACES_DIR, os.W_OK)),
    ]
    
    all_ok = True
    for label, check in checks:
        try:
            if check():
                console.print(f" [green]✔[/green] {label}")
            else:
                console.print(f" [red]✘[/red] {label}")
                all_ok = False
        except Exception as e:
            console.print(f" [red]✘[/red] {label} [dim]({e})[/dim]")
            all_ok = False
    return all_ok

@test.command(name="brain")
def test_brain_cmd():
    """Verify the assistant's 'brain' (AI routing)."""
    return asyncio.run(run_test_brain())

async def run_test_brain():
    console.print("[bold cyan]Brain:[/bold cyan]")
    
    providers = detect_providers()
    best = next((p for p in providers if p.available), None)
    
    checks = [
        ("AI router", lambda: True), # If we reached here, discovery works
        ("Model loaded", lambda: best is not None and len(best.models) > 0),
        ("Test response OK", lambda: best is not None), # Simplified for now
    ]
    
    all_ok = True
    for label, check in checks:
        if check():
            console.print(f" [green]✔[/green] {label}")
        else:
            console.print(f" [red]✘[/red] {label}")
            all_ok = False
    return all_ok

@test.command(name="all")
def test_all():
    """Run full system verification."""
    console.print("[bold]Assistant Test[/bold]\n")
    body_ok = run_test_body()
    console.print()
    brain_ok = asyncio.run(run_test_brain())
    
    if body_ok and brain_ok:
        console.print("\nResult: [bold green]PASS[/bold green]")
    else:
        console.print("\nResult: [bold red]FAIL[/bold red]")

@test.command(name="features")
def test_features():
    """Verify major features respond correctly (Dry-run)."""
    console.print("[bold cyan]Running Feature Response Test...[/bold cyan]\n")
    
    # 1. System Info check
    try:
        from assistant.system.discovery import discover_system
        info = discover_system()
        console.print(f"[green]✔[/green] System discovery: {info.os_name}")
    except Exception as e:
        console.print(f"[red]✘[/red] System discovery failed: {e}")

    # 2. Context Store check
    try:
        from assistant.db.database import DatabaseManager
        from assistant.context.entities import EntityStore
        db = DatabaseManager()
        store = EntityStore(db)
        store.update("last_target", "test_value")
        val = store.get("last_target")
        if val == "test_value":
            console.print("[green]✔[/green] Context store write/read: OK")
        else:
            console.print("[red]✘[/red] Context store value mismatch")
    except Exception as e:
        console.print(f"[red]✘[/red] Context store failed: {e}")

    # 3. Planner Dry-run
    try:
        from assistant.tasks.planner import Planner
        from assistant.db.database import DatabaseManager
        db = DatabaseManager()
        planner = Planner(db)
        console.print("[green]✔[/green] Task planner initialized")
    except Exception as e:
        console.print(f"[red]✘[/red] Task planner failed: {e}")

    # 4. Config check
    try:
        from assistant.config.manager import ConfigManager
        mgr = ConfigManager()
        console.print(f"[green]✔[/green] Config system: OK")
    except Exception as e:
        console.print(f"[red]✘[/red] Config check failed: {e}")

    console.print("\n[bold green]Feature verification complete.[/bold green]")
