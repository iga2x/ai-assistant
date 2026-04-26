import click
from rich.console import Console
from rich.table import Table
from assistant.system.discovery import discover_system

console = Console()

@click.group()
def system():
    """System information and management."""
    pass

@system.command(name="info")
def system_info():
    """Show detailed system information."""
    info = discover_system()
    table = Table(title="System Information")
    table.add_column("Attribute", style="cyan")
    table.add_column("Value", style="magenta")
    
    table.add_row("Hostname", info.hostname)
    table.add_row("Username", info.username)
    table.add_row("Architecture", info.architecture)
    table.add_row("CPU Count", str(info.cpu_count))
    table.add_row("Total RAM (GB)", f"{info.total_ram_gb:.2f}")
    table.add_row("Disk Free (GB)", f"{info.disk_free_gb:.2f}")
    table.add_row("Python", info.python_version)
    
    console.print(table)
