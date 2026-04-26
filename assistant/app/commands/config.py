import click
from rich.console import Console
from assistant.config.manager import ConfigManager

console = Console()

@click.group()
def config():
    """Manage configuration settings."""
    pass

@config.command(name="get")
@click.argument("key")
def config_get(key):
    """Get a configuration value."""
    mgr = ConfigManager()
    data = mgr.config.model_dump()
    parts = key.split(".")
    val = data
    for p in parts:
        if isinstance(val, dict):
            val = val.get(p)
        else:
            val = None
            break
    console.print(f"{key}: {val}")

@config.command(name="set")
@click.argument("key")
@click.argument("value")
def config_set(key, value):
    """Set a configuration value."""
    mgr = ConfigManager()
    parts = key.split(".")
    if len(parts) == 2:
        section, k = parts
        if hasattr(mgr.config, section):
            subsec = getattr(mgr.config, section)
            if hasattr(subsec, k):
                if value.lower() in ["true", "false"]:
                    value = value.lower() == "true"
                setattr(subsec, k, value)
                mgr.save_config()
                console.print(f"[green]✔[/green] {key} set to {value}")
            else:
                console.print(f"[red]✘[/red] Key {k} not found in {section}")
        else:
            console.print(f"[red]✘[/red] Section {section} not found")
    else:
        console.print("[yellow]Only 'section.key' format is currently supported for setting.[/yellow]")

@config.command(name="reset")
def config_reset():
    """Reset configuration to defaults."""
    if click.confirm("Are you sure you want to reset the configuration?"):
        mgr = ConfigManager()
        mgr.reset_config()
        console.print("[green]✔[/green] Configuration reset to defaults.")
