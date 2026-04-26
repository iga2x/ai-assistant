import click
from rich.console import Console
from rich.table import Table
from assistant.workspace.manager import WorkspaceManager

console = Console()

@click.group()
def workspace():
    """Manage target workspaces."""
    pass

@workspace.command(name="list")
def workspace_list():
    """List all available workspaces."""
    wm = WorkspaceManager()
    ws = wm.list_workspaces()
    table = Table(title="Workspaces")
    table.add_column("Target")
    for w in ws:
        table.add_row(w)
    console.print(table)
