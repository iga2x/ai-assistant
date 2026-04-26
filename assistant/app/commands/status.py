import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from assistant.system.discovery import discover_system
from assistant.ai.detector import detect_providers
from assistant.tools.detector import detect_tools

console = Console()

@click.command()
def status():
    """Show the current status of the assistant and its environment."""
    sys_info = discover_system()
    providers = detect_providers()
    tools = detect_tools()

    # System Panel
    console.print(Panel(
        f"[bold cyan]OS:[/bold cyan] {sys_info.os_detailed}\n"
        f"[bold cyan]Shell:[/bold cyan] {sys_info.shell} ({sys_info.shell_path})\n"
        f"[bold cyan]Python:[/bold cyan] {sys_info.python_version}\n"
        f"[bold cyan]Admin:[/bold cyan] {'[green]Yes[/green]' if sys_info.is_admin else '[yellow]No[/yellow]'}\n"
        f"[bold cyan]Resources:[/bold cyan] CPU: {sys_info.cpu_count}, RAM: {sys_info.total_ram_gb}GB, Disk Free: {sys_info.disk_free_gb}GB\n"
        f"[bold cyan]Network:[/bold cyan] IP: {sys_info.local_ip}",
        title="[bold]System Overview[/bold]", expand=False
    ))

    # AI Providers Table
    ai_table = Table(title="AI Providers", box=None)
    ai_table.add_column("Provider", style="cyan")
    ai_table.add_column("Status", style="magenta")
    ai_table.add_column("Models", style="dim")
    for p in providers:
        status_str = "[green]Available[/green]" if p.available else "[red]Offline[/red]"
        models_str = ", ".join(p.models[:3]) + ("..." if len(p.models) > 3 else "")
        ai_table.add_row(p.name, status_str, models_str)
    console.print(ai_table)

    # Tools Summary
    installed_tools = [t for t in tools if t.installed]
    console.print(f"\n[bold]Tools Detected:[/bold] {len(installed_tools)} / {len(tools)} common tools found.")
    
    security_tools = [t for t in installed_tools if t.category in ["scanner", "recon"]]
    if security_tools:
        console.print(f"[bold green]✔[/bold green] Security tools ready: {', '.join(t.name for t in security_tools)}")
    
    missing = [t.name for t in tools if not t.installed and t.category in ["scanner", "recon"]]
    if missing:
        console.print(f"[bold yellow]![/bold yellow] Recommended missing: {', '.join(missing)}")

    console.print("\n[dim]Run 'assistant doctor' for full diagnostics.[/dim]")
