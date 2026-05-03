from click.testing import CliRunner
from unittest.mock import patch
from assistant.main import cli

def test_cli_entry():
    runner = CliRunner()
    # Mock run_repl to prevent hanging in test
    with patch('assistant.app.terminal.repl.run_repl'):
        result = runner.invoke(cli)
        assert result.exit_code == 0

def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Commands:" in result.output
