# tests/app/terminal/test_repl_renderer.py
from assistant.app.terminal.repl import render_structured_response
from assistant.ai.response_types_v2 import StructuredResponse
from rich.console import Console
from io import StringIO
import re

def test_render_structured_response_with_all_fields():
    console = Console(file=StringIO(), force_terminal=True, width=80)
    response = StructuredResponse(
        answer="Your local IP is 192.168.10.108.",
        command="hostname -I",
        details="This shows the IP addresses assigned to your machine.",
        next_step="Check your network configuration?"
    )

    # Capture output and strip ANSI codes
    render_structured_response(console, response)
    ansi_output = console.file.getvalue()
    output = re.sub(r'\x1b\[[0-9;]*m', '', ansi_output)

    assert "Your local IP is 192.168.10.108." in output
    assert "hostname -I" in output
    assert "This shows the IP addresses assigned to your machine." in output
    assert "Check your network configuration?" in output

def test_render_structured_response_with_only_answer():
    console = Console(file=StringIO(), force_terminal=True, width=80)
    response = StructuredResponse(answer="Simple answer.")

    render_structured_response(console, response)
    ansi_output = console.file.getvalue()
    output = re.sub(r'\x1b\[[0-9;]*m', '', ansi_output)

    assert "Simple answer." in output
    # Should not show empty sections
    assert "Command" not in output
    assert "Details" not in output
