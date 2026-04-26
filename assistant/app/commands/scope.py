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
    sm.add_to_scope(target)
    console.print(f"Added {target} to scope.")
