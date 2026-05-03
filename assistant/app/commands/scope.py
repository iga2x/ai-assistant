import click
from rich.console import Console
from assistant.db.database import DatabaseManager
from assistant.safety.scope import ScopeManager

console = Console()

@click.group()
def scope():
    """Manage engagement scope."""
    pass

@scope.command(name="add")
@click.argument("target")
def scope_add(target):
    """Add a target to the whitelist."""
    db = DatabaseManager()
    sm = ScopeManager(db)
    sm.add_scope(target)
    console.print(f"[green]✔[/green] Added {target} to scope.")

@scope.command(name="import")
@click.argument("file_path", type=click.Path(exists=True))
def scope_import(file_path):
    """Import targets from a file."""
    db = DatabaseManager()
    sm = ScopeManager(db)
    
    count = 0
    with open(file_path, "r") as f:
        for line in f:
            target = line.strip()
            if target and not target.startswith("#"):
                sm.add_scope(target)
                count += 1
    
    console.print(f"[green]✔[/green] Successfully imported {count} targets into scope.")

@scope.command(name="list")
def scope_list():
    """List all targets in scope."""
    db = DatabaseManager()
    sm = ScopeManager(db)
    items = sm.get_all()
    
    if not items:
        console.print("[yellow]Scope is empty.[/yellow]")
        return
        
    from rich.table import Table
    table = Table(title="Authorized Scope")
    table.add_column("Target", style="cyan")
    table.add_column("Type", style="magenta")
    
    for item in items:
        table.add_row(item.target, item.target_type)
    console.print(table)

