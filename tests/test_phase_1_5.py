import pytest
from click.testing import CliRunner
from assistant.app.cli import cli
from assistant.app.terminal.repl import InteractiveREPL, run_repl
import asyncio

def test_cli_default_starts_repl(monkeypatch):
    """Test that running 'assistant' without arguments starts the REPL."""
    runner = CliRunner()
    
    # Mock run_repl to avoid blocking
    repl_called = False
    def mock_run_repl():
        nonlocal repl_called
        repl_called = True
    
    monkeypatch.setattr("assistant.app.terminal.repl.run_repl", mock_run_repl)
    
    result = runner.invoke(cli, [])
    assert repl_called == True
    assert result.exit_code == 0

def test_repl_starts_and_exits(monkeypatch):
    """Test that REPL starts, accepts /exit, and prints Goodbye."""
    # Mock dependencies of InteractiveREPL to avoid real DB/Config access if needed
    # But here we want to test the loop logic
    
    inputs = iter(["/exit"])
    monkeypatch.setattr("rich.console.Console.input", lambda self, prompt="": next(inputs))
    
    # Capture output
    from io import StringIO
    from rich.console import Console
    output = StringIO()
    custom_console = Console(file=output, force_terminal=False)
    monkeypatch.setattr("assistant.app.terminal.repl.console", custom_console)
    
    run_repl()
    
    out_text = output.getvalue()
    assert "AI Assistant started" in out_text
    assert "Goodbye." in out_text

def test_repl_handles_exit_without_slash(monkeypatch):
    """Test that 'exit' without slash also works."""
    inputs = iter(["exit"])
    monkeypatch.setattr("rich.console.Console.input", lambda self, prompt="": next(inputs))
    
    from io import StringIO
    from rich.console import Console
    output = StringIO()
    custom_console = Console(file=output, force_terminal=False)
    monkeypatch.setattr("assistant.app.terminal.repl.console", custom_console)
    
    run_repl()
    
    out_text = output.getvalue()
    assert "Goodbye." in out_text
