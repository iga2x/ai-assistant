import click
from rich.console import Console
from rich.table import Table
from assistant.tools.detector import detect_tools

console = Console()

@click.group()
def tools():
    """Manage security and terminal tools."""
    pass

@tools.command(name="scan")
def tools_scan():
    """Detailed scan of all common tools."""
    _do_tools_list()

@tools.command(name="list")
def tools_list():
    """List available security and terminal tools."""
    _do_tools_list()

def _do_tools_list():
    tools = detect_tools()
    table = Table(title="Tool Detection Results")
    table.add_column("Tool", style="cyan")
    table.add_column("Status", style="magenta")
    table.add_column("Version", style="dim")
    table.add_column("Category", style="yellow")
    table.add_column("Risk", style="red")
    
    for t in tools:
        status_str = "[green]Installed[/green]" if t.installed else "[red]Missing[/red]"
        table.add_row(t.name, status_str, t.version, t.category, t.risk_level)
    console.print(table)
