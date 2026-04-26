import click
from rich.console import Console
from rich.table import Table
from assistant.ai.runtime import AIRuntime
from assistant.config.manager import ConfigManager

console = Console()

@click.group()
def ai():
    """Manage AI providers and models."""
    pass

@ai.command(name="scan")
def ai_scan():
    """Scan and list all available AI services."""
    _do_ai_refresh()

@ai.command(name="list")
def ai_list():
    """List all available AI providers and their models."""
    config = ConfigManager()
    runtime = AIRuntime(config)
    import asyncio
    asyncio.run(runtime.refresh())
    
    table = Table(title="AI Provider & Model Inventory")
    table.add_column("Provider", style="cyan")
    table.add_column("Type", style="dim")
    table.add_column("Status", style="magenta")
    table.add_column("Available Models", style="green")
    
    for p in runtime.providers:
        status_str = "[green]Available[/green]" if p.available else "[red]Offline[/red]"
        models_str = ", ".join(p.models) if p.models else "None"
        table.add_row(p.name, p.type, status_str, models_str)
    console.print(table)

@ai.command(name="active")
def ai_active():
    """Show the currently active AI routing state."""
    config = ConfigManager()
    runtime = AIRuntime(config)
    import asyncio
    asyncio.run(runtime.refresh())
    state = runtime.get_state()
    
    console.print("[bold cyan]Active AI Runtime State[/bold cyan]")
    console.print(f"Provider: [bold]{state.provider}[/bold]")
    console.print(f"Model:    [bold]{state.model if state.model else 'None'}[/bold]")
    console.print(f"Source:   [dim]{state.source}[/dim]")
    console.print(f"Status:   {'[green]Available[/green]' if state.available else '[red]Unavailable[/red]'}")

@ai.command(name="refresh")
def ai_refresh():
    """Manually refresh AI service detection."""
    _do_ai_refresh()

def _do_ai_refresh():
    config = ConfigManager()
    runtime = AIRuntime(config)
    import asyncio
    console.print("Scanning AI services...")
    asyncio.run(runtime.refresh())
    console.print("[green]✔[/green] AI runtime refreshed.")
    
    state = runtime.get_state()
    console.print("[bold cyan]New Active AI Runtime State[/bold cyan]")
    console.print(f"Provider: [bold]{state.provider}[/bold]")
    console.print(f"Model:    [bold]{state.model if state.model else 'None'}[/bold]")
    console.print(f"Source:   [dim]{state.source}[/dim]")

@ai.command(name="use")
@click.argument("provider")
@click.argument("model")
def ai_use(provider, model):
    """Set a specific provider and model as the default."""
    console.print(f"Switching to [bold]{provider}/{model}[/bold]...")
    # TODO: Implement config update logic here
    console.print("[yellow]Note: Manual 'use' override persistence coming soon.[/yellow]")

@ai.command(name="test")
def ai_test():
    """Send a test ping to the active AI model (Developer Verification)."""
    config = ConfigManager()
    runtime = AIRuntime(config)
    import asyncio
    asyncio.run(runtime.refresh())
    state = runtime.get_state()
    
    if not state.available:
        console.print("[red]✘ No active AI model available.[/red]")
        return
        
    console.print(f"Testing connectivity to [bold]{state.provider}/{state.model}[/bold]...")
    
    # Challenge prompt for verification
    challenge = "Return exactly: AI_RUNTIME_OK"
    messages = [
        {"role": "system", "content": "You are a verification service. Return exactly the text requested in JSON format."},
        {"role": "user", "content": challenge}
    ]
    
    from assistant.ai.router import AIRouter
    router = AIRouter(config)
    
    try:
        console.print("Sending challenge...")
        import time
        start_time = time.time()
        response_raw = asyncio.run(router.chat_completion(messages))
        elapsed = time.time() - start_time
        
        console.print(f"Response received in {elapsed:.2f}s")
        
        # Verify if it's the mock response or real
        is_mock = "offline mode" in response_raw.lower()
        
        if is_mock:
            console.print("[red]✘ FAILED: System returned a mock/fallback response.[/red]")
            console.print(f"Response: {response_raw}")
        elif "AI_RUNTIME_OK" in response_raw:
            console.print("[green]✔ SUCCESS: Real AI model verified.[/green]")
            console.print(f"Response: [dim]{response_raw}[/dim]")
        else:
            console.print("[yellow]! WARNING: Model responded but did not follow the challenge exactly.[/yellow]")
            console.print(f"Response: {response_raw}")
            
    except Exception as e:
        console.print(f"[red]✘ ERROR during verification: {str(e)}[/red]")
