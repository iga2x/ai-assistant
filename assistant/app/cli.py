import click
from assistant.version import __version__
from rich.console import Console

from assistant.utils.paths import ensure_dirs
from assistant.utils.logger import setup_logger

console = Console()

@click.group(invoke_without_command=True)
@click.option("--version", "-v", is_flag=True, help="Show version and exit.")
@click.pass_context
def cli(ctx, version):
    """
    AI Assistant: A personal terminal AI for PC tasks, coding, and security.
    """
    # Load environment variables from .env if present
    from dotenv import load_dotenv
    load_dotenv()
    
    # Ensure environment is ready
    ensure_dirs()
    setup_logger()

    if version:
        console.print(f"AI Assistant [bold cyan]v{__version__}[/bold cyan]")
        return
    
    if ctx.invoked_subcommand is None:
        from assistant.app.terminal.repl import run_repl
        run_repl()

# Import and register subcommands
from assistant.app.commands.status import status
from assistant.app.commands.doctor import doctor
from assistant.app.commands.test import test
from assistant.app.commands.ai import ai
from assistant.app.commands.tools import tools
from assistant.app.commands.config import config
from assistant.app.commands.system import system
from assistant.app.commands.workspace import workspace
from assistant.app.commands.scope import scope
from assistant.app.commands.report import report
from assistant.app.commands.setup import setup

cli.add_command(status)
cli.add_command(doctor)
cli.add_command(test)
cli.add_command(ai)
cli.add_command(tools)
cli.add_command(config)
cli.add_command(system)
cli.add_command(workspace)
cli.add_command(scope)
cli.add_command(report)
cli.add_command(setup)

@cli.command()
def chat():
    """Start an interactive chat session."""
    from assistant.app.terminal.repl import run_repl
    run_repl()

if __name__ == "__main__":
    cli()
